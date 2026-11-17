"""EXPERIMENTAL: drive a Terrain Builder instance this runner launched, by Win32 messages only.

Status 2026-10-03: menus and standard file dialogs verified without taking focus after
launch (see README.md). Generate Layers, a real import and an end-to-end WRP export are
NOT driven by this tool yet.

No SendInput, no SetCursorPos, no SetForegroundWindow. Menu commands go through
PostMessage(WM_COMMAND), which wx 2.8.12 wxFrame::HandleCommand processes without a focus
check (src/msw/frame.cpp:951-979). File dialogs are filled with WM_SETTEXT; dialog_file
confirms with the OK by id 1 (standard Windows dialogs; Terrain Builder's own swap the
Ok and Cancel ids). probe cancels by label. Only the instance recorded in the state file is ever addressed. Back up and
restore Bin/TerrainBuilder *.opt and Proj.vdat around a run: TB rewrites them on exit.

Windows only. The module imports on any OS; the Win32 functions are bound when a command
runs, and every command refuses off Windows. The executable comes from --tb-exe or the
TBRUNNER_TB_EXE environment variable; there is no default path.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import os
import tempfile

STATE = Path(os.environ.get('TBRUNNER_STATE', Path(tempfile.gettempdir()) / 'tbrunner-state.json'))
HERE = STATE.parent
TB_EXE = None  # set by main() from --tb-exe or TBRUNNER_TB_EXE
LOGS = None  # TB_EXE.parent / 'Logs'

user32 = None  # bound by _win32() when a command runs on Windows
kernel32 = None
EnumProc = None

WM_NULL, WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, WM_CLOSE, WM_COMMAND = 0x0, 0xC, 0xD, 0xE, 0x10, 0x111
SMTO_ABORTIFHUNG = 0x2
SW_SHOWNOACTIVATE = 4
STARTF_USESHOWWINDOW = 0x1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
MIIM_STATE, MIIM_ID, MIIM_SUBMENU, MIIM_STRING, MIIM_FTYPE = 0x1, 0x2, 0x4, 0x40, 0x100
MFT_SEPARATOR, MFT_OWNERDRAW = 0x800, 0x100
MFS_DISABLED = 0x3


class RunnerError(Exception):
    """A command refused or unable to go on; the message says why."""


class MENUITEMINFOW(ctypes.Structure):
    _fields_ = [('cbSize', wt.UINT), ('fMask', wt.UINT), ('fType', wt.UINT), ('fState', wt.UINT),
                ('wID', wt.UINT), ('hSubMenu', wt.HMENU), ('hbmpChecked', wt.HBITMAP),
                ('hbmpUnchecked', wt.HBITMAP), ('dwItemData', ctypes.c_size_t), ('dwTypeData', wt.LPWSTR),
                ('cch', wt.UINT), ('hbmpItem', wt.HBITMAP)]


def on_windows():
    return sys.platform == 'win32'


def _win32():
    """Bind user32 and kernel32 on first use; refuse off Windows."""
    global user32, kernel32, EnumProc
    if not on_windows():
        raise RunnerError(f'tbrunner drives Terrain Builder through Win32 messages and runs on Windows only '
                          f'(this is {sys.platform})')
    if user32 is not None:
        return
    lib = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    lib.EnumWindows.argtypes = [EnumProc, wt.LPARAM]
    lib.EnumChildWindows.argtypes = [wt.HWND, EnumProc, wt.LPARAM]
    lib.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    lib.GetWindowThreadProcessId.restype = wt.DWORD
    lib.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    lib.IsWindowVisible.argtypes = [wt.HWND]
    lib.IsWindowEnabled.argtypes = [wt.HWND]
    lib.GetDlgCtrlID.argtypes = [wt.HWND]
    lib.GetParent.argtypes = [wt.HWND]
    lib.GetParent.restype = wt.HWND
    lib.GetMenu.argtypes = [wt.HWND]
    lib.GetMenu.restype = wt.HMENU
    lib.GetMenuItemCount.argtypes = [wt.HMENU]
    lib.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    lib.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, ctypes.c_void_p, wt.UINT, wt.UINT,
                                        ctypes.POINTER(ctypes.c_size_t)]
    lib.SendMessageTimeoutW.restype = ctypes.c_size_t
    lib.IsHungAppWindow.argtypes = [wt.HWND]
    lib.GetForegroundWindow.restype = wt.HWND
    lib.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
    lib.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
    lib.GetMenuItemInfoW.argtypes = [wt.HMENU, wt.UINT, wt.BOOL, ctypes.POINTER(MENUITEMINFOW)]
    lib.GetSubMenu.argtypes = [wt.HMENU, ctypes.c_int]
    lib.GetSubMenu.restype = wt.HMENU
    user32 = lib


def load_state():
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding='utf-8'))
    except ValueError as error:
        raise RunnerError(f'state file {STATE} is not JSON: {error}') from error


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _require_pid(state):
    if not state.get('pid'):
        raise RunnerError(f'no Terrain Builder instance recorded in {STATE}; run launch first')
    return state['pid']


def _require_log(state):
    _require_pid(state)
    if not state.get('log'):
        raise RunnerError(f'no log recorded for pid {state["pid"]} in {STATE}: launch saw no new .rpt in {LOGS}')
    return LOGS / state['log']


def _require_frame(state):
    f = frame(state)
    if not f:
        raise RunnerError(f'no Terrain Builder frame found for pid {state["pid"]}')
    return f


def pid_of(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def text_of(hwnd, timeout_ms=2000):
    n = ctypes.c_size_t()
    if not user32.SendMessageTimeoutW(hwnd, WM_GETTEXTLENGTH, 0, None, SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(n)):
        return None
    buf = ctypes.create_unicode_buffer(n.value + 2)
    if not user32.SendMessageTimeoutW(hwnd, WM_GETTEXT, n.value + 1, ctypes.cast(buf, ctypes.c_void_p),
                                      SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(ctypes.c_size_t())):
        return None
    return buf.value


def top_windows(pid, visible_only=True):
    found = []

    def cb(hwnd, _):
        if pid_of(hwnd) == pid and (user32.IsWindowVisible(hwnd) or not visible_only):
            found.append(hwnd)
        return True
    user32.EnumWindows(EnumProc(cb), 0)
    return found


def child_windows(hwnd):
    found = []

    def cb(h, _):
        found.append(h)
        return True
    user32.EnumChildWindows(hwnd, EnumProc(cb), 0)
    return found


def describe(hwnd):
    return dict(hwnd=int(hwnd), cls=class_name(hwnd), text=text_of(hwnd), visible=bool(user32.IsWindowVisible(hwnd)),
                enabled=bool(user32.IsWindowEnabled(hwnd)), id=user32.GetDlgCtrlID(hwnd))


def desktop_state():
    fg = user32.GetForegroundWindow()
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return dict(foreground=int(fg or 0), foreground_pid=pid_of(fg) if fg else None,
                foreground_cls=class_name(fg) if fg else None, cursor=[pt.x, pt.y])


def frame(state):
    for hwnd in top_windows(state['pid']):
        title = text_of(hwnd) or ''
        if title.startswith('Terrain Builder'):
            return hwnd
    return None


def dialogs(state):
    return [h for h in top_windows(state['pid']) if class_name(h) == '#32770']


def responsive(hwnd, timeout_ms=1000):
    r = ctypes.c_size_t()
    ok = user32.SendMessageTimeoutW(hwnd, WM_NULL, 0, None, SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(r))
    return bool(ok) and not user32.IsHungAppWindow(hwnd)


def menu_tree(hmenu, path=()):
    items = []
    for i in range(user32.GetMenuItemCount(hmenu)):
        buf = ctypes.create_unicode_buffer(512)
        info = MENUITEMINFOW(cbSize=ctypes.sizeof(MENUITEMINFOW),
                             fMask=MIIM_ID | MIIM_SUBMENU | MIIM_STRING | MIIM_FTYPE | MIIM_STATE,
                             dwTypeData=ctypes.cast(buf, wt.LPWSTR), cch=511)
        if not user32.GetMenuItemInfoW(hmenu, i, True, ctypes.byref(info)):
            items.append(dict(path=list(path) + [f'#{i}'], error=ctypes.get_last_error()))
            continue
        label = buf.value.replace('&', '')
        entry = dict(path=list(path) + [label or f'#{i}'], id=info.wID, separator=bool(info.fType & MFT_SEPARATOR),
                     ownerdraw=bool(info.fType & MFT_OWNERDRAW), disabled=bool(info.fState & MFS_DISABLED))
        if info.hSubMenu:
            entry['submenu'] = menu_tree(info.hSubMenu, tuple(entry['path']))
        items.append(entry)
    return items


def flatten(items):
    for e in items:
        yield e
        yield from flatten(e.get('submenu', []))


def find_file_edit(dlg):
    """Filename box of a common file dialog: Edit under ComboBoxEx32/ComboBox id 1148, else edt1 (1152)."""
    edits = [h for h in child_windows(dlg) if class_name(h) == 'Edit' and user32.IsWindowVisible(h)]
    for h in edits:  # open dialogs: ComboBoxEx32 1148 > ComboBox > Edit
        p = user32.GetParent(h)
        if user32.GetDlgCtrlID(h) in (1148, 1152) or (p and 1148 in (user32.GetDlgCtrlID(p),
                                                                     user32.GetDlgCtrlID(user32.GetParent(p)))):
            return h
    for h in edits:  # save dialogs: ComboBox > Edit 1001
        p = user32.GetParent(h)
        if user32.GetDlgCtrlID(h) == 1001 and p and class_name(p) == 'ComboBox':
            return h
    return None


def latest_log():
    logs = sorted(LOGS.glob('terrainbuilder_*.rpt'), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def cmd_launch():
    state = load_state()
    if state.get('pid'):
        raise RunnerError(f'an instance is already recorded (pid {state["pid"]}) in {STATE}; close it first')
    if not TB_EXE.is_file():
        raise RunnerError(f'Terrain Builder executable {TB_EXE} is not a file (--tb-exe or TBRUNNER_TB_EXE)')
    before = desktop_state()
    si = subprocess.STARTUPINFO()
    si.dwFlags = STARTF_USESHOWWINDOW
    si.wShowWindow = SW_SHOWNOACTIVATE
    logs_before = {p.name for p in LOGS.glob('*.rpt')}
    proc = subprocess.Popen([str(TB_EXE)], cwd=str(TB_EXE.parent), startupinfo=si)
    state = dict(pid=proc.pid, launched=time.time(), logs_before=sorted(logs_before))
    save_state(state)
    hwnd, t0 = None, time.time()
    while time.time() - t0 < 90:
        hwnd = frame(state)
        if hwnd and responsive(hwnd):
            break
        time.sleep(0.5)
    if hwnd:
        user32.SetWindowPos(hwnd, wt.HWND(1), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    new_logs = sorted({p.name for p in LOGS.glob('*.rpt')} - logs_before)
    state.update(frame=int(hwnd or 0), log=new_logs[-1] if new_logs else None)
    save_state(state)
    print(json.dumps(dict(pid=proc.pid, frame=int(hwnd or 0), seconds=round(time.time() - t0, 1), log=state['log'],
                          desktop_before=before, desktop_after=desktop_state(),
                          windows=[describe(h) for h in top_windows(proc.pid)]), indent=1))


def cmd_windows():
    state = load_state()
    _require_pid(state)
    out = []
    for h in top_windows(state['pid']):
        d = describe(h)
        if d['cls'] == '#32770':
            d['children'] = [describe(k) for k in child_windows(h)
                             if class_name(k) in ('Static', 'Button', 'Edit', 'ComboBoxEx32')]
        out.append(d)
    f = frame(state)
    print(json.dumps(dict(windows=out, frame_responsive=responsive(f) if f else None, desktop=desktop_state()),
                     indent=1, ensure_ascii=False))


def cmd_menu():
    state = load_state()
    _require_pid(state)
    f = _require_frame(state)
    hmenu = user32.GetMenu(f)
    tree = menu_tree(hmenu) if hmenu else []
    (HERE / 'menu.json').write_text(json.dumps(tree, indent=1, ensure_ascii=False), encoding='utf-8')
    for e in flatten(tree):
        if e.get('error') is not None:
            print(' > '.join(e['path']), f"(unreadable, GetMenuItemInfoW error {e['error']})")
            continue
        if not e.get('separator') and 'submenu' not in e:
            print(e['id'], ' > '.join(e['path']), '(disabled)' if e.get('disabled') else '',
                  '(ownerdraw)' if e.get('ownerdraw') else '')


WM_INITMENUPOPUP = 0x117


def refresh_menus(f):
    """wx 2.8 on MSW updates menu enable state only on WM_INITMENUPOPUP (framecmn.cpp OnMenuOpen);
    ProcessCommand ignores items still marked disabled. Ask the frame to refresh every top menu."""
    hmenu = user32.GetMenu(f)
    for i in range(user32.GetMenuItemCount(hmenu)):
        sub = user32.GetSubMenu(hmenu, i)
        if sub:
            user32.SendMessageTimeoutW(f, WM_INITMENUPOPUP, ctypes.cast(sub, ctypes.c_void_p).value or 0, ctypes.c_void_p(i),
                                       SMTO_ABORTIFHUNG, 3000, ctypes.byref(ctypes.c_size_t()))


def item_state(f, cmd_id):
    for e in flatten(menu_tree(user32.GetMenu(f))):
        if e.get('id') == int(cmd_id) and 'submenu' not in e:
            return dict(path=' > '.join(e['path']), disabled=e['disabled'])
    return None


def cmd_command(cmd_id):
    state = load_state()
    _require_pid(state)
    f = _require_frame(state)
    if dialogs(state):
        raise RunnerError('a dialog is open; close it before posting a menu command')
    refresh_menus(f)
    print(json.dumps(dict(item=item_state(f, cmd_id))))
    before = desktop_state()
    ok = user32.PostMessageW(f, WM_COMMAND, int(cmd_id) & 0xFFFF, 0)
    time.sleep(1.0)
    print(json.dumps(dict(posted=bool(ok), desktop_before=before, desktop_after=desktop_state(),
                          dialogs=[describe(d) for d in dialogs(state)]), indent=1, ensure_ascii=False))


def _one_dialog(state):
    dl = dialogs(state)
    if len(dl) != 1:
        raise RunnerError(f'expected one dialog, found {len(dl)}')
    return dl


def cmd_dialog_file(path):
    state = load_state()
    _require_pid(state)
    dl = _one_dialog(state)
    edit = find_file_edit(dl[0])
    if not edit:
        raise RunnerError('filename edit not found in the open dialog')
    before = desktop_state()
    buf = ctypes.create_unicode_buffer(path)
    user32.SendMessageTimeoutW(edit, WM_SETTEXT, 0, ctypes.cast(buf, ctypes.c_void_p), SMTO_ABORTIFHUNG, 2000,
                               ctypes.byref(ctypes.c_size_t()))
    readback = text_of(edit)
    ok_button = next((k for k in child_windows(dl[0]) if user32.GetDlgCtrlID(k) == 1 and class_name(k) == 'Button'), None)
    user32.PostMessageW(dl[0], WM_COMMAND, 1, ok_button or 0)
    time.sleep(1.5)
    print(json.dumps(dict(readback=readback, desktop_before=before, desktop_after=desktop_state(),
                          dialogs_after=[describe(d) for d in dialogs(state)]), indent=1, ensure_ascii=False))


def cmd_dialog_button(button_id):
    state = load_state()
    _require_pid(state)
    dl = _one_dialog(state)
    btn = next((k for k in child_windows(dl[0]) if user32.GetDlgCtrlID(k) == int(button_id)), None)
    before = desktop_state()
    user32.PostMessageW(dl[0], WM_COMMAND, int(button_id), btn or 0)
    time.sleep(1.0)
    print(json.dumps(dict(desktop_before=before, desktop_after=desktop_state(),
                          dialogs_after=[describe(d) for d in dialogs(state)]), indent=1, ensure_ascii=False))


def cmd_wait_log(pattern, timeout):
    state = load_state()
    log = _require_log(state)
    t0, rx = time.time(), re.compile(pattern)
    while time.time() - t0 < float(timeout):
        text = log.read_text(encoding='latin-1', errors='replace')
        m = rx.search(text)
        if m:
            print(json.dumps(dict(found=True, seconds=round(time.time() - t0, 1), match=m.group(0)[:300])))
            return
        time.sleep(0.5)
    print(json.dumps(dict(found=False, seconds=float(timeout), tail=log.read_text(encoding='latin-1')[-600:])))


def cmd_save_loop(save_id, tv4p, count):
    state = load_state()
    _require_pid(state)
    f = _require_frame(state)
    target = Path(tv4p)
    results = []
    for i in range(int(count)):
        if dialogs(state):
            raise RunnerError('a dialog is open before save')
        refresh_menus(f)
        if i == 0:
            print(json.dumps(dict(item=item_state(f, save_id))))
        before = desktop_state()
        m0 = target.stat().st_mtime_ns
        user32.PostMessageW(f, WM_COMMAND, int(save_id) & 0xFFFF, 0)
        t0, changed = time.time(), False
        while time.time() - t0 < 10:
            if target.stat().st_mtime_ns != m0:
                changed = True
                break
            time.sleep(0.1)
        after = desktop_state()
        results.append(dict(i=i, changed=changed, seconds=round(time.time() - t0, 2),
                            tb_took_foreground=after['foreground_pid'] == state['pid'],
                            foreground_same=after['foreground'] == before['foreground'],
                            cursor_same=after['cursor'] == before['cursor'],
                            dialogs=len(dialogs(state))))
        time.sleep(1.1)
    print(json.dumps(dict(passed=sum(r['changed'] and not r['tb_took_foreground'] and not r['dialogs'] for r in results),
                          of=len(results), results=results), indent=1))


CANCEL_LABELS = ('cancel', 'cancelar')
OK_LABELS = ('ok', 'aceptar', '&abrir', 'abrir', '&guardar', 'guardar', '&open', 'open', '&save', 'save')


def press_label(dlg, labels):
    """Press a dialog button by its caption. TB's own dialogs swap ids (Ok=2, Cancel=1), so ids lie."""
    for k in child_windows(dlg):
        if class_name(k) == 'Button' and user32.IsWindowVisible(k) and (text_of(k) or '').strip().lower() in labels:
            user32.PostMessageW(dlg, WM_COMMAND, user32.GetDlgCtrlID(k) & 0xFFFF, k)
            return True
    return False


def cmd_probe(prefix):
    """Post every enabled leaf under a menu path prefix (e.g. 'File > #10'), record the dialog title it
    opens, cancel it. Disposable instance only."""
    state = load_state()
    _require_pid(state)
    f = _require_frame(state)
    results = []
    refresh_menus(f)
    exact = prefix.split('|') if '|' in prefix else None
    leaves = [e for e in flatten(menu_tree(user32.GetMenu(f)))
              if 'submenu' not in e and 'error' not in e and not e['separator'] and
              (' > '.join(e['path']) in exact if exact else ' > '.join(e['path']).startswith(prefix))]
    log = None
    for e in leaves:
        refresh_menus(f)
        cur = next((x for x in flatten(menu_tree(user32.GetMenu(f))) if x['path'] == e['path']), None)
        if not cur or 'error' in cur or cur['disabled']:
            results.append(dict(path=' > '.join(e['path']), skipped='disabled'))
            continue
        if log is None:
            log = _require_log(state)
        size0 = log.stat().st_size
        user32.PostMessageW(f, WM_COMMAND, cur['id'] & 0xFFFF, 0)
        time.sleep(2.0)
        titles = [text_of(d) for d in dialogs(state)]
        for _ in range(3):
            for d in dialogs(state):
                press_label(d, CANCEL_LABELS)
            time.sleep(1.0)
        new_log = log.read_text(encoding='latin-1', errors='replace')[size0:].strip()[-200:] if log.stat().st_size > size0 else ''
        results.append(dict(path=' > '.join(cur['path']), id=cur['id'], dialogs=titles, log=new_log,
                            left_open=[text_of(d) for d in dialogs(state)], fg_pid=desktop_state()['foreground_pid']))
        if results[-1]['left_open']:
            break
    print(json.dumps(results, indent=1, ensure_ascii=False))


def cmd_close():
    state = load_state()
    _require_pid(state)
    f = frame(state)
    if f:
        user32.PostMessageW(f, WM_CLOSE, 0, 0)
    time.sleep(2)
    print(json.dumps(dict(dialogs=[describe(d) for d in dialogs(state)], alive=bool(top_windows(state['pid'], False))),
                     indent=1, ensure_ascii=False))


COMMANDS = dict(
    launch=lambda a: cmd_launch(),
    windows=lambda a: cmd_windows(),
    menu=lambda a: cmd_menu(),
    command=lambda a: cmd_command(a.cmd_id),
    dialog_file=lambda a: cmd_dialog_file(a.path),
    dialog_button=lambda a: cmd_dialog_button(a.button_id),
    wait_log=lambda a: cmd_wait_log(a.pattern, a.timeout),
    save_loop=lambda a: cmd_save_loop(a.save_id, a.tv4p, a.count),
    close=lambda a: cmd_close(),
    probe=lambda a: cmd_probe(a.prefix),
)


def _parser():
    parser = argparse.ArgumentParser(
        prog='tbrunner.py',
        description='EXPERIMENTAL, Windows only: drive a Terrain Builder this runner launched, by Win32 messages.',
    )
    parser.add_argument('--tb-exe', type=Path,
                        help="DayZ Tools' Bin/TerrainBuilder/terrainBuilder.exe (default: TBRUNNER_TB_EXE)")
    sub = parser.add_subparsers(dest='verb', required=True, metavar='COMMAND')
    sub.add_parser('launch', help='start Terrain Builder without activating it and record its pid')
    sub.add_parser('windows', help="list the recorded instance's top windows and dialog controls")
    sub.add_parser('menu', help='print every menu leaf with its id; write menu.json next to the state file')
    sub.add_parser('command', help='refresh the menus and post one menu command').add_argument('cmd_id', type=int)
    sub.add_parser('dialog_file', help='type a path into the one open file dialog and press its OK (id 1)'
                   ).add_argument('path')
    sub.add_parser('dialog_button', help='press a button of the one open dialog BY ID (TB swaps Ok and Cancel ids)'
                   ).add_argument('button_id', type=int)
    wait = sub.add_parser('wait_log', help="wait for a regex in the instance's .rpt log")
    wait.add_argument('pattern')
    wait.add_argument('timeout', type=float)
    save = sub.add_parser('save_loop', help='post a save command COUNT times; passed counts a changed .tv4p, Terrain Builder not taking the foreground, and no dialog; foreground_same and cursor_same are reported per iteration and do not count toward passed')
    save.add_argument('save_id', type=int)
    save.add_argument('tv4p')
    save.add_argument('count', type=int)
    sub.add_parser('close', help='post WM_CLOSE to the frame')
    sub.add_parser('probe', help="post every enabled leaf under a menu path prefix and cancel what it opens "
                   "('A > B' prefix, or exact paths joined by |); disposable instance only").add_argument('prefix')
    return parser


def main(argv=None):
    global TB_EXE, LOGS
    parser = _parser()
    args = parser.parse_args(argv)
    exe = args.tb_exe or (Path(os.environ['TBRUNNER_TB_EXE']) if os.environ.get('TBRUNNER_TB_EXE') else None)
    if exe is None:
        parser.error("set --tb-exe or TBRUNNER_TB_EXE to DayZ Tools' terrainBuilder.exe")
    TB_EXE, LOGS = exe, exe.parent / 'Logs'
    try:
        _win32()
        COMMANDS[args.verb](args)
    except (RunnerError, OSError, re.error) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
