# -----------------------------------------------------------------------------
# Created: Sun 24 May 2020 20:45:00 IST
# Last-Updated: Mon  6 Jul 2020 20:28:20 IST
#
# __init__.py is part of somepackge
# URL: https://gitlab.com/justinekizhak/devinstaller
# Description: Init everything
#
# Copyright (c) 2020, Justine Kizhakkinedath
# All rights reserved
#
# Licensed under the terms of The MIT License
# See LICENSE file in the project root for full information.
# -----------------------------------------------------------------------------
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "software"), to deal in the software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the software, and to permit
# persons to whom the software is furnished to do so, subject to the
# following conditions:
#
# the above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the software.
#
# the software is provided "as is", without warranty of any kind,
# express or implied, including but not limited to the warranties of
# merchantability, fitness for a particular purpose and noninfringement.
# in no event shall the authors or copyright holders be liable for any claim,
# damages or other liability, whether in an action of contract, tort or
# otherwise, arising from, out of or in connection with the software or the
# use or other dealings in the software.
# -----------------------------------------------------------------------------

"""Init everything"""

from typing import List, Optional
from devinstaller import file_handler as f
from devinstaller import installer as i
from devinstaller import commands as c
from devinstaller import schema as s
from devinstaller import exceptions as e
from devinstaller import models as m


def validate_spec(doc_file_path: str) -> m.FullDocumentType:
    """Validate the spec

    Args:
        doc_file_path: The path to the devfile

    Returns:
        Valid schema file
    """
    document = f.read(doc_file_path)
    return s.validate(document)


def install(
    full_document: m.FullDocumentType, platform: str = None, preset: str = None
) -> None:
    """Entry point for the install function

    Args:
        full_document: The full spec file
        platform: name of the platform
        preset: name of the preset
    """
    document = _get_platform_document(full_document, platform)
    graph = s.generate_dependency(document)
    requirements_list = _get_preset_requirements(document, preset)
    i.main(graph, requirements_list)


def _get_preset_data(
    presets: List[m.PresetType], preset_name: str, rule_code: int
) -> m.PresetType:
    """Returns the required preset object

    Args:
        presets: The object containing info about all the presets
        preset_name: The name of the required preset
        rule_code: The error exception which will be thrown when no preset is
            matched with the name of required preset

    Returns:
        The data of the required preset which is to be installed
    """
    for preset in presets:
        if preset["name"] == preset_name:
            return preset
    raise e.RuleViolationError(rule_code)


def _get_platform_document(
    full_document: m.FullDocumentType, platform_name: Optional[str]
) -> m.PlatformType:
    """Returns the spec for the required platform.

    Args:
        document: The whole spec (including all the platforms)
        platform_name: The name of the platform given by the user

    Returns:
        The part of spec specific to the platform
    """
    for platform in full_document["platforms"]:
        if platform_name and platform["name"] == platform_name:
            return platform
        if compare_command_and_response(platform["platform_info"]):
            return platform
    raise e.RuleViolationError(100)


def _get_preset_requirements(
    document: m.PlatformType, preset_name: Optional[str]
) -> m.PresetType:
    """Get the list of all the modules which has to be installed.
    This data is extracted by either the user giving us the name of the
    preset which is to be installed or by using the name of default
    preset and extracting the data.

    Args:
        document: The complete spec specific to the platform
        preset_name: The name of the preset given by the user

    Returns:
        The preset module object
    """
    if preset_name:
        return _get_preset_data(document["presets"], preset_name, 102)
    if "default" in document:
        return _get_preset_data(document["presets"], document["default"], 103)
    raise e.RuleViolationError(101)


def compare_command_and_response(input_data: m.PlatformInfo) -> bool:
    """Check if the given platform is the one expected.
    It runs the command and checks it with the expected response in the
    devfile. If matches then it returns true else false.

    Args:
        input_data: The platform object in the devfile

    Returns:
        If present then True
    """
    pass