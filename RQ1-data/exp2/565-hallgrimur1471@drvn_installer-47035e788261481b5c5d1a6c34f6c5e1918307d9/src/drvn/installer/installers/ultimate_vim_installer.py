import sys
import logging
from pathlib import Path

import drvn.installer._utils as utils
import drvn.installer._dotfile_repository as dotfile_repository


def install(is_install_drvn_configs):
    logging.info("Installing ultimate_vim ...")
    _install_prerequisites()
    _install_vim()
    _install_ultimate_vim()
    _install_extra_plugins()
    if is_install_drvn_configs:
        _install_drvn_configs()


def _install_prerequisites():
    utils.try_cmd("sudo apt-get install -y cmake")

    python = _get_current_python_interpreter()
    utils.try_cmd(f"{python} -m pip install python-language-server")
    utils.try_cmd(f"{python} -m pip install mypy")


def _install_vim():
    try_cmd("sudo apt-get install -y vim")


def _install_ultimate_vim():
    ultimate_vim_path = Path("~/.vim_runtime").expanduser()
    if ultimate_vim_path.is_dir():
        logging.debug(
            "Looks like ultimate_vim is already cloned, "
            + "skipping cloning ..."
        )
    else:
        utils.try_cmd(
            "git clone --depth=1 "
            + f"https://github.com/amix/vimrc.git {ultimate_vim_path}"
        )
    utils.try_cmd("sh ~/.vim_runtime/install_awesome_vimrc.sh")


def _install_extra_plugins():
    _install_you_complete_me()
    _install_more_color_schemes()


def _install_you_complete_me():
    ycm_path_str = "~/.vim_runtime/my_plugins/YouCompleteMe"
    ycm_path = Path(ycm_path_str).expanduser()
    if not ycm_path.is_dir():
        utils.try_cmd(
            "cd ~/.vim_runtime/my_plugins && "
            + "git clone https://github.com/ycm-core/YouCompleteMe.git && "
            + "cd YouCompleteMe && "
            + "git submodule update --init --recursive"
        )
    else:
        logging.debug(
            "Looks like YouCompleteMe is already cloned, "
            + "skipping cloning ..."
        )

    python = _get_current_python_interpreter()
    utils.try_cmd(
        "cd ~/.vim_runtime/my_plugins/YouCompleteMe && "
        + f"{python} install.py --clang-completer"
    )


def _install_more_color_schemes():
    plugins_path = Path("~/.vim_runtime/sources_forked").expanduser()
    colorschemes_path = plugins_path / "vim-colorschemes"
    if not colorschemes_path.is_dir():
        utils.try_cmd("git clone https://github.com/flazz/vim-colorschemes.git")
    else:
        logging.debug(
            "Looks like vim-colorschemes is already cloned, "
            + "skipping cloning ..."
        )


def _install_drvn_configs():
    if not dotfile_repository.is_cloned():
        dotfile_repository.clone()
    _symlink_configs_to_dotfile_repository()


def _symlink_configs_to_dotfile_repository():
    dotfile_path = Path(".vim_runtime/my_configs.vim")
    real_path = dotfile_repository.get_path(dotfile_path)
    symlink_path = Path("~").expanduser() / dotfile_path
    utils.cmd(f"rm {symlink_path}")
    utils.try_cmd(f"ln -s '{real_path}' '{symlink_path}'")


def _get_current_python_interpreter():
    major = sys.version_info.major
    minor = sys.version_info.minor
    return f"python{major}.{minor}"