"""tbrunner against a fake desktop: fake user32 and kernel32, never the real Win32 API.

No test here calls a real Windows function (no GetForegroundWindow, SetForegroundWindow,
SendMessage, PostMessage, EnumWindows) or starts Terrain Builder or another program;
the three TestImport tests spawn sys.executable -c to import the module in a child
Python. tbrunner.user32 is replaced by a fake that records every call and
tbrunner.kernel32, which tbrunner binds but never calls, by one that fails the
test on any call; ctypes.WinDLL, ctypes.WINFUNCTYPE and subprocess.Popen are
replaced by functions that fail the test, and the platform check is patched.
The user32 fake keeps ctypes semantics: it fills the out-parameters and the
buffers tbrunner passes, through ctypes.byref and the buffer addresses, the way
the real calls do. Stdlib only; runs on any OS.
"""

from __future__ import annotations

import contextlib
import ctypes
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


TOOL_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))

import tbrunner  # noqa: E402


WM_NULL, WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x0, 0xC, 0xD, 0xE
WM_CLOSE, WM_COMMAND, WM_INITMENUPOPUP = 0x10, 0x111, 0x117
MFT_SEPARATOR, MFT_OWNERDRAW, MFS_DISABLED = 0x800, 0x100, 0x3
TB_PID, OTHER_PID = 4242, 1717

VERBS = [
    ["launch"],
    ["windows"],
    ["menu"],
    ["command", "101"],
    ["dialog_file", "project.tv4p"],
    ["dialog_button", "1"],
    ["wait_log", "Import", "1"],
    ["save_loop", "105", "project.tv4p", "1"],
    ["close"],
    ["probe", "File"],
]


def _forbidden(name):
    def call(*args, **kwargs):
        raise AssertionError(f"a test reached {name}")

    return call


class Window:
    def __init__(self, hwnd, cls, text, pid, visible, enabled, ctrl_id, parent, menu):
        self.hwnd, self.cls, self.text, self.pid = hwnd, cls, text, pid
        self.visible, self.enabled, self.ctrl_id = visible, enabled, ctrl_id
        self.parent, self.menu, self.children = parent, menu, []


class FakeKernel32:
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"tbrunner called kernel32.{name}")


class FakeUser32:
    """The user32 calls tbrunner makes, over a small in-memory desktop."""

    def __init__(self):
        self.windows = {}
        self.top = []
        self.menus = {}
        self.calls = []
        self.posted = []
        self.sent = []
        self.foreground = self.add(0x9000, "ConsoleWindowClass", "a terminal", pid=OTHER_PID)

    def add(self, hwnd, cls, text="", *, parent=None, pid=None, visible=True, enabled=True, ctrl_id=0, menu=None):
        if pid is None:
            pid = self.windows[parent].pid if parent is not None else TB_PID
        self.windows[hwnd] = Window(hwnd, cls, text, pid, visible, enabled, ctrl_id, parent, menu)
        if parent is None:
            self.top.append(hwnd)
        else:
            self.windows[parent].children.append(hwnd)
        return hwnd

    def _log(self, name, *args):
        self.calls.append((name, *args))

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"tbrunner called user32.{name}, which the fake does not provide")

    # Windows

    def EnumWindows(self, proc, lparam):
        self._log("EnumWindows")
        for hwnd in list(self.top):
            if not proc(hwnd, lparam):
                break
        return 1

    def EnumChildWindows(self, hwnd, proc, lparam):
        self._log("EnumChildWindows", hwnd)

        def walk(parent):
            for child in self.windows[parent].children:
                yield child
                yield from walk(child)

        for child in list(walk(hwnd)):
            if not proc(child, lparam):
                break
        return 1

    def GetWindowThreadProcessId(self, hwnd, pid_ref):
        self._log("GetWindowThreadProcessId", hwnd)
        window = self.windows.get(hwnd)
        if window is None:
            return 0
        pid_ref._obj.value = window.pid
        return 1

    def GetClassNameW(self, hwnd, buffer, size):
        self._log("GetClassNameW", hwnd)
        buffer.value = self.windows[hwnd].cls[: size - 1]
        return len(buffer.value)

    def IsWindowVisible(self, hwnd):
        self._log("IsWindowVisible", hwnd)
        return int(self.windows[hwnd].visible)

    def IsWindowEnabled(self, hwnd):
        self._log("IsWindowEnabled", hwnd)
        return int(self.windows[hwnd].enabled)

    def GetDlgCtrlID(self, hwnd):
        self._log("GetDlgCtrlID", hwnd)
        window = self.windows.get(hwnd)
        return 0 if window is None else window.ctrl_id

    def GetParent(self, hwnd):
        self._log("GetParent", hwnd)
        window = self.windows.get(hwnd)
        return None if window is None else window.parent

    def IsHungAppWindow(self, hwnd):
        self._log("IsHungAppWindow", hwnd)
        return 0

    def GetForegroundWindow(self):
        self._log("GetForegroundWindow")
        return self.foreground

    def GetCursorPos(self, point_ref):
        self._log("GetCursorPos")
        point_ref._obj.x, point_ref._obj.y = 640, 360
        return 1

    def SetWindowPos(self, hwnd, after, x, y, cx, cy, flags):
        self._log("SetWindowPos", hwnd, flags)
        return 1

    # Messages

    def PostMessageW(self, hwnd, message, wparam, lparam):
        self._log("PostMessageW", hwnd, message, wparam, lparam)
        self.posted.append((hwnd, message, wparam, lparam))
        return 1

    def SendMessageTimeoutW(self, hwnd, message, wparam, lparam, flags, timeout, result_ref):
        self._log("SendMessageTimeoutW", hwnd, message)
        window = self.windows.get(hwnd)
        if window is None:
            return 0
        if message == WM_NULL:
            return 1
        if message == WM_GETTEXTLENGTH:
            result_ref._obj.value = len(window.text)
            return 1
        if message == WM_GETTEXT:
            text = window.text[: max(int(wparam) - 1, 0)]
            data = ctypes.create_unicode_buffer(text)
            ctypes.memmove(lparam.value, data, ctypes.sizeof(data))
            result_ref._obj.value = len(text)
            return 1
        if message == WM_SETTEXT:
            window.text = ctypes.wstring_at(lparam.value)
            self.sent.append((hwnd, message, window.text))
            return 1
        if message == WM_INITMENUPOPUP:
            self.sent.append((hwnd, message, int(wparam), lparam.value or 0))
            return 1
        raise AssertionError(f"unexpected message {message:#x}")

    # Menus

    def GetMenu(self, hwnd):
        self._log("GetMenu", hwnd)
        window = self.windows.get(hwnd)
        return None if window is None else window.menu

    def GetMenuItemCount(self, hmenu):
        self._log("GetMenuItemCount", hmenu)
        return len(self.menus[hmenu]) if hmenu in self.menus else -1

    def GetSubMenu(self, hmenu, index):
        self._log("GetSubMenu", hmenu, index)
        return self.menus[hmenu][index].get("submenu")

    def GetMenuItemInfoW(self, hmenu, index, by_position, info_ref):
        self._log("GetMenuItemInfoW", hmenu, index)
        item = self.menus[hmenu][index]
        if item.get("fail"):
            return 0
        info = info_ref._obj
        address = ctypes.c_void_p.from_buffer(info, type(info).dwTypeData.offset).value
        if item.get("label") and not item.get("ftype", 0) & MFT_OWNERDRAW:
            data = ctypes.create_unicode_buffer(item["label"])
            ctypes.memmove(address, data, ctypes.sizeof(data))
        info.wID = item.get("id", 0)
        info.fType = item.get("ftype", 0)
        info.fState = item.get("fstate", 0)
        info.hSubMenu = item.get("submenu")
        return 1


def tb_menu(user32):
    """File > Open..., a separator, Export > SHP... (disabled) and an owner-draw item; Help > About."""
    user32.menus[0x100] = [{"label": "&File", "submenu": 0x110}, {"label": "&Help", "submenu": 0x130}]
    user32.menus[0x110] = [
        {"label": "&Open...", "id": 101},
        {"ftype": MFT_SEPARATOR},
        {"label": "E&xport", "submenu": 0x120},
    ]
    user32.menus[0x120] = [
        {"label": "SHP...", "id": 201, "fstate": MFS_DISABLED},
        {"id": 202, "ftype": MFT_OWNERDRAW},
    ]
    user32.menus[0x130] = [{"label": "&About", "id": 301}]
    return 0x100


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = tbrunner.main([str(item) for item in argv])
        except SystemExit as exit_:
            code = exit_.code
    return code, stdout.getvalue(), stderr.getvalue()


class _Desktop(unittest.TestCase):
    """A fake desktop holding one Terrain Builder frame of pid TB_PID, and another app's window."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.exe = self.root / "DayZ Tools" / "Bin" / "TerrainBuilder" / "terrainBuilder.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"not a program")
        self.state = self.root / "state" / "tbrunner-state.json"
        self.state.parent.mkdir()
        self.user32 = FakeUser32()
        self.user32.add(0x0300, "wxWindowClassNR", "Terrain Builder - not ours", pid=OTHER_PID, menu=None)
        self.frame = self.user32.add(0x1000, "wxWindowClassNR", "Terrain Builder - fixture", menu=tb_menu(self.user32))
        environment = {key: value for key, value in os.environ.items() if key != "TBRUNNER_TB_EXE"}
        for patch in (
            mock.patch.object(tbrunner, "user32", self.user32),
            mock.patch.object(tbrunner, "kernel32", FakeKernel32()),
            mock.patch.object(tbrunner, "EnumProc", lambda function: function),
            mock.patch.object(tbrunner, "on_windows", lambda: True),
            mock.patch.object(tbrunner, "STATE", self.state),
            mock.patch.object(tbrunner, "HERE", self.state.parent),
            mock.patch.object(tbrunner, "TB_EXE", None),
            mock.patch.object(tbrunner, "LOGS", None),
            mock.patch.object(tbrunner.time, "sleep", lambda seconds: None),
            mock.patch.object(ctypes, "WinDLL", _forbidden("ctypes.WinDLL"), create=True),
            mock.patch.object(ctypes, "WINFUNCTYPE", _forbidden("ctypes.WINFUNCTYPE"), create=True),
            mock.patch.object(subprocess, "Popen", _forbidden("subprocess.Popen")),
            mock.patch.dict(os.environ, environment, clear=True),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        self._tmp.cleanup()

    def record(self, **state):
        state.setdefault("pid", TB_PID)
        self.state.write_text(json.dumps(state), encoding="utf-8")

    def tb(self, *argv):
        return run(["--tb-exe", self.exe, *argv])


class TestImport(unittest.TestCase):
    def isolated(self, code, **environment):
        script = textwrap.dedent(
            """
            import ctypes, sys
            def forbidden(*args, **kwargs):
                raise AssertionError("Win32 bound at import")
            ctypes.WinDLL = ctypes.WINFUNCTYPE = forbidden
            sys.path.insert(0, sys.argv[1])
            import tbrunner
            """
        ) + textwrap.dedent(code)
        env = {key: value for key, value in os.environ.items() if key != "TBRUNNER_STATE"}
        env.update(environment)
        return subprocess.run(
            [sys.executable, "-c", script, str(TOOL_ROOT)], capture_output=True, text=True, env=env
        )

    def test_imports_on_any_os_without_binding_win32(self):
        result = self.isolated("print(tbrunner.user32, tbrunner.kernel32, tbrunner.EnumProc, tbrunner.TB_EXE)")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("None None None None", result.stdout.strip())

    def test_state_path_from_TBRUNNER_STATE(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = pathlib.Path(tmp) / "runs" / "tb-state.json"

            result = self.isolated("print(tbrunner.STATE); print(tbrunner.HERE)", TBRUNNER_STATE=str(state))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([str(state), str(state.parent)], result.stdout.splitlines())

    def test_default_state_path_is_in_the_temp_directory(self):
        result = self.isolated("import tempfile; print(tbrunner.STATE == tbrunner.Path(tempfile.gettempdir()) / 'tbrunner-state.json')")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("True", result.stdout.strip())


class TestRefusals(_Desktop):
    def test_every_command_refuses_off_windows(self):
        for argv in VERBS:
            with self.subTest(command=argv[0]), mock.patch.object(tbrunner, "on_windows", lambda: False), \
                    mock.patch.object(tbrunner, "user32", None), mock.patch.object(tbrunner, "kernel32", None), \
                    mock.patch.object(tbrunner, "EnumProc", None):
                code, _, stderr = self.tb(*argv)

                self.assertEqual(1, code)
                self.assertIn("Windows", stderr)
                self.assertIsNone(tbrunner.user32)
        self.assertEqual([], self.user32.calls)
        self.assertFalse(self.state.exists())

    def test_no_command_without_the_exe(self):
        for argv in VERBS:
            with self.subTest(command=argv[0]):
                code, _, stderr = run(argv)

                self.assertEqual(2, code)
                self.assertIn("TBRUNNER_TB_EXE", stderr)
        self.assertEqual([], self.user32.calls)

    def test_exe_from_the_environment_and_the_flag_wins(self):
        self.record()
        other = self.root / "elsewhere" / "terrainBuilder.exe"
        with mock.patch.dict(os.environ, {"TBRUNNER_TB_EXE": str(self.exe)}):
            self.assertEqual(0, run(["windows"])[0])
            self.assertEqual((self.exe, self.exe.parent / "Logs"), (tbrunner.TB_EXE, tbrunner.LOGS))

            self.assertEqual(0, run(["--tb-exe", other, "windows"])[0])
            self.assertEqual(other, tbrunner.TB_EXE)

    def test_launch_refused_while_a_pid_is_recorded(self):
        self.record(pid=TB_PID)

        code, _, stderr = self.tb("launch")

        self.assertEqual(1, code)
        self.assertIn("already recorded", stderr)
        self.assertEqual({"pid": TB_PID}, json.loads(self.state.read_text(encoding="utf-8")))

    def test_launch_refused_when_the_exe_is_not_a_file(self):
        code, _, stderr = run(["--tb-exe", self.root / "missing.exe", "launch"])

        self.assertEqual(1, code)
        self.assertIn("not a file", stderr)
        self.assertFalse(self.state.exists())

    def test_commands_need_a_recorded_instance(self):
        for argv in VERBS[1:]:
            with self.subTest(command=argv[0]):
                code, _, stderr = self.tb(*argv)

                self.assertEqual(1, code)
                self.assertIn("no Terrain Builder instance recorded", stderr)
        self.assertEqual([], self.user32.posted)

    def test_log_commands_need_a_recorded_log(self):
        self.record(log=None)
        for argv in (["wait_log", "Import", "1"], ["probe", "File"]):
            with self.subTest(command=argv[0]):
                code, _, stderr = self.tb(*argv)

                self.assertEqual(1, code)
                self.assertIn("no log", stderr)
        self.assertEqual([], self.user32.posted)

    def test_a_missing_frame_is_an_error(self):
        self.record(pid=999)
        for argv in (["menu"], ["command", "101"], ["save_loop", "105", "p.tv4p", "1"]):
            with self.subTest(command=argv[0]):
                code, _, stderr = self.tb(*argv)

                self.assertEqual(1, code)
                self.assertIn("frame", stderr)
        self.assertEqual([], self.user32.posted)

    def test_usage_errors_exit_2(self):
        for argv in (["nonsense"], ["command", "Open"], ["wait_log", "x"], []):
            with self.subTest(argv=argv):
                self.assertEqual(2, self.tb(*argv)[0])


class TestMenus(_Desktop):
    def test_menu_tree_and_flatten(self):
        tree = tbrunner.menu_tree(0x100)
        flat = [(" > ".join(item["path"]), item["id"], item["separator"], item["ownerdraw"], item["disabled"],
                 "submenu" in item) for item in tbrunner.flatten(tree)]

        self.assertEqual(
            [
                ("File", 0, False, False, False, True),
                ("File > Open...", 101, False, False, False, False),
                ("File > #1", 0, True, False, False, False),
                ("File > Export", 0, False, False, False, True),
                ("File > Export > SHP...", 201, False, False, True, False),
                ("File > Export > #1", 202, False, True, False, False),
                ("Help", 0, False, False, False, True),
                ("Help > About", 301, False, False, False, False),
            ],
            flat,
        )

    def test_an_unreadable_item_is_kept_with_its_error(self):
        self.user32.menus[0x130].append({"fail": True})
        with mock.patch.object(ctypes, "get_last_error", lambda: 1400, create=True):
            tree = tbrunner.menu_tree(0x100)

        self.assertEqual({"path": ["Help", "#1"], "error": 1400}, tree[1]["submenu"][1])

    def test_menu_prints_an_unreadable_item_and_exits_0(self):
        self.record()
        self.user32.menus[0x130].append({"fail": True})
        with mock.patch.object(ctypes, "get_last_error", lambda: 1400, create=True):
            code, stdout, stderr = self.tb("menu")

        self.assertEqual(0, code, stderr)
        self.assertIn("unreadable, GetMenuItemInfoW error 1400", stdout)
        self.assertEqual([], self.user32.posted)

    def test_probe_skips_an_unreadable_item(self):
        self.record()
        self.user32.menus[0x130].append({"fail": True})
        with mock.patch.object(ctypes, "get_last_error", lambda: 1400, create=True):
            code, stdout, stderr = self.tb("probe", "Help > #1")

        self.assertEqual(0, code, stderr)
        self.assertEqual([], json.loads(stdout))
        self.assertEqual([], self.user32.posted)

    def test_probe_without_a_log_and_no_matches_prints_empty(self):
        self.record(log=None)

        code, stdout, stderr = self.tb("probe", "NoSuchMenu")

        self.assertEqual(0, code, stderr)
        self.assertEqual([], json.loads(stdout))
        self.assertEqual([], self.user32.posted)

    def test_probe_without_a_log_refuses_an_enabled_leaf(self):
        self.record(log=None)

        code, _, stderr = self.tb("probe", "File > Open...")

        self.assertEqual(1, code)
        self.assertIn("no log", stderr)
        self.assertEqual([], self.user32.posted)

    def test_close_posts_wm_close_to_the_recorded_frame(self):
        self.record()

        code, _, stderr = self.tb("close")

        self.assertEqual(0, code, stderr)
        self.assertEqual([(self.frame, WM_CLOSE, 0, 0)], self.user32.posted)

    def test_dialog_button_posts_wm_command_to_the_open_dialog(self):
        self.record()
        dialog = self.user32.add(0x500, "#32770", "Message")
        self.user32.add(0x501, "Button", "Ok", parent=dialog, ctrl_id=2)

        code, _, stderr = self.tb("dialog_button", "2")

        self.assertEqual(0, code, stderr)
        self.assertEqual([(dialog, WM_COMMAND, 2, 0x501)], self.user32.posted)

    def test_save_loop_counts_a_changed_file_without_focus_or_dialog(self):
        self.record()
        tv4p = self.root / "p.tv4p"
        tv4p.write_bytes(b"v1")
        original = self.user32.PostMessageW

        def bump_mtime(hwnd, message, wparam, lparam):
            result = original(hwnd, message, wparam, lparam)
            tv4p.write_bytes(b"v2")
            return result

        self.user32.PostMessageW = bump_mtime

        code, stdout, stderr = self.tb("save_loop", "105", str(tv4p), "1")

        self.assertEqual(0, code, stderr)
        decoder, idx, objects = json.JSONDecoder(), 0, []
        while idx < len(stdout):
            while idx < len(stdout) and stdout[idx].isspace():
                idx += 1
            if idx >= len(stdout):
                break
            obj, idx = decoder.raw_decode(stdout, idx)
            objects.append(obj)
        report = next(obj for obj in objects if isinstance(obj, dict) and "passed" in obj)
        self.assertEqual(1, report["passed"])
        self.assertEqual(1, report["of"])
        self.assertEqual([(self.frame, WM_COMMAND, 105, 0)], self.user32.posted)

    def test_menu_prints_the_leaves_and_writes_menu_json(self):
        self.record()

        code, stdout, stderr = self.tb("menu")

        self.assertEqual(0, code, stderr)
        self.assertEqual(
            ["101 File > Open...", "201 File > Export > SHP... (disabled)", "202 File > Export > #1 (ownerdraw)",
             "301 Help > About"],
            [" ".join(line.split()) for line in stdout.splitlines()],
        )
        saved = json.loads((self.state.parent / "menu.json").read_text(encoding="utf-8"))
        self.assertEqual(["File", "Open..."], saved[0]["submenu"][0]["path"])
        self.assertEqual([], self.user32.posted)

    def test_command_refreshes_the_menus_then_posts_to_the_recorded_frame_only(self):
        self.record()

        code, stdout, stderr = self.tb("command", "101")

        self.assertEqual(0, code, stderr)
        self.assertEqual(
            [(self.frame, WM_INITMENUPOPUP, 0x110, 0), (self.frame, WM_INITMENUPOPUP, 0x130, 1)],
            [item for item in self.user32.sent if item[1] == WM_INITMENUPOPUP],
        )
        self.assertEqual([(self.frame, WM_COMMAND, 101, 0)], self.user32.posted)
        refresh_and_post = {("SendMessageTimeoutW", self.frame, WM_INITMENUPOPUP), ("PostMessageW", self.frame, WM_COMMAND)}
        self.assertEqual(
            ["SendMessageTimeoutW", "SendMessageTimeoutW", "PostMessageW"],
            [call[0] for call in self.user32.calls if call[:3] in refresh_and_post],
        )
        self.assertEqual({"path": "File > Open...", "disabled": False}, json.loads(stdout.splitlines()[0])["item"])

    def test_command_refused_while_a_dialog_is_open(self):
        self.record()
        self.user32.add(0x2000, "#32770", "Import")

        code, _, stderr = self.tb("command", "101")

        self.assertEqual(1, code)
        self.assertIn("dialog", stderr)
        self.assertEqual([], self.user32.posted)

    def test_windows_lists_the_recorded_instance_only(self):
        self.record()

        code, stdout, stderr = self.tb("windows")

        self.assertEqual(0, code, stderr)
        report = json.loads(stdout)
        self.assertEqual([self.frame], [item["hwnd"] for item in report["windows"]])
        self.assertTrue(report["frame_responsive"])
        self.assertEqual(OTHER_PID, report["desktop"]["foreground_pid"])
        self.assertEqual([], self.user32.posted)


class TestFileDialogs(_Desktop):
    def open_dialog(self):
        add = self.user32.add
        dialog = add(0x500, "#32770", "Abrir")
        add(0x520, "Edit", "", parent=dialog, ctrl_id=1152, visible=False)
        add(0x530, "Edit", "search", parent=dialog, ctrl_id=1234)
        combo_ex = add(0x510, "ComboBoxEx32", "", parent=dialog, ctrl_id=1148)
        combo = add(0x511, "ComboBox", "", parent=combo_ex, ctrl_id=0)
        add(0x512, "Edit", "", parent=combo, ctrl_id=1001)
        add(0x540, "Button", "&Abrir", parent=dialog, ctrl_id=1)
        add(0x541, "Button", "Cancelar", parent=dialog, ctrl_id=2)
        return dialog

    def save_dialog(self):
        add = self.user32.add
        dialog = add(0x600, "#32770", "Guardar como")
        view = add(0x610, "DUIViewWndClassName", "", parent=dialog)
        add(0x620, "Edit", "", parent=view, ctrl_id=1001)
        combo = add(0x611, "ComboBox", "", parent=view, ctrl_id=1001)
        add(0x612, "Edit", "", parent=combo, ctrl_id=1001)
        add(0x640, "Button", "&Guardar", parent=dialog, ctrl_id=1)
        return dialog

    def test_open_dialog_filename_edit(self):
        self.assertEqual(0x512, tbrunner.find_file_edit(self.open_dialog()))

    def test_save_dialog_filename_edit(self):
        self.assertEqual(0x612, tbrunner.find_file_edit(self.save_dialog()))

    def test_no_filename_edit(self):
        dialog = self.user32.add(0x700, "#32770", "Message")
        self.user32.add(0x701, "Button", "Ok", parent=dialog, ctrl_id=2)

        self.assertIsNone(tbrunner.find_file_edit(dialog))

    def test_dialog_file_sets_the_name_and_confirms_by_the_ok_id(self):
        self.record()
        dialog = self.open_dialog()
        target = r"work\fixture\project.tv4p"

        code, stdout, stderr = self.tb("dialog_file", target)

        self.assertEqual(0, code, stderr)
        self.assertEqual([(0x512, WM_SETTEXT, target)], [item for item in self.user32.sent if item[1] == WM_SETTEXT])
        self.assertEqual(target, json.loads(stdout)["readback"])
        self.assertEqual([(dialog, WM_COMMAND, 1, 0x540)], self.user32.posted)

    def test_dialog_file_needs_exactly_one_dialog(self):
        self.record()
        code, _, stderr = self.tb("dialog_file", "x.tv4p")
        self.assertEqual(1, code)
        self.assertIn("expected one dialog, found 0", stderr)

        self.open_dialog()
        self.save_dialog()
        code, _, stderr = self.tb("dialog_file", "x.tv4p")
        self.assertEqual(1, code)
        self.assertIn("found 2", stderr)
        self.assertEqual([], self.user32.posted)

    def test_dialog_file_without_a_filename_edit_is_an_error(self):
        self.record()
        dialog = self.user32.add(0x700, "#32770", "Message")
        self.user32.add(0x701, "Button", "Ok", parent=dialog, ctrl_id=2)

        code, _, stderr = self.tb("dialog_file", "x.tv4p")

        self.assertEqual(1, code)
        self.assertIn("filename edit not found", stderr)
        self.assertEqual([], self.user32.posted)


class TestPressByLabel(_Desktop):
    def tb_dialog(self, labels):
        dialog = self.user32.add(0x800, "#32770", "Terrain Builder dialog")
        for offset, (label, ctrl_id, visible) in enumerate(labels, start=1):
            self.user32.add(0x800 + offset, "Button", label, parent=dialog, ctrl_id=ctrl_id, visible=visible)
        self.user32.add(0x8FF, "Static", "Cancel", parent=dialog, ctrl_id=1)
        return dialog

    def test_swapped_ids_are_pressed_by_label(self):
        # Terrain Builder's own dialogs carry Ok = 2 and Cancel = 1, the reverse of IDOK and IDCANCEL.
        dialog = self.tb_dialog([("Ok", 2, True), ("Cancel", 1, True)])

        self.assertTrue(tbrunner.press_label(dialog, tbrunner.CANCEL_LABELS))
        self.assertTrue(tbrunner.press_label(dialog, tbrunner.OK_LABELS))

        self.assertEqual([(dialog, WM_COMMAND, 1, 0x802), (dialog, WM_COMMAND, 2, 0x801)], self.user32.posted)

    def test_spanish_labels_and_mnemonics(self):
        dialog = self.tb_dialog([("&Guardar", 6, True), ("Cancelar", 9, True)])

        self.assertTrue(tbrunner.press_label(dialog, tbrunner.OK_LABELS))
        self.assertTrue(tbrunner.press_label(dialog, tbrunner.CANCEL_LABELS))

        self.assertEqual([(dialog, WM_COMMAND, 6, 0x801), (dialog, WM_COMMAND, 9, 0x802)], self.user32.posted)

    def test_hidden_buttons_and_other_controls_are_never_pressed(self):
        dialog = self.tb_dialog([("Cancel", 7, False), ("Help", 3, True)])

        self.assertFalse(tbrunner.press_label(dialog, tbrunner.CANCEL_LABELS))
        self.assertEqual([], self.user32.posted)


class TestLog(_Desktop):
    def test_wait_log_reads_the_recorded_log_next_to_the_exe(self):
        logs = self.exe.parent / "Logs"
        logs.mkdir()
        (logs / "terrainbuilder_fixture.rpt").write_text("start\nImport finished\n", encoding="latin-1")
        self.record(log="terrainbuilder_fixture.rpt")

        code, stdout, stderr = self.tb("wait_log", "Import \\w+", "1")

        self.assertEqual(0, code, stderr)
        self.assertEqual({"found": True, "match": "Import finished"}, {k: v for k, v in json.loads(stdout).items() if k != "seconds"})
        self.assertEqual([], self.user32.calls)

    def test_a_bad_pattern_is_an_error(self):
        logs = self.exe.parent / "Logs"
        logs.mkdir()
        (logs / "terrainbuilder_fixture.rpt").write_text("start\n", encoding="latin-1")
        self.record(log="terrainbuilder_fixture.rpt")

        code, _, stderr = self.tb("wait_log", "(unclosed", "1")

        self.assertEqual(1, code)
        self.assertTrue(stderr.startswith("error: "), stderr)


if __name__ == "__main__":
    unittest.main()
