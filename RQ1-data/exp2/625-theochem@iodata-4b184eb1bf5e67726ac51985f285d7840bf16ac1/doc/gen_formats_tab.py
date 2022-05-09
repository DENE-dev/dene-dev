#!/usr/bin/env python3
# IODATA is an input and output module for quantum chemistry.
# Copyright (C) 2011-2019 The IODATA Development Team
#
# This file is part of IODATA.
#
# IODATA is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# IODATA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
# --
# pylint: disable=unused-argument,redefined-builtin
"""Generate formats.rst."""
from collections import defaultdict
import inspect
import importlib

import iodata


__all__ = (write_rst_table, generate_table_rst)


def _generate_all_format_parser():
    """Parse supported functionality from each module.

    Returns
    -------
    tuple(dict, dict)
        dict{format_name: index}
        dict{proper_name: formats_name_supported}
    """
    # inspect iodata format module
    # obtaining a list of tuble [(module_name: str, module_object: obj)]
    format_modules = inspect.getmembers(iodata.formats, inspect.ismodule)

    fmt_names = {}  # storing supported format name and index(position) in table
    prop_with_mods = defaultdict(list)  # storing methods with format supporting it.
    for fmt_name, _ in format_modules:
        # inspect(import) target module
        fmt_module = importlib.import_module("iodata.formats." + fmt_name)
        # add new format name to fmt_names
        if fmt_name not in fmt_names:
            fmt_names[fmt_name] = len(fmt_names) + 1
        # obtaining supported properties
        fields = fmt_module.load_one.guaranteed
        for i in fields:
            # add format to its supported property list
            prop_with_mods[i].append(fmt_name)
    return fmt_names, prop_with_mods


def generate_table_rst():
    """Construct table contents.

    Returns
    -------
    list[list[]]
        table with rows of each property and columns of each format
    """
    table = []
    methods_names, prop_with_mods = _generate_all_format_parser()
    # construct header
    header = ["Properties"] + list(methods_names.keys())
    table.append(header)
    for prop in sorted(prop_with_mods.keys()):
        # construct each row contents
        row = [prop] + ["--"] * len(methods_names)
        for method in prop_with_mods[prop]:
            row[methods_names[method]] = u"\u2713"
        table.append(row)
    return table


def write_rst_table(f, table, nhead=1):
    """Write an RST table to file f.

    Parameters
    ----------
    f : file object
        A writable file object
    table : list[list[]]
        A list of rows. Each row must be a list of cells containing strings
    nhead : int, optional
        The number of header rows
    """

    def format_cell(cell):
        if cell is None or len(cell.strip()) == 0:
            return "\\ "
        return str(cell)

    # Determine the width of each column
    widths = {}
    for row in table:
        for icell, cell in enumerate(row):
            widths[icell] = max(widths.get(icell, 2), len(format_cell(cell)))

    def format_row(cells, margin):
        return " ".join(
            margin + format_cell(cell).rjust(widths[icell]) + margin
            for icell, cell in enumerate(cells)
        )

    # construct the column markers
    markers = format_row(["=" * widths[icell] for icell in range(len(widths))], "=")

    # top markers
    print(markers, file=f)

    # heading rows (if any)
    for irow in range(nhead):
        print(format_row(table[irow], " "), file=f)
    if nhead > 0:
        print(markers, file=f)

    # table body
    for irow in range(nhead, len(table)):
        print(format_row(table[irow], " "), file=f)

    # bottom markers
    print(markers, file=f)


content_table = generate_table_rst()
with open("format_tab.inc", "w") as inc_file:
    write_rst_table(
        inc_file, content_table,
    )