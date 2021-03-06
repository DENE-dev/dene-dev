# -*- coding=UTF-8 -*-
"""Comp multi pass to beauty."""
from __future__ import absolute_import, unicode_literals

import inspect
import json
import logging
import os
import re
import sys

import cast_unknown as cast
import nuke

from edit import add_layer, copy_layer, replace_node
from filetools import get_layer, module_path
from organize import autoplace

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import (Dict, List, Any, Set, Text, Optional)

LOGGER = logging.getLogger('com.wlf.precomp')


class __PrecompSwitch(object):
    """Modified switch node for precomp.  """

    knob_name = b'raw_hash'

    @classmethod
    def init(cls, node):
        # type: (nuke.Node) -> nuke.Node
        """Add necessary knobs.  """

        assert isinstance(
            node, nuke.Node), 'Expect a node, got: {}'.format(node)

        knob_name = cls.knob_name
        knobs = node.knobs()
        if knob_name not in knobs:
            n = node.input(1)
            raw_hash = cls.hash(n)
            k = nuke.Int_Knob(cast.binary(knob_name))
            _ = k.setValue(raw_hash)
            node.addKnob(k)
        else:
            k = knobs[knob_name]
        k.setFlag(nuke.READ_ONLY)
        return node

    @classmethod
    def hash(cls, node):
        # type: (nuke.Node) -> int
        """Node hash result of @node up to upstream start.  """

        assert isinstance(
            node, nuke.Node), 'Expect a node, got: {}'.format(node)

        def _hash(n):
            assert isinstance(n, nuke.Node)
            ret = n.writeKnobs(nuke.WRITE_ALL | nuke.WRITE_NON_DEFAULT_ONLY)
            ret = ret.split()
            assert isinstance(ret, list)
            for knob in (
                    'xpos', 'ypos', 'selected',
                    'name', 'gl_color', 'tile_color'
                    'label', 'note_font', 'note_font_size', 'note_font_color',
                    'hide_input', 'cached', 'cached', 'dope_sheet', 'bookmark',
                    'postage_stamp', 'postage_stamp_frame',
            ):
                if knob in ret:
                    ret.remove(knob)
            ret = hash(tuple(ret))
            return ret

        def _get_upstream(nodes, flags=nuke.INPUTS | nuke.HIDDEN_INPUTS):
            ret = set()
            if isinstance(nodes, nuke.Node):
                nodes = [nodes]

            nodes = tuple(nodes)
            while nodes:
                deps = nuke.dependencies(nodes, flags)
                nodes = [n for n in deps
                         if n not in ret
                         and n not in nodes
                         and n.Class() in ('Merge2', 'Shuffle')]
                ret.update(set(deps))
            return ret

        nodes = _get_upstream(node)
        ret = _hash(node)

        for n in nodes:
            ret += _hash(n)
        ret = hash(ret)

        return ret

    @classmethod
    def get_which(cls, node):
        """Return auto input choice for @node.  """

        assert isinstance(node, nuke.Node)\
            and node.Class() == 'Switch',\
            'Expect a switch node, got: {}'.format(node)

        n = node.input(1)
        if not n:
            ret = False
        elif cls.knob_name not in node.knobs():
            ret = True
        else:
            ret = node[cast.binary(cls.knob_name)].value() != cls.hash(n)

        _ = node[b'tile_color'].setValue(0xFFFFFFFF if ret else 0x000000FF)
        return ret


PrecompSwitch = __PrecompSwitch


class RendererConfig():
    def __init__(self):
        self.name = ""  # type: Text
        self.layers = set()  # type: Set[Text]
        self.combine = {}  # type: Dict[Text, List[Text]]
        self.combineMode = {}  # type: Dict[Text, Text]
        self.translate = {}  # type: Dict[Text, Text]
        self.copy = []  # type: List[Text]
        self.rename = {}  # type: Dict[Text, Text]
        self.plus = []  # type: List[Text]

    def fromJSON(self, data):
        # type: (Dict[Text, Any]) -> RendererConfig
        """load data from json.

        Args:
            data (Dict[str, Any]): Parsed json data.

        Returns:
            self: for method chaining.
        """
        self.name = data.get("name", "")
        self.layers = set(data.get("layers", []))
        self.combine = data.get("combine", {})
        self.combineMode = data.get("combineMode", {})
        self.translate = data.get("translate", {})
        self.copy = data.get("copy", {})
        self.rename = data.get("rename", {})
        self.plus = data.get("plus", {})
        return self

    def l10n(self, value):
        # type: (Text) -> Text
        """Return translated value.  """

        if not value:
            return ''
        for pat in self.translate:
            if re.match(pat, value):
                return re.sub(pat, self.translate[pat], value)
        return cast.text(value)


RENDERER_REGISTRY = {}  # type: Dict[Text, RendererConfig]


def load_renderer_config():
    for i in os.listdir(module_path("../data")):
        match = re.match(r"^precomp\.(.+).json", i)
        if not match:
            continue
        name = match.group(1)
        with open(module_path("../data", i), "r") as f:
            data = json.load(f, encoding="utf-8")
        RENDERER_REGISTRY[name] = RendererConfig().fromJSON(data)


load_renderer_config()


def detect_renderer(layers):
    ret = None
    retLayerMatch = 0
    for i in RENDERER_REGISTRY.values():
        layerMatch = len([j for j in layers if j in i.layers])
        if layerMatch > retLayerMatch:
            ret = i
            retLayerMatch = layerMatch
    if ret is None:
        raise ValueError("detect_renderer: can not detect renderer")
    return ret


class Precomp(object):
    """A sequence of merge or copy.  """

    def __init__(self, nodes, renderer=None, async_=True):
        # type: (List[nuke.Node], Text, bool) -> None
        self.last_node = None  # type: Optional[nuke.Node]
        self.source = {}  # type: Dict[Text, nuke.Node]

        assert nodes, 'Can not precomp without node.'

        def _get_filename(n):
            # type: (nuke.Node) -> Text
            return cast.text(n.metadata(b'input/filename') or nuke.filename(n) or '')

        if isinstance(nodes, nuke.Node):
            nodes = [nodes]
        elif len(nodes) > 1:
            nodes = list(n for n in nodes if n.Class() == 'Read')

        # Record node for every source layer.
        for n in nodes:
            layer = get_layer(_get_filename(n))
            if layer:
                self.source[layer] = n
            else:
                self.source['beauty'] = n
        if len(self.source) == 1:
            n = sorted(nodes,
                       key=lambda n: (len(nuke.layers(n)),
                                      len(_get_filename(n)) * -1),
                       reverse=True)[0]
            layers = nuke.layers(n)
            LOGGER.debug(
                'Precomp single node that has this layers:\n%s', layers)
            self.source = {cast.text(layer): n
                           for layer in layers}
            self.source['beauty'] = n
        LOGGER.debug('Source layers:\n%s', self.source.keys())

        # load config
        self._config = (detect_renderer(self.source.keys())
                        if renderer is None
                        else RENDERER_REGISTRY[renderer])

        # set label for nodes
        if len(nodes) > 1:
            for layer, n in self.source.items():
                _layer = cast.binary(self._config.l10n(layer))
                _label = n[b'label'].value()
                if _layer not in _label:
                    (
                        n[b'label'].
                        setValue(
                            (_label + b"\n" + _layer).strip(),
                        )
                    )

        self.last_node = self.node('beauty')
        for layer in self._config.copy:
            for i in self.source.keys():
                if re.match('(?i)^{}\\d*$'.format(layer), cast.text(i)):
                    self.copy(i)
        for layer, output in self._config.rename.items():
            self.copy(layer, output)

        # Plus nodes.
        dot_node = nuke.nodes.Dot(inputs=(self.last_node,))
        remove_node = nuke.nodes.Remove(
            inputs=(dot_node,), channels='rgb')
        self.last_node = remove_node
        for layer in self._config.plus:
            _ = self.plus(layer)

        # Precomp Switch.
        kwargs = {'which':
                  cast.binary(
                      '{{[python {__PrecompSwitch.get_which(nuke.thisNode())}]}}'),
                  'inputs': [dot_node, self.last_node],
                  'label': cast.binary('{} ?????????\n????????????'.format(self._config.name)),
                  'onCreate': cast.binary(inspect.getsource(PrecompSwitch) + """
__PrecompSwitch.init(nuke.thisNode())""")}
        setattr(sys.modules['__main__'], '__PrecompSwitch', PrecompSwitch)
        if self.last_node is remove_node:
            kwargs['disable'] = True
        self.last_node = PrecompSwitch.init(
            nuke.nodes.Switch(**kwargs))

        replace_node(dot_node.input(0), self.last_node)

        _ = autoplace(self.last_node, recursive=True,
                      undoable=False, async_=async_)

    def check(self):
        """Check if has all necessary layer.  """
        pass

    def layers(self):
        """Return layers in self.last_node. """

        if not self.last_node:
            return []
        return nuke.layers(self.last_node)

    def node(self, layer):
        # type: (Text) -> Optional[nuke.Node]
        """Return a node that should be treat as @layer.  """

        _ = add_layer(layer)
        ret = self.source.get(layer)
        if layer in self.layers():
            kwargs = {
                'inputs': (self.last_node,),
                'in': cast.binary(layer),
            }

            try:
                kwargs['postage_stamp'] = (
                    cast.not_none(self.
                                  last_node)[b'postage_stamp'].
                    value()
                )
            except NameError:
                pass
            ret = nuke.nodes.Shuffle(**kwargs)
        elif layer in self._config.combine:
            pair = self._config.combine[layer]
            if self.source.get(pair[0])\
                    and self.source.get(pair[1]):
                LOGGER.debug('Combine for layer: %s, %s -> %s',
                             pair[0], pair[1], layer)
                input0, input1 = self.node(pair[0]), self.node(pair[1])
                kwargs = {
                    'inputs': [input0, input1],
                    'operation': (
                        self.
                        _config.
                        combineMode.
                        get(layer, 'multiply')
                    ),
                    'output': 'rgb',
                    'label': cast.binary(self._config.l10n(layer)),
                }
                try:
                    if input0 and input1:
                        kwargs['postage_stamp'] = (
                            input0[b'postage_stamp'].value()
                            and input1[b'postage_stamp'].value()
                        )
                except NameError:
                    pass
                n = nuke.nodes.Merge2(**kwargs)
                self.source[layer] = n
                ret = n
            else:
                LOGGER.debug('Source not enough: %s', self.source.keys())
        if not ret:
            LOGGER.debug('Can not get node for layer:%s', layer)
        return ret

    def plus(self, layer):
        # type: (Text) -> Optional[nuke.Node]
        """Plus a layer to last rgba.  """

        input1 = self.node(layer)
        if not input1:
            return
        LOGGER.debug('Plus layer to last:%s', layer)
        if not self.last_node:
            self.last_node = nuke.nodes.Constant()

        if layer not in self.layers():
            input1 = nuke.nodes.Shuffle(inputs=[input1], out=layer)
        self.last_node = nuke.nodes.Merge2(
            inputs=[self.last_node, input1], operation='plus',
            also_merge=layer if layer not in self.layers() else 'none',
            label=cast.binary(self._config.l10n(layer)),
            output='rgb')

    def copy(self, layer, output=None):
        # type: (Text, Optional[Text]) ->  None
        """Copy a layer to last.  """

        if not self.last_node:
            self.last_node = self.node(layer)
        elif layer not in self.layers() and self.source.get(layer):
            LOGGER.debug('Copy layer to last:%s -> %s', layer, output or layer)
            self.last_node = copy_layer(
                self.last_node, self.node(layer), layer=layer, output=output)