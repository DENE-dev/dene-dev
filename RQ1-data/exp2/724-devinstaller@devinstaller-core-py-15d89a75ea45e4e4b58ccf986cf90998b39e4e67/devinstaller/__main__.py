# -----------------------------------------------------------------------------
# Created: Mon 25 May 2020 15:10:17 IST
# Last-Updated: Mon  6 Jul 2020 20:28:25 IST
#
# __main__.py is part of devinstaller
# URL: https://gitlab.com/justinekizhak/devinstaller
# Description: Main entrypoint
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

"""The main entrypoint module"""

import os
import click
import devinstaller as d
from devinstaller import exceptions as e


DEFAULT_DOC_FILE_PATH = os.getcwd() + "/sample.devfile.yml"


@click.group()
def main():
    """Main entrypoint function. Everything in this run before any of the
    subcommand
    """


@main.resultcallback()
def process_result():
    """Final callback function. Runs after the end of everything."""
    click.secho("Bye. Have a good day.", fg="green")


@main.command()
@click.option(
    "-f",
    "--file",
    "file_name",
    default=DEFAULT_DOC_FILE_PATH,
    help="Name of the install file. Default: `install.yaml`",
)
@click.option(
    "-p",
    "--platform",
    "platform",
    help=(
        "Name of the current platform. If not provided then I'll try to "
        "check if you have provided any help in the file."
        "For more information read the docs."
    ),
)
@click.option(
    "--preset",
    "preset",
    help=(
        "Name of the preset you want to install. "
        "If not provided then the default preset will be installed."
    ),
)
def install(file_name, platform, preset):
    """Install the default preset and the modules which it requires."""
    try:
        full_document = d.validate_spec(file_name)
        d.install(full_document, platform, preset)
    except e.RuleViolation as err:
        click.secho(str(err), fg="red")
    except e.SchemaComplianceError as err:
        click.secho(str(err), fg="red")


@main.command()
@click.option(
    "-f",
    "--file",
    "file_name",
    default=DEFAULT_DOC_FILE_PATH,
    help="Name of the install file. Default: `install.yaml`",
)
def show(file_name):
    """Show all the presets and modules available for your OS."""
    try:
        d.validate_spec(file_name)
    except e.SchemaComplianceError as err:
        click.secho(str(err), fg="red")


# @main.command()
# @click.argument("commands", nargs=-1)
# def run(commands):
#     """where COMMANDS is your regular bash command

#     Example: Here `dev run brew install pipenv clang emacs` will install all
#     the packages using brew and add it into the spec automagically.
#     """
#     pass


if __name__ == "__main__":
    main()