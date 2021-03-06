# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
This module provides a plug&play config for renderers that produce multiple
output files and allow the user to define the pages with the API objects
to document.
"""

from nr.databind.core import Collection, Field, ProxyType, Struct
from pydoc_markdown.interfaces import Renderer
from pydoc_markdown.reflection import ModuleGraph
from typing import Iterable, Optional, List
import collections
import copy
import fnmatch
import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)
Page = ProxyType()


class IterHierarchyItem(Struct):
  page = Field(Page)
  parent_chain = Field([Page])

  def filename(self,
      parent_dir: Optional[str],  #: Parent directory to join with
      suffix_with_dot: str,  #: Suffix of the generated filename
      index_name: str = 'index',
      skip_empty_pages: bool = True,
      ) -> Optional[str]:
    path = [p.name for p in self.parent_chain] + [self.page.name]
    if self.page.children:
      if skip_empty_pages and not self.page.contents and not self.page.source:
        return None
      path.append(index-name)
    filename = os.path.join(*path) + suffix_with_dot
    if parent_dir:
      filename = os.path.join(parent_dir, filename)
    return filename


@Page.implementation  # pylint: disable=function-redefined
class Page(Struct):
  """
  Metadata for a page that a renderer implementation should understand
  in order to produce multiple output files. The page hierarchy defines
  the site navigation as well as the generated files.
  """

  #: The name of the page. This is usually the filename without the suffix.
  #: It may have additional meaning depending on the renderer. If it is
  #: not specified, it will fall back to a slug version of the #title.
  name = Field(str, default=None)

  #: The title of the page.
  title = Field(str)

  #: If set, the page does not generate a file but instead is rendered as
  #: a link to the specified URL in the site navigation.
  href = Field(str, default=None)

  #: If set, the page is rendered using the contents of the specified
  #: file. Some renderers may modify the source or add a preamble.
  source = Field(str, default=None)

  #: A list of glob patterns that match the absolute unique names of API
  #: objects to include for rendering in the page.
  contents = Field([str], default=None)

  #: A list of pages that are children of this page.
  children = Field([Page], default=list)

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if not self.name:
      self.name = re.sub(r'\s+', '-', self.title.lower())

  def iter_hierarchy(self, parent_chain: List['Page'] = None) -> Iterable[IterHierarchyItem]:
    if parent_chain is None:
      parent_chain = []
    yield IterHierarchyItem(self, parent_chain)
    for child in self.children:
      yield from child.iter_hierarchy(parent_chain + [self])

  def filtered_graph(self, graph: ModuleGraph) -> ModuleGraph:
    """
    Creates a copy of the module graph where only the API objects selected
    via #Page.contents are visible.
    """

    def _match(node):
      if self.contents:
        path = node.path()
        return any(fnmatch.fnmatch(path, x) for x in self.contents or ())
      return False

    def _update_nodes(x):
      x.visible = x.visible and _match(x)
      # Make sure all parents are visible as well.
      while x and x.visible:
        x = x.parent
        if x:
          x.visible = True

    clone = copy.deepcopy(graph)
    clone.visit(_update_nodes)
    return clone

  def render(
      self,
      filename: str,
      graph: ModuleGraph,
      renderer: Renderer
      ) -> None:
    """
    Renders the page by either copying the *source* to the specified
    *filename* or by rendering the *contents* from the *graph* using the
    specified *renderer*.

    Note that the *renderer* should be pre-configured to output to *filename*.
    """

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    if self.source:
      logger.info('Writing "%s" (source: "%s")', filename, self.source)
      shutil.copyfile(self.source, filename)
    else:
      logger.info('Rendering "%s"', filename)
      renderer.render(self.filtered_graph(graph))


class Pages(Collection, list):
  item_type = Page

  def iter_hierarchy(self) -> Iterable[IterHierarchyItem]:
    for page in self:
      yield from page.iter_hierarchy()