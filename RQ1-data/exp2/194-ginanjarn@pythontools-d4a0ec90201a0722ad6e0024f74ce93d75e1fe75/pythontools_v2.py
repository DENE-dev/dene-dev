"""Main plugin"""


import sublime  # pylint: disable=import-error
import sublime_plugin  # pylint: disable=import-error
import threading
import logging
import os
import time
from .core.sublimetext import client
from .core.sublimetext import document
from .core.sublimetext import interpreter


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
sh.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "plugins.log"))
fh.setFormatter(logging.Formatter("%(levelname)s\t%(module)s: %(lineno)d\t%(message)s"))
fh.setLevel(logging.ERROR)
logger.addHandler(sh)
logger.addHandler(fh)


INSTANCE_LOCK = threading.Lock()
REQUEST_LOCK = threading.RLock()


def instance_lock(func):
    """instance lock

    prevent run multiple instance
    """

    def wrapper(*args, **kwargs):
        if INSTANCE_LOCK.locked():
            logger.debug("instance locked")
            return None

        with INSTANCE_LOCK:
            return func(*args, **kwargs)

    return wrapper


def request_lock(func):
    """request lock

    prevent multiple request from outer context
    """

    def wrapper(*args, **kwargs):
        with REQUEST_LOCK:
            return func(*args, **kwargs)

    return wrapper


SETTINGS_BASENAME = "Pytools.sublime-settings"

# Settings name
F_AUTOCOMPLETE = "autocomplete"
F_DOCUMENTATION = "documentation"
W_ABSOLUTE_IMPORT = "absolute_import"
F_DOCUMENT_FORMATTING = "document_formatting"
F_DIAGNOSTIC = "diagnostic"
F_RENAME = "rename"

# All features enabled
ALL_ENABLED = False


def feature_enabled(feature_name: str, *, default=True) -> bool:
    """check if feature enabled on settings"""

    sublime_settings = sublime.load_settings(SETTINGS_BASENAME)
    return sublime_settings.get(feature_name, default) and ALL_ENABLED


class ServerCapability(dict):
    """server capability"""


SERVER_CAPABILITY = ServerCapability()


def server_capable(feature_name: str, *, default=False) -> bool:
    """check if server capable perform feature"""

    return SERVER_CAPABILITY.get(feature_name, default)


SERVER_ONLINE = False


def set_offline(status=True):
    """set server state offline"""

    global SERVER_ONLINE

    SERVER_ONLINE = not status


def check_connection():
    """check any server online"""

    logger.info("check_connection")

    try:
        client.ping()

    except client.ServerOffline:
        set_offline()

    else:
        set_offline(False)  # online


INITIALIZED = False


@request_lock
def initialize():
    """initialize server"""

    logger.info("initialize")

    global SERVER_ONLINE
    global INITIALIZED

    if INITIALIZED:
        return

    try:
        result = client.initialize()

    except client.ServerOffline:
        logger.debug("ServerOffline")
        set_offline()
        INITIALIZED = False

    else:
        logger.debug("ServerOnline")
        set_offline(False)  # online
        INITIALIZED = True

        if result.error:
            return

        global SERVER_CAPABILITY

        # apply capability
        SERVER_CAPABILITY[F_AUTOCOMPLETE] = result.results.get("completion", False)
        SERVER_CAPABILITY[F_DOCUMENTATION] = result.results.get("hover", False)
        SERVER_CAPABILITY[F_DOCUMENT_FORMATTING] = result.results.get(
            "document_format", False
        )
        SERVER_CAPABILITY[F_DIAGNOSTIC] = result.results.get("diagnostic", False)
        SERVER_CAPABILITY[F_RENAME] = result.results.get("rename", False)
        logger.debug(SERVER_CAPABILITY)

    finally:
        logger.debug("SERVER_ONLINE : %s, INITIALIZED : %s", SERVER_ONLINE, INITIALIZED)


WORKSPACE_DIRECTORY = None


@request_lock
def change_workspace(directory_path) -> None:
    """change workspace directory"""

    logger.info("on change workspace")

    global WORKSPACE_DIRECTORY

    if directory_path != WORKSPACE_DIRECTORY:
        result = client.change_workspace(directory_path)
        if result.results:
            WORKSPACE_DIRECTORY = result.results["workspace_directory"]
            logger.debug("WORKSPACE_DIRECTORY = %s", WORKSPACE_DIRECTORY)


def valid_source(view, pos=0):
    """python source file"""

    return view.match_selector(pos, "source.python")


def valid_attribute(view, pos):
    """attribute in valid scope"""

    result = all(
        [
            view.match_selector(pos, "source.python"),
            not view.match_selector(pos, "source.python comment"),
            not view.match_selector(pos, "source.python meta.string.python string"),
        ]
    )
    return result


SERVER_ERROR = False


class PytoolsPythonInterpreterCommand(sublime_plugin.WindowCommand):
    """Load python interpreter command"""

    def run(self):
        try:
            interpreter.set_interpreter(self.window)
        except Exception:
            logger.error("set interpreter", exc_info=True)


class PytoolsRunserverCommand(sublime_plugin.WindowCommand):
    """Run server command"""

    def run(self):
        logger.info("on run server")

        if SERVER_ERROR:
            logger.debug("server error")
            return  # cancel if server error

        sublime_settings = sublime.load_settings("Pytools.sublime-settings")
        python_path = sublime_settings.get("interpreter")

        if not python_path:
            config = sublime.ok_cancel_dialog(
                "Python interpreter not configured.\nConfigure now?",
            )

            if config:
                self.window.run_command("pytools_python_interpreter")

            # TODO: HANDLE ON IGNORE ------------------------------------------
            else:
                global ALL_ENABLED
                ALL_ENABLED = False
            # -----------------------------------------------------------------

            return

        thread = threading.Thread(target=self.run_server, args=(python_path,))
        thread.start()

    @instance_lock
    @request_lock
    def run_server(self, python_path):
        """run server thread"""

        activate_path = interpreter.find_activate(python_path)
        env_path = interpreter.find_environment(python_path)

        server_path = os.path.dirname(
            os.path.abspath(__file__)
        )  # current file directory

        server_module = "core.server"

        activate_path = [path for path in (activate_path, env_path) if path]

        global SERVER_ERROR

        try:
            logger.debug("running server")
            logger.debug("%s, %s, %s", server_path, server_module, activate_path)

            active = request_lock(
                client.run_server(
                    server_path, server_module, activate_path=activate_path
                )
            )

            if active:
                ncount = 0
                while not SERVER_ONLINE:
                    time.sleep(pow(2, ncount))  # sleep for 2^n second
                    ncount += 1
                    initialize()

        except client.ServerError:
            logger.debug("server error")
            SERVER_ERROR = True

        except Exception:
            logger.error("run server", exc_info=True)


class PytoolsShutdownserverCommand(sublime_plugin.WindowCommand):

    """Shutdown command"""

    @instance_lock
    def run(self):
        logger.info("on shutdown server")

        thread = threading.Thread(target=self.exit)
        thread.start()

    @request_lock
    def exit(self):

        if SERVER_ERROR:  # cancel all request if server error
            return

        try:
            response = client.shutdown()
        except client.ServerOffline:
            set_offline()
            logger.debug("ServerOffline")

        except Exception:
            logger.error("shutdown server", exc_info=True)

        else:
            set_offline()
            logger.debug("finish shutdown server")

        finally:
            global INITIALIZED
            global SERVER_CAPABILITY

            INITIALIZED = False
            SERVER_CAPABILITY.clear()


def plugin_loaded():
    """on plugin loaded

    sublime definition for plugin_loaded event
    """

    # Enable default on loaded
    global ALL_ENABLED
    ALL_ENABLED = True

    thread = threading.Thread(target=initialize)
    thread.start()
    # TODO: HANDLE ON SETTINGS CHANGE --------------------------------------------


def absolute_folder(view):

    file_name = view.file_name()
    matches = [
        folder for folder in view.window().folders() if file_name.startswith(folder)
    ]

    if any(matches):
        # return the longest matched path
        return max(matches)

    return file_name


# Diagnostic data holder
DIAGNOSTICS = []


class Event(sublime_plugin.ViewEventListener):
    """Event handler"""

    def __init__(self, view):

        self.view = view

        self.completion = None

        self.cached_completion = None
        self.temp_completion_src = ""
        self.cached_docstring = None
        self.temp_docstring_src = ""
        self.cached_diagnostic = None

    @staticmethod
    def build_completion(completions: "Iterable") -> "Iterator[Any, Any]":
        """build completion"""

        for completion in completions:
            yield (
                "%s  \t%s" % (completion["label"], completion["type"]),
                completion["label"],
            )

    @instance_lock
    @request_lock
    def fetch_completions(self, prefix, location):
        """fetch completion process"""

        view = self.view

        start = 0
        end = location
        word_region = view.word(location)
        if view.substr(word_region).isidentifier() and len(prefix) > 1:
            end = word_region.a  # complete at first identifier offset
        source_region = sublime.Region(start, end)
        line, character = view.rowcol(end)  # get rowcol at end selection

        source = view.substr(source_region)

        if self.temp_completion_src == source:
            self.completion = self.cached_completion
            return None

        try:
            initialize()

            if feature_enabled(W_ABSOLUTE_IMPORT):
                work_dir = absolute_folder(view)
            else:
                work_dir = os.path.dirname(view.file_name())

            change_workspace(work_dir)

            result = client.fetch_completion(source, line, character)

        except client.ServerOffline:
            set_offline()
            logger.debug("ServerOffline")
            return None

        else:
            if result.error:
                logger.info(result.error)
                return None

            self.completion = (
                list(self.build_completion(result.results)),
                sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS,
            )

            # set cache
            self.temp_completion_src = source
            self.cached_completion = self.completion

        document.show_completions(view)

    def on_query_completions(self, prefix, locations):
        """on_query_completion event"""

        logger.info("on query completions")
        view = self.view
        if all(
            [
                valid_source(view),
                valid_attribute(view, locations[0]),
                feature_enabled(F_AUTOCOMPLETE),
            ]
        ):
            if self.completion:
                completion = self.completion
                self.completion = None
                return completion

            if not SERVER_ONLINE:
                view.window().run_command("pytools_runserver")
                return

            if not server_capable(F_AUTOCOMPLETE):
                return

            thread = threading.Thread(
                target=self.fetch_completions, args=(prefix, locations[0])
            )
            thread.start()

    @staticmethod
    def decorate(content) -> str:
        """decorate popup content"""
        return '<div style="padding: .5em">%s</div>' % content

    @instance_lock
    @request_lock
    def fetch_documentation(self, location):
        """fetch documentation thread"""

        view = self.view

        start = 0
        word_region = view.word(location)

        if view.substr(word_region).isidentifier():
            end = word_region.b  # select until end of word
        else:
            return  # cancel request for non identifier

        source_region = sublime.Region(start, end)

        source = view.substr(source_region)
        line, character = view.rowcol(end)  # get rowcol at end selection

        content, link = None, None  # cache holder

        if self.temp_docstring_src == source:
            logger.debug("use cached docstring : %s", self.cached_docstring)
            content, link = self.cached_docstring

        else:
            try:
                initialize()

                if feature_enabled(W_ABSOLUTE_IMPORT):
                    work_dir = absolute_folder(view)
                else:
                    work_dir = os.path.dirname(view.file_name())

                change_workspace(work_dir)

                result = client.fetch_documentation(
                    view.substr(source_region), line, character
                )
                logger.debug(result)

            except client.ServerOffline:
                set_offline()
                logger.debug("ServerOffline")

            except Exception:
                logger.error("fetch documentation", exc_info=True)

            else:
                if result.error:  # any error
                    return  # cancel

                if not result.results:  # empty results
                    return  # cancel

                content = result.results.get("html")
                link = result.results.get("link")

                # set cache
                self.temp_docstring_src = source
                self.cached_docstring = (content, link)

        if content:  # any content
            document.show_popup(
                view,
                self.decorate(content),
                location,
                lambda _: document.open_link(view, link),
            )

    def on_hover(self, point, hover_zone):
        """on_hover event"""

        logger.info("on hover")
        view = self.view

        if all(
            [
                valid_source(view),
                valid_attribute(view, point),
                feature_enabled(F_DOCUMENTATION),
                hover_zone == sublime.HOVER_TEXT,
            ]
        ):
            if not SERVER_ONLINE:
                view.window().run_command("pytools_runserver")
                return

            if not server_capable(F_DOCUMENTATION):
                return

            thread = threading.Thread(target=self.fetch_documentation, args=(point,))
            thread.start()

        elif all(
            [
                valid_source(view),
                valid_attribute(view, point),
                feature_enabled(F_DIAGNOSTIC),
                hover_zone == sublime.HOVER_GUTTER,
                DIAGNOSTICS,
            ]
        ):
            row, _ = view.rowcol(point)
            if self.cached_diagnostic:
                content = self.cached_diagnostic.get(row)
                logger.debug("cached : %s", content)
            else:
                diagnostic_message = document.diagnostic_message(DIAGNOSTICS, view)
                self.cached_diagnostic = diagnostic_message
                content = self.cached_diagnostic.get(row)
                logger.debug("loaded : %s", content)

            if content:  # any content
                document.show_popup(view, self.decorate(content), point, callback=None)

    def clear_cached_diagnostic(self):
        if self.cached_diagnostic:
            self.cached_diagnostic = None

    def on_modified(self):
        self.clear_cached_diagnostic()

    def on_activated(self):
        self.clear_cached_diagnostic()

    def on_pre_save_async(self) -> None:
        self.clear_cached_diagnostic()
        self.view.run_command("pytools_clear_diagnostic")


class PytoolsFormatCommand(sublime_plugin.TextCommand):
    """Formatting command"""

    def run(self, edit):
        logger.info("on format document")

        view = self.view

        if all([valid_source(view), feature_enabled(F_DOCUMENT_FORMATTING),]):
            if not SERVER_ONLINE:
                view.window().run_command("pytools_runserver")
                return

            if not server_capable(F_DOCUMENT_FORMATTING):
                return

            source = view.substr(sublime.Region(0, view.size()))
            file_name = view.file_name()

            thread = threading.Thread(
                target=self.formatting_task, args=(file_name, source)
            )
            thread.start()

    @staticmethod
    @instance_lock
    @request_lock
    def formatting_task(path, source):
        logger.debug("on formatting thread")

        try:
            result = client.format_code(source)
            logger.debug(result)

        except client.ServerOffline:
            set_offline()
            logger.debug("ServerOffline")

        except Exception:
            logger.error("format document", exc_info=True)

        else:
            if result.error:  # any error
                logger.debug(result.error)
                return

            window = sublime.active_window()
            view = window.open_file(path)
            view.run_command(
                "pytools_apply_rpc_change", args={"changes": result.results}
            )

    def is_visible(self):
        return valid_source(self.view)


class PytoolsDiagnosticCommand(sublime_plugin.TextCommand):
    """Diagnostic command"""

    def run(self, edit, path=None):
        logger.info("on diagnostic")

        view = self.view
        if all([valid_source(view), feature_enabled(F_DIAGNOSTIC),]):

            if not server_capable(F_DIAGNOSTIC):
                return

            if not path:
                path = view.file_name()

            if not any([os.path.isdir(path), os.path.isfile(path)]):
                return

            thread = threading.Thread(target=self.diagnose, args=(path,))
            thread.start()

    @instance_lock
    @request_lock
    def diagnose(self, path):
        logger.debug("on diagnostic thread")
        try:
            result = client.analyzer.get_diagnostic(path)
        except client.ServerOffline:
            logger.debug("ServerOffline")
        else:
            if result.error:
                logger.debug(result.error)
                return

            global DIAGNOSTICS

            for diagnostic in result.results:
                DIAGNOSTICS.append(document.Mark.from_rpc(self.view, diagnostic))

            logger.debug(DIAGNOSTICS)

            document.apply_diagnostics(self.view, DIAGNOSTICS)


class PytoolsClearDiagnosticCommand(sublime_plugin.TextCommand):
    """Diagnostic command"""

    def run(self, edit):
        logger.info("on clear diagnostic")

        view = self.view

        for severity in [
            document.ERROR,
            document.WARNING,
            document.INFO,
            document.HINT,
        ]:
            document.erase_regions(view, document.KEY_FORMAT % severity)

        global DIAGNOSTICS

        # clear diagnostic on current view only
        def keeped_criteria(mark: document.Mark):
            return mark.view_id != view.id()

        DIAGNOSTICS = list(filter(keeped_criteria, DIAGNOSTICS))


class PytoolsRenameCommand(sublime_plugin.TextCommand):
    """Diagnostic command"""

    def run(self, edit, paths: "List[str]" = None):
        logger.info("on rename")

        if all([feature_enabled(F_RENAME)]):

            view = self.view
            self.path = paths[0] if paths else None
            rename_module = True if self.path else False

            if rename_module:
                # rename module

                self.offset = None
                name, ext = os.path.splitext(os.path.basename(path))
                old_name = name

                if ext not in [".py", ".pyi", ".pyc"]:
                    logger.debug("not python file")
                    return

            else:
                # rename attribute

                view.run_command("save")  # write buffer
                selection = view.sel()[0]

                if not all([valid_source(view), valid_attribute(view, selection.a)]):
                    logger.debug("invalid view and attribute")
                    return

                self.path = view.file_name()

                if selection.size() != view.word(selection.a).size():
                    logger.debug(
                        "no selected attribute, found : %s", view.substr(selection)
                    )
                    return

                self.offset = selection.a
                old_name = view.substr(selection)

            if not server_capable(F_RENAME):
                return

            window = view.window()
            document.show_input_panel(
                window,
                "New name",
                on_done=self.on_input_name_done,
                initial_text=old_name,
            )

    def on_input_name_done(self, name):
        thread = threading.Thread(
            target=self.rename_thread, args=(self.path, self.offset, name)
        )
        thread.start()

    @staticmethod
    @instance_lock
    @request_lock
    def rename_thread(path, offset, name):
        try:
            result = client.rename(file_path=path, offset=offset, new_name=name)

        except client.ServerOffline:
            logger.debug("ServerOffline")

        except Exception:
            logger.error("rename error", exc_info=True)

        else:
            if result.error:
                logger.debug(result.error)

            else:
                # apply changes
                logger.debug(result.results)
                PytoolsRenameCommand.apply_renames(result.results)

    @staticmethod
    def apply_renames(changes: "Dict[str, Any]"):
        window = sublime.active_window()
        for change in changes:
            try:
                if change["type"] == "change":
                    view = window.open_file(change["file_name"])
                    view.run_command(
                        "pytools_apply_rpc_change", args={"changes": change["changes"]}
                    )

                elif change["type"] == "rename":
                    old_name = change["changes"]["old_name"]
                    new_name = change["changes"]["new_name"]
                    os.rename(old_name, new_name)

            except (KeyError, FileNotFoundError):
                logger.error("error apply_renames", exc_info=True)


class PytoolsApplyRpcChangeCommand(sublime_plugin.TextCommand):
    """Diagnostic command"""

    def run(self, edit, changes):
        document.apply_changes(self.view, edit, changes)


class PytoolsStateinfoCommand(sublime_plugin.WindowCommand):
    """Shutdown command"""

    def run(self):
        print(
            "SERVER_ONLINE : %s, SERVER_ERROR : %s, SERVER_CAPABILITY : %s"
            % (SERVER_ONLINE, SERVER_ERROR, SERVER_CAPABILITY)
        )
        print("DIAGNOSTICS : %s", DIAGNOSTICS)