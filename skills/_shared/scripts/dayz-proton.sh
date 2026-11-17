#!/bin/sh
# Run DayZ Tools (Steam app 830640) and DayZDiag on Linux through Proton.
#
#   dayz-proton.sh doctor                         what is installed, versions, prefixes, dayzmake
#   dayz-proton.sh init [<P-root>]                create the private tools prefix, register the game, map P:
#   dayz-proton.sh winpath <path>                 the Windows path a tool sees for a Linux path
#   dayz-proton.sh tool <Tool> [args...]          run a console tool, print its output, return its exit code
#   dayz-proton.sh gui  <Tool> [args...]          run a GUI tool on the current display
#   dayz-proton.sh binarize <P-root> <addon> <out> [file.p3d|file.rtm ...]
#                                                 BI binarize.exe in a confined sandbox, run from the P: root
#   dayz-proton.sh headless start <state> <Tool|DayZDiag> [args...]   GUI tool in a headless sway
#   dayz-proton.sh headless shot  <state> <out.png>
#   dayz-proton.sh headless stop  <state>
#
# Tools: AddonBuilder BankRev Binarize CfgConvert DSCheckSignatures DSCreateKey DSSignFile FileBank
#        ImageToPAA ImageToPAAGUI ObjectBuilder Publisher TerrainBuilder TexView Workbench, and DayZDiag
#        (the diag executable from the game folder, run in the private *game* prefix).
#
# Why: DayZ (221100) and DayZ Tools (830640) are separate Steam apps, so Proton gives each its own
# Wine prefix, and nothing the Windows tools expect to share crosses between them: the game's
# HKLM\SOFTWARE\(WOW6432Node\)Bohemia Interactive\DayZ "main" key is empty in the tools prefix, and
# the P: drive (subst on Windows; Wine has no subst) exists in neither. `init` builds private
# prefixes under DAYZ_PROTON_HOME and leaves Steam's own prefixes alone. In the tools prefix it
# replays what Steam does on a first launch (installscript.vdf registry, VC++ runtime with MFC from
# Steamworks Shared), adds the game key, spends the one failing first .NET start, and maps P: (a
# dosdevices symlink) in both prefixes. Run it once; it takes about two minutes.
#
# Rules learned the hard way (2026-11-03, Proton Hotfix and GE-Proton11-1, Debian testing):
# - One display per prefix at a time: a prefix's wineserver is bound to the display its first
#   program used; others die with "X Error ... BadWindow ... X_UnmapWindow". A headless state
#   path may only contain A-Z a-z 0-9 / . _ - (checked as given and once resolved, before any
#   side effect, in `start`, `stop` and `shot`). `headless start` requires `setsid`, refuses a
#   busy (or untellable) prefix, and refuses while a launcher or sway of the same state may
#   still be running: it always scans for one before touching the state, and if sway.pid,
#   sway.identity or sway.cancel exists and no launcher or sway of this state is alive,
#   those files are stale and are removed with one stderr line before continuing. It succeeds
#   only when the recorded pid's /proc comm is sway with the exact three-entry sway argv; `headless stop` signals only a
#   sway whose recorded /proc identity (start time + full argv) still matches, then only that
#   session's wineserver (by pid:starttime, re-checked before each signal; an empty or
#   unreadable recorded display signals no wineserver). These checks and the signal are not
#   atomic: they reduce, but do not eliminate, the check-then-signal race.
#   Invariant for `headless start`: after it returns (success or failure) either the recorded
#   sway is tracked with a verified identity, or no sway of this state is running. A failed
#   start first writes $state/sway.cancel, which the launcher child checks before writing
#   sway.pid and again just after; the failed start signals the published pid, waits five
#   tenths of a second re-checking for a pid published in that window, and only then removes
#   sway.pid/sway.identity. The cancel marker is left behind after a failure (a slower child
#   still sees it and exits without exec'ing sway); it is removed by the next start only after
#   that start has proved no launcher of this state is alive, and by a successful start once
#   the identity is recorded. The sway.conf path is passed to awk through the environment
#   (ENVIRON), never `awk -v`, whose escape handling would mis-compare some state paths.
#   `binarize` and console `tool` write their arguments only into a quoted .bat and refuse
#   any with a double quote, CR, LF or empty before doing anything. `init` stops only the
#   wineservers that were not running when it began, in the prefixes it used. Real Proton,
#   sway and cmd.exe were not run by the offline tests.
#   DAYZ_PROTON_START_WAIT_TENTHS bounds the `headless start` wait for sway to appear, in
#   tenths of a second (default 50).
# - 32-bit tools run with PROTON_USE_WOW64=1 (default here), or GDI dialogs show no text when the
#   host has no i386 FreeType. DAYZ_PROTON_RUNTIME=1 starts Proton inside the Steam Linux Runtime
#   instead, as Steam does; GDI tools crashed there on this host.
# - Object Builder asks for BI's licence on its first start: run `gui ObjectBuilder` once on your
#   desktop and answer it yourself.
#
# Arguments that are absolute Linux paths (/x/y, or -opt=/x/y) are rewritten to Windows paths: P:\...
# inside the P: root, Z:\... elsewhere. Pass `--` to stop the rewriting for the remaining arguments.
#
# Environment: STEAM_ROOT (auto), PROTON (tool name or path; default: Proton Hotfix, else GE-Proton*,
# else Proton - Experimental), DAYZ_PROTON_HOME (default ${XDG_DATA_HOME:-~/.local/share}/dayz-proton),
# DAYZ_P (P: root, default: what `init` recorded), DAYZ_PROTON_CWD (working directory of `tool`),
# DAYZ_PROTON_PREFIX=steam to use Steam's compatdata/<appid> prefixes instead (then `init` writes the
# game key and P: into them, nothing else).
set -eu

me=$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")
die() { echo "dayz-proton: $*" >&2; exit 1; }
CR=$(printf '\r')
# Literal newline: $(printf '\n') is empty, as $() strips trailing newlines.
LF='
'

# --- batch-file quoting (binarize, console tools) ----------------------------
# bat_validate <value> [<caller>]: refuse values a .bat cannot carry safely.
# Called on the original arguments before any side effect.
bat_validate() {
    _bv_who=${2:-bat}
    [ -n "$1" ] || die "$_bv_who: an empty argument is not allowed"
    case $1 in
        *'"'*) die "$_bv_who: an argument containing a double quote is not allowed" ;;
        *"$CR"*|*"$LF"*) die "$_bv_who: an argument containing CR or LF is not allowed" ;;
    esac
}
# bat_quote <value>: print it double-quoted for a .bat: % doubled, and the whole
# run of trailing backslashes doubled (MS C runtime rule, so \" is not an
# escaped quote). No validation here; call bat_validate first.
bat_quote() {
    _bq_v=$(printf '%s' "$1" | sed 's/%/%%/g')
    _bq_tail=
    while :; do
        case $_bq_v in
            *\\) _bq_tail="$_bq_tail\\"; _bq_v=${_bq_v%\\} ;;
            *) break ;;
        esac
    done
    printf '"%s%s%s"' "$_bq_v" "$_bq_tail" "$_bq_tail"
}

# ---------------------------------------------------------------- Steam, apps, Proton
find_steam() {
    if [ -n "${STEAM_ROOT:-}" ]; then echo "$STEAM_ROOT"; return; fi
    for d in "$HOME/.steam/debian-installation" "$HOME/.steam/steam" "$HOME/.local/share/Steam" \
             "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"; do
        [ -d "$d/steamapps" ] && { (cd "$d" && pwd -P); return; }
    done
    die "no Steam install found (set STEAM_ROOT)"
}
STEAM_ROOT=$(find_steam)

libraries() {
    echo "$STEAM_ROOT"
    sed -n 's/^[[:space:]]*"path"[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' \
        "$STEAM_ROOT/steamapps/libraryfolders.vdf" 2>/dev/null | sed 's/\\\\/\\/g'
}

# manifest <appid> -> path of appmanifest_<appid>.acf, empty if not installed
manifest() {
    libraries | while IFS= read -r lib; do
        [ -f "$lib/steamapps/appmanifest_$1.acf" ] && { echo "$lib/steamapps/appmanifest_$1.acf"; break; }
    done || true  # not found: the loop's status is the failed test, which set -e turned into an exit
}
acf() { sed -n "s/^[[:space:]]*\"$2\"[[:space:]]*\"\(.*\)\"/\1/p" "$1" | head -n 1; }

# appdir <appid> -> install folder
appdir() {
    m=$(manifest "$1"); [ -n "$m" ] || return 1
    echo "$(dirname "$m")/common/$(acf "$m" installdir)"
}

find_proton() {
    p=${PROTON:-}
    if [ -n "$p" ]; then
        for c in "$p" "$STEAM_ROOT/compatibilitytools.d/$p" "$STEAM_ROOT/steamapps/common/$p"; do
            [ -x "$c/proton" ] && { echo "$c/proton"; return; }
            [ -f "$c" ] && [ "$(basename "$c")" = proton ] && { echo "$c"; return; }
        done
        die "Proton tool '$p' not found"
    fi
    for c in "$STEAM_ROOT/steamapps/common/Proton Hotfix" \
             $(ls -d "$STEAM_ROOT"/compatibilitytools.d/GE-Proton* 2>/dev/null | sort -V -r) \
             "$STEAM_ROOT/steamapps/common/Proton - Experimental"; do
        [ -x "$c/proton" ] && { echo "$c/proton"; return; }
    done
    c=$(ls -d "$STEAM_ROOT"/steamapps/common/Proton\ [0-9]* 2>/dev/null | sort -V | tail -n 1)
    [ -n "$c" ] && [ -x "$c/proton" ] && { echo "$c/proton"; return; }
    die "no Proton found (install one through Steam or set PROTON)"
}

H=${DAYZ_PROTON_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/dayz-proton}

# The Steam Linux Runtime container a Proton build asks for (toolmanifest.vdf require_tool_appid).
find_runtime() {
    id=$(sed -n 's/.*"require_tool_appid"[[:space:]]*"\([0-9]*\)".*/\1/p' "$(dirname "$PROTON_BIN")/toolmanifest.vdf" 2>/dev/null)
    [ -n "$id" ] || return 0
    d=$(appdir "$id" 2>/dev/null) || return 0
    [ -x "$d/_v2-entry-point" ] && echo "$d/_v2-entry-point"
    return 0
}

# prun <exe> [args]: `proton run`, by default bare with PROTON_USE_WOW64=1.
# The measured tool/font workaround uses WoW64; inspect installed PE headers for bitness.
# Bare and without WoW64, Proton runs them against the host's i386 libraries, and without an i386
# FreeType their dialogs show no text at all. Inside the Steam Linux Runtime container
# (DAYZ_PROTON_RUNTIME=1, what Steam itself does) GDI tools died on a fontconfig/X error here.
# WoW64 runs them through the 64-bit host libraries, which fixed both (measured 2026-11-03).
prun() {
    if [ "${DAYZ_PROTON_RUNTIME:-0}" = 1 ] && rt=$(find_runtime) && [ -n "$rt" ]; then
        "$rt" --verb=run -- "$PROTON_BIN" run "$@"
    else
        PROTON_USE_WOW64=${PROTON_USE_WOW64:-1} "$PROTON_BIN" run "$@"
    fi
}


# prefix_dir <appid> -> the STEAM_COMPAT_DATA_PATH used for that app
prefix_dir() {
    if [ "${DAYZ_PROTON_PREFIX:-}" = steam ]; then
        m=$(manifest "$1"); [ -n "$m" ] || die "app $1 is not installed"
        echo "$(dirname "$m")/compatdata/$1"
    elif [ "$1" = 830640 ]; then echo "$H/tools"
    else echo "$H/game"
    fi
}

p_root() {
    if [ -n "${DAYZ_P:-}" ]; then echo "$DAYZ_P"; return; fi
    [ -f "$H/p-root" ] && cat "$H/p-root"
    return 0
}

# ---------------------------------------------------------------- paths
# winpath <linux path> -> P:\... when inside the P: root, else Z:\...
winpath() {
    case $1 in /*) a=$1 ;; *) a=$(pwd -P)/$1 ;; esac
    d=$(dirname "$a"); b=$(basename "$a")
    [ -d "$d" ] && a=$(cd "$d" && pwd -P)/$b
    a=${a%/.}
    pr=$(p_root)
    if [ -n "$pr" ] && { [ "$a" = "$pr" ] || [ "${a#"$pr"/}" != "$a" ]; }; then
        r=${a#"$pr"}; r=${r#/}
        printf 'P:\\%s\n' "$(printf '%s' "$r" | tr / '\\')"
    else
        printf 'Z:%s\n' "$(printf '%s' "$a" | tr / '\\')"
    fi
}

# ---------------------------------------------------------------- tools
# tool_exe <Tool> -> "<kind> <path>" ; kind = con | gui | game
tool_exe() {
    T=$(appdir 830640 2>/dev/null)/Bin
    case $1 in
        AddonBuilder)      echo "con $T/AddonBuilder/AddonBuilder.exe" ;;
        Binarize)          echo "con $T/Binarize/binarize.exe" ;;
        CfgConvert)        echo "con $T/CfgConvert/CfgConvert.exe" ;;
        DSSignFile|DSCheckSignatures|DSCreateKey)
                           echo "con $T/DsUtils/$1.exe" ;;
        DSUtils)           echo "gui $T/DsUtils/DSUtils.exe" ;;
        FileBank|BankRev)  echo "con $T/PboUtils/$1.exe" ;;
        ImageToPAA)        echo "con $T/ImageToPAA/ImageToPAA.exe" ;;
        ImageToPAAGUI)     echo "gui $T/ImageToPAA/imageToPaaGUI.exe" ;;
        TexView)           echo "gui $T/ImageToPAA/TexView.exe" ;;
        ObjectBuilder)     echo "gui $T/ObjectBuilder/ObjectBuilder.exe" ;;
        Publisher)         echo "gui $T/Publisher/Publisher.exe" ;;
        TerrainBuilder)    echo "gui $T/TerrainBuilder/terrainBuilder.exe" ;;
        Workbench)         echo "gui $T/Workbench/WorkbenchApp.exe" ;;
        DayZDiag)          g=$(appdir 221100) || die "DayZ (221100) is not installed"
                           echo "game $g/DayZDiag_x64.exe" ;;
        *) die "unknown tool '$1' (see: $me with no arguments)" ;;
    esac
}

proton_env() {   # proton_env <appid>
    pfx=$(prefix_dir "$1"); mkdir -p "$pfx"
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT" STEAM_COMPAT_DATA_PATH="$pfx"
    export SteamAppId="$1" SteamGameId="$1" STEAM_COMPAT_APP_ID="$1"
    PROTON_BIN=$(find_proton)
}

ensure_prefix() {   # ensure_prefix <appid>: create the Wine prefix once
    proton_env "$1"
    [ -d "$STEAM_COMPAT_DATA_PATH/pfx/dosdevices" ] && return 0
    echo "dayz-proton: creating prefix $STEAM_COMPAT_DATA_PATH (once, ~10 s)" >&2
    prun cmd.exe /c exit >/dev/null 2>&1 || true
    if [ "$1" = 830640 ] && [ "${DAYZ_PROTON_PREFIX:-}" != steam ]; then
        import_registry; install_vcredist; warm_dotnet
    fi
    return 0
}

# The first .NET tool started in a fresh prefix never finishes: AddonBuilder crashed (DXVK error)
# without WoW64 and hung after its constructor with it; every later start works (2026-11-03).
# Spend that one start on a throwaway pack, time-boxed, then stop the prefix's wineserver.
warm_dotnet() {
    ab=$(appdir 830640)/Bin/AddonBuilder/AddonBuilder.exe
    [ -f "$ab" ] || return 0
    # Executable guard for the wineserver stop below: snapshot this prefix's
    # wineserver PIDs first; afterwards signal only PIDs that are new. An
    # unknown snapshot means signal nothing. (A fresh prefix has no dosdevices
    # yet, but that alone does not prove no server serves its path.)
    if _wd_snap=$(prefix_wineserver "$STEAM_COMPAT_DATA_PATH"); then _wd_ok=1; else _wd_snap=; _wd_ok=0; fi
    wd=$(mktemp -d "${TMPDIR:-/tmp}/dayz-proton-warm.XXXXXX"); mkdir -p "$wd/src" "$wd/out"
    echo warm > "$wd/src/readme.txt"
    echo "dayz-proton: warming up .NET in the new prefix (once, up to 90 s)" >&2
    ( cd "$(dirname "$ab")" && timeout 90 sh -c 'PROTON_USE_WOW64=${PROTON_USE_WOW64:-1} "$1" run "$2" "$3" "$4" -packonly -prefix=warm' \
        sh "$PROTON_BIN" "$ab" "$(winpath "$wd/src")" "$(winpath "$wd/out")" ) >/dev/null 2>&1 || true
    signal_new_wineservers "$STEAM_COMPAT_DATA_PATH" "$_wd_snap" "$_wd_ok" ""
    rm -rf "$wd"
}

# What Steam writes into the tools prefix on first launch (installscript.vdf "Registry"), which a
# private prefix never gets: without it TexView stops at "Missing registry entry
# HKEY_LOCAL_MACHINE/Software\BIStudio\TextureConvert". Plus the game's "main" key, which on Windows
# the DayZ installer writes and which no Proton prefix of 830640 has (the game lives in 221100's).
# HKLM keys go to both registry views, including WOW6432Node for tools that read it.
import_registry() {
    td=$(appdir 830640) || return 0
    wtd=$(winpath "$td" | sed 's/\\/\\\\/g')
    reg=$STEAM_COMPAT_DATA_PATH/dayz-proton.reg
    {
        printf 'Windows Registry Editor Version 5.00\r\n'
        DIR=$wtd awk '
            /"Registry"/ { inreg = 1; next }
            inreg && /"Run Process"/ { exit }
            inreg && match($0, /^[[:space:]]*"(HKEY_[^"]*)"[[:space:]]*$/) {
                k = $0; sub(/^[[:space:]]*"/, "", k); sub(/"[[:space:]]*$/, "", k); gsub(/\\\\/, "\\", k)
                n = 1; keys[1] = k
                if (k ~ /^HKEY_LOCAL_MACHINE\\SOFTWARE\\/) { w = k; sub(/SOFTWARE\\/, "SOFTWARE\\WOW6432Node\\", w); keys[++n] = w }
                next
            }
            inreg && n && match($0, /^[[:space:]]*"[^"]*"[[:space:]]+"[^"]*"[[:space:]]*$/) {
                split($0, f, "\""); v = f[4]
                while ((i = index(v, "%INSTALLDIR%")) > 0) v = substr(v, 1, i - 1) ENVIRON["DIR"] substr(v, i + 12)
                for (i = 1; i <= n; i++) vals[keys[i]] = vals[keys[i]] sprintf("\"%s\"=\"%s\"\r\n", f[2], v)
                if (!(keys[1] in seen)) { seen[keys[1]] = 1; order[++m] = keys[1]; if (n > 1) order[++m] = keys[2] }
            }
            END { for (i = 1; i <= m; i++) printf "\r\n[%s]\r\n%s", order[i], vals[order[i]] }
        ' "$td/installscript.vdf"
        g=$(appdir 221100 2>/dev/null) && {
            wg=$(winpath "$g" | sed 's/\\/\\\\/g')
            for k in 'HKEY_LOCAL_MACHINE\SOFTWARE\Bohemia Interactive\DayZ' \
                     'HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ'; do
                printf '\r\n[%s]\r\n"main"="%s"\r\n' "$k" "$wg"
            done
        }
    } > "$reg"
    prun regedit /S "$(winpath "$reg")" >/dev/null 2>&1 || echo "dayz-proton: registry import failed ($reg)" >&2
}

# A prefix has one wineserver, and its desktop is bound to the display the first program of the
# prefix started on. Programs started later on another display (or after that display is gone, e.g.
# a stopped headless sway) die with "X Error ... BadWindow ... X_UnmapWindow". So: one display per
# prefix at a time, and stop the wineserver whenever a session ends.
# norm_path <path>: print it without trailing slashes ("/" stays "/").
norm_path() {
    _np=$1
    while :; do case $_np in */) _np=${_np%/} ;; *) break ;; esac; done
    printf '%s\n' "${_np:-/}"
}
# wineserver_serves <pid> <prefix> <display|"">: 0 = environ readable and the
# WINEPREFIX matches the prefix literally (the value may be the compatdata dir
# or its pfx subdir, with or without a trailing slash; no regex, so a prefix
# containing [ ] . * cannot mis-match) and, when a display is given,
# WAYLAND_DISPLAY equals it. 1 = no match. 2 = environ unreadable (unknown).
wineserver_serves() {
    _ws_tmp=$(mktemp) || return 2
    if ! tr '\0' '\n' < "/proc/$1/environ" > "$_ws_tmp" 2>/dev/null; then rm -f "$_ws_tmp"; return 2; fi
    _ws_wp=; _ws_disp=; _ws_have_disp=0
    while IFS= read -r _ws_line; do
        case $_ws_line in
            WINEPREFIX=*) _ws_wp=${_ws_line#WINEPREFIX=} ;;
            WAYLAND_DISPLAY=*) _ws_disp=${_ws_line#WAYLAND_DISPLAY=}; _ws_have_disp=1 ;;
        esac
    done < "$_ws_tmp"
    rm -f "$_ws_tmp"
    [ -n "$_ws_wp" ] || return 1
    _ws_wp=$(norm_path "$_ws_wp"); _ws_pfx=$(norm_path "$2")
    [ "$_ws_wp" = "$_ws_pfx" ] || [ "$_ws_wp" = "$_ws_pfx/pfx" ] || return 1
    if [ -n "$3" ]; then
        if [ "$_ws_have_disp" != 1 ] || [ "$_ws_disp" != "$3" ]; then return 1; fi
    fi
    return 0
}
# wineserver_identity_ok <pid> <starttime>: /proc comm is wineserver and the
# live start time (field 22) still equals the recorded one. The check and a
# following kill are still not atomic: a pid can exit and be reused between
# them, so this narrows but does not eliminate the check-then-signal race.
wineserver_identity_ok() {
    [ -n "$2" ] || return 1
    _wi_comm=$(cat "/proc/$1/comm" 2>/dev/null) || return 1
    [ "$_wi_comm" = wineserver ] || return 1
    _wi_now=$(proc_starttime "$1") || return 1
    [ "$_wi_now" = "$2" ]
}
# prefix_wineserver <compatdata dir>: print pid:starttime pairs serving it,
# one per line (the start time is taken as each candidate is enumerated).
# Returns 1 when that cannot be told (pgrep failed, or a wineserver's environ
# or start time was unreadable): unknown is never reported as free; callers
# treat it as busy.
prefix_wineserver() {
    if _pw_list=$(pgrep -x wineserver 2>/dev/null); then _pw_rc=0; else _pw_rc=$?; fi
    [ "$_pw_rc" = 1 ] && return 0
    [ "$_pw_rc" = 0 ] || return 1
    _pw_unknown=0
    for _pw_p in $_pw_list; do
        if wineserver_serves "$_pw_p" "$1" ""; then
            if _pw_start=$(proc_starttime "$_pw_p"); then
                printf '%s:%s\n' "$_pw_p" "$_pw_start"
            else
                _pw_unknown=1
            fi
        elif [ $? = 2 ]; then
            _pw_unknown=1
        fi
    done
    [ "$_pw_unknown" = 0 ]
}
# signal_session_wineservers <prefix> <display>: kill -INT only the
# pid:starttime pairs serving the prefix on exactly this display, each
# re-checked (environ, comm, start time) immediately before its signal.
# Guard: an empty display signals nothing here, whatever the caller passed;
# wineserver_serves is never reached with an empty session display.
signal_session_wineservers() {
    if [ -z "$2" ]; then
        echo "dayz-proton: no recorded display; leaving the wineserver alone" >&2
        return 0
    fi
    if ! _ss_pairs=$(prefix_wineserver "$1"); then
        echo "dayz-proton: could not tell which wineservers serve $1; leaving them running" >&2
        return 0
    fi
    for _ss_pair in $_ss_pairs; do
        _ss_pid=${_ss_pair%%:*}; _ss_start=${_ss_pair#*:}
        if wineserver_serves "$_ss_pid" "$1" "$2" && wineserver_identity_ok "$_ss_pid" "$_ss_start"; then
            kill -INT "$_ss_pid" 2>/dev/null || true
        fi
    done
    return 0
}
# signal_new_wineservers <prefix> <snapshot pid:starttime pairs> <ok 1|0>
# <display|"">: kill -INT (what wineserver -k sends) only pairs serving the
# prefix that were not in the snapshot, re-verified (environ, comm, start
# time) immediately before signalling. An unknown snapshot or scan signals
# nothing. The re-check and the signal are still not atomic (see
# wineserver_identity_ok).
signal_new_wineservers() {
    if [ "$3" != 1 ]; then
        echo "dayz-proton: could not tell which wineservers served $1 before; leaving them running" >&2
        return 0
    fi
    if ! _sn_now=$(prefix_wineserver "$1"); then
        echo "dayz-proton: could not tell which wineservers serve $1 now; leaving them running" >&2
        return 0
    fi
    for _sn_pair in $_sn_now; do
        _sn_pid=${_sn_pair%%:*}; _sn_start=${_sn_pair#*:}
        _sn_old=0
        for _sn_o in $2; do [ "$_sn_o" = "$_sn_pair" ] && _sn_old=1; done
        [ "$_sn_old" = 1 ] && continue
        if wineserver_serves "$_sn_pid" "$1" "$4" && wineserver_identity_ok "$_sn_pid" "$_sn_start"; then
            kill -INT "$_sn_pid" 2>/dev/null || true
        fi
    done
    [ -n "$2" ] && echo "dayz-proton: wineserver for $1 was already running; left running" >&2
    return 0
}
stop_wineserver() {   # stop_wineserver <appid>: kept for compatibility; by PID now
    pfx=$(prefix_dir "$1")
    if ! _sw_pairs=$(prefix_wineserver "$pfx"); then
        echo "dayz-proton: could not tell which wineservers serve $pfx; leaving them running" >&2
        return 0
    fi
    for _sw_pair in $_sw_pairs; do
        _sw_pid=${_sw_pair%%:*}; _sw_start=${_sw_pair#*:}
        if wineserver_serves "$_sw_pid" "$pfx" "" && wineserver_identity_ok "$_sw_pid" "$_sw_start"; then
            kill -INT "$_sw_pid" 2>/dev/null || true
        fi
    done
}

# The VC++ runtime with MFC (Object Builder needs mfc140.dll). Steam installs it from Steamworks
# Shared/_CommonRedist on an app's first launch; a private prefix has to do it itself.
install_vcredist() {
    [ -f "$STEAM_COMPAT_DATA_PATH/pfx/drive_c/windows/syswow64/mfc140.dll" ] && return 0
    sw=$(appdir 228980 2>/dev/null) || sw=
    vd=$(ls -d "$sw"/_CommonRedist/vcredist/20* 2>/dev/null | sort -r | while IFS= read -r d; do
        [ -f "$d/VC_redist.x86.exe" ] && { echo "$d"; break; }; done)
    [ -n "$vd" ] || { echo "dayz-proton: no VC++ redistributable in Steamworks Shared (app 228980); Object Builder will not start" >&2; return 0; }
    echo "dayz-proton: installing the VC++ runtime from $vd (once)" >&2
    for a in x86 x64; do (cd "$vd" && timeout 300 sh -c 'PROTON_USE_WOW64=1 "$1" run "$2" /q /norestart' sh "$PROTON_BIN" "./VC_redist.$a.exe") >/dev/null 2>&1 || true; done
}

# rewrite_args: one argument per line on stdout, absolute paths converted
rewrite_args() {
    raw=0
    for a in "$@"; do
        if [ $raw = 1 ]; then printf '%s\n' "$a"; continue; fi
        case $a in
            --) raw=1 ;;
            /*) winpath "$a" ;;
            -*=/*) printf '%s=%s\n' "${a%%=*}" "$(winpath "${a#*=}")" ;;
            *) printf '%s\n' "$a" ;;
        esac
    done
}

run_tool() {   # run_tool con|gui <Tool> [args]
    mode=$1; name=$2; shift 2
    set -- "$name" "$@"
    spec=$(tool_exe "$1"); kind=${spec%% *}; exe=${spec#* }; shift
    [ -f "$exe" ] || die "$exe not found (is DayZ Tools, app 830640, installed?)"
    if [ "$mode" != gui ] && [ "$kind" = con ]; then
        for _rt_a in "$@"; do bat_validate "$_rt_a" "tool $name"; done
        bat_validate "$(winpath "$exe")" "tool $name"
        bat_validate "${TMPDIR:-/tmp}" "tool $name"
    fi
    args=$(mktemp); rewrite_args "$@" > "$args"
    set --; while IFS= read -r a; do set -- "$@" "$a"; done < "$args"; rm -f "$args"
    if [ "$mode" != gui ] && [ "$kind" = con ]; then
        for _rt_a in "$@"; do bat_validate "$_rt_a" "tool $name"; done
    fi
    app=830640; [ "$kind" = game ] && app=221100
    ensure_prefix "$app"
    cd "${DAYZ_PROTON_CWD:-$(dirname "$exe")}"
    if [ "$mode" = gui ] || [ "$kind" != con ]; then
        prun "$exe" "$@"; exit $?
    fi
    # Console tools: several (DS*, ImageToPAA) print nothing on Proton's console, so run them
    # through cmd with their output redirected to a file, then show it. cmd passes the exit code on.
    out=$(mktemp -d "${TMPDIR:-/tmp}/dayz-proton.XXXXXX")
    # A .bat file keeps quoting intact: Proton escapes quotes inside a `cmd /c "..."` string.
    # Every value is written double-quoted by bat_quote; DisableDelayedExpansion keeps ! literal.
    {
        printf '@echo off\r\n'
        printf 'setlocal DisableDelayedExpansion\r\n'
        printf '%s' "$(bat_quote "$(winpath "$exe")")"
        for _rt_a in "$@"; do
            printf ' %s' "$(bat_quote "$_rt_a")"
        done
        printf ' > %s 2>&1\r\nexit /b %%errorlevel%%\r\n' "$(bat_quote "$(winpath "$out/log.txt")")"
    } > "$out/run.bat"
    rpt=$(dirname "$(dirname "$exe")")/Logs/AddonBuilder.rpt
    rpt_lines=$(cat "$rpt" 2>/dev/null | wc -l)
    rc=0
    prun cmd.exe /c "$(winpath "$out/run.bat")" >"$out/proton.txt" 2>&1 || rc=$?
    [ -f "$out/log.txt" ] && tr -d '\r' < "$out/log.txt"
    # AddonBuilder exits 0 on a failed build; the result is only in its rpt ("[ResultCode]=1").
    if [ "$name" = AddonBuilder ] && [ -f "$rpt" ]; then
        tail -n +"$((rpt_lines + 1))" "$rpt" | tr -d '\r' | grep -E '\[(ERROR|FATAL)\]|ResultCode' | cut -c1-300 >&2 || true
        res=$(tail -n +"$((rpt_lines + 1))" "$rpt" | tr -d '\r' | sed -n 's/.*\[ResultCode\]=\([0-9]*\).*/\1/p' | tail -n 1)
        [ -n "$res" ] && [ "$res" != 0 ] && [ $rc = 0 ] && rc=$res
        [ -n "$res" ] || { [ $rc = 0 ] && rc=1; echo "dayz-proton: AddonBuilder wrote no ResultCode (see $rpt)" >&2; }
    fi
    [ $rc = 0 ] || grep -v -E 'fsync|radv|FreeType|freetype|2\.0\.5|freetype\.org' "$out/proton.txt" >&2 || true
    rm -rf "$out"
    return $rc
}

# ---------------------------------------------------------------- binarize sandbox
# binarize.exe walks Wine's Z: drive (= / by default) for minutes; it is only usable with a Z: that
# holds nothing but the sandbox. It resolves texture paths relative to its current directory, so it
# must run from the P: root or alpha textures are silently lost.
do_binarize() {
    [ $# -ge 3 ] || die "usage: binarize <P-root> <addon path under P:> <out dir> [files...]"
    # Validate the original addon and file arguments before anything is
    # created, copied, linked, removed or run (see bat_validate).
    bat_validate "$2" binarize
    _bz_i=0
    for _bz_a in "$@"; do
        _bz_i=$((_bz_i + 1))
        if [ "$_bz_i" -gt 3 ]; then bat_validate "$_bz_a" binarize; fi
    done
    proot=$(cd "$1" && pwd -P); addon=$2; out=$3; shift 3
    # Strip trailing / from the addon before it becomes a backslash path (a
    # trailing \" would read as an escaped quote in the .bat).
    while :; do case $addon in */) addon=${addon%/} ;; *) break ;; esac; done
    [ -n "$addon" ] || die "binarize: an empty argument is not allowed"
    [ -d "$proot/$addon" ] || die "$proot/$addon does not exist"
    T=$(appdir 830640)/Bin/Binarize; [ -f "$T/binarize.exe" ] || die "DayZ Tools Binarize not found"
    sb=$H/binarize; mkdir -p "$sb/out" "$sb/prefix"
    if [ ! -f "$sb/Binarize/binarize.exe" ] || [ "$T/binarize.exe" -nt "$sb/Binarize/binarize.exe" ]; then
        rm -rf "$sb/Binarize"; cp -r "$T" "$sb/Binarize"
    fi
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT" STEAM_COMPAT_DATA_PATH="$sb/prefix"
    export SteamAppId=830640 SteamGameId=830640
    PROTON_BIN=$(find_proton)
    [ -d "$sb/prefix/pfx/dosdevices" ] || prun cmd.exe /c exit >/dev/null 2>&1 || true
    ln -sfn "$sb" "$sb/prefix/pfx/dosdevices/z:"
    ln -sfn "$proot" "$sb/prefix/pfx/dosdevices/p:"
    rm -rf "$sb/out"/*
    waddon=$(printf '%s' "$addon" | tr / '\\')
    # A .bat under the sandbox (Z:\run.bat, never under the wiped $sb/out):
    # no user text reaches the cmd.exe /c string. Every user value is written
    # double-quoted by bat_quote; DisableDelayedExpansion keeps ! literal.
    {
        printf '@echo off\r\n'
        printf 'setlocal DisableDelayedExpansion\r\n'
        printf '"Z:\\Binarize\\binarize.exe" -norecurse -always -maxProcesses=0 '
        printf '%s ' "$(bat_quote "P:\\$waddon")"
        printf '"Z:\\out"'
        for _bz_a in "$@"; do printf ' %s' "$(bat_quote "$_bz_a")"; done
        printf ' > "Z:\\out\\binarize.log" 2>&1\r\n'
        printf 'exit /b %%errorlevel%%\r\n'
    } > "$sb/run.bat"
    cd "$proot"
    rc=0
    prun cmd.exe /c 'Z:\run.bat' > /dev/null 2>&1 || rc=$?
    mkdir -p "$out"
    tr -d '\r' < "$sb/out/binarize.log" 2>/dev/null | grep -v '^$' | tail -n 40 || true
    rm -f "$sb/out/binarize.log"
    cp -r "$sb/out/." "$out/"
    echo "dayz-proton: binarize exit $rc, output in $out" >&2
    return $rc
}

# ---------------------------------------------------------------- headless sway
# The sway identity is its /proc start time (field 22 of /proc/<pid>/stat,
# parsed after the last ')' so a comm with spaces or parens cannot shift it)
# plus its full argv, both recorded by `start` itself in sway.identity (first
# line the start time, then one argv entry per line). `stop` re-reads both and
# signals only on an exact match. The PID is written by the child that execs
# sway, so it survives exec; $! of a setsid launcher would not under job
# control, where setsid forks and $! names the exiting parent.
proc_starttime() {
    _ps_stat=$(cat "/proc/$1/stat" 2>/dev/null) || return 1
    _ps_rest=${_ps_stat##*)}
    _ps_i=0
    for _ps_f in $_ps_rest; do
        _ps_i=$((_ps_i + 1))
        if [ "$_ps_i" = 20 ]; then printf '%s\n' "$_ps_f"; return 0; fi
    done
    return 1
}
# sway_identity_ok <pid> <state>: pid alive, recorded start time and full argv
# still match, and the argv names sway with -c <state>/sway.conf.
sway_identity_ok() {
    [ -d "/proc/$1" ] || return 1
    [ -f "$2/sway.identity" ] || return 1
    _si_recorded=$(head -n 1 "$2/sway.identity" 2>/dev/null) || return 1
    [ -n "$_si_recorded" ] || return 1
    _si_now=$(proc_starttime "$1") || return 1
    [ "$_si_now" = "$_si_recorded" ] || return 1
    _si_cur=$(mktemp) || return 1
    _si_rec=$(mktemp) || { rm -f "$_si_cur"; return 1; }
    if ! tr '\0' '\n' < "/proc/$1/cmdline" > "$_si_cur" 2>/dev/null; then
        rm -f "$_si_cur" "$_si_rec"; return 1
    fi
    tail -n +2 "$2/sway.identity" > "$_si_rec"
    if ! cmp -s "$_si_cur" "$_si_rec"; then rm -f "$_si_cur" "$_si_rec"; return 1; fi
    # ENVIRON, not awk -v: -v interprets escapes, so a state path holding a
    # literal backslash-t would reach awk with a TAB in it and never match.
    SWAYCONF="$2/sway.conf" awk '
        function base(p,   n, a) { n = split(p, a, "/"); return a[n] }
        NR == 1 { first = $0 }
        { prev2 = prev1; prev1 = $0; n = NR }
        END {
            if (n != 3 || prev2 != "-c" || prev1 != ENVIRON["SWAYCONF"]) exit 1
            if (base(first) == "sway") exit 0
            exit 1
        }' "$_si_cur"
    _si_rc=$?
    rm -f "$_si_cur" "$_si_rec"
    [ "$_si_rc" = 0 ]
}
# sway_cmdline_matches <pid> <state>: the live argv is exactly the three
# entries sway, -c, <state>/sway.conf (first entry's basename is sway).
sway_cmdline_matches() {
    _sc_cur=$(mktemp) || return 1
    if ! tr '\0' '\n' < "/proc/$1/cmdline" > "$_sc_cur" 2>/dev/null; then
        rm -f "$_sc_cur"; return 1
    fi
    SWAYCONF="$2/sway.conf" awk '
        function base(p,   n, a) { n = split(p, a, "/"); return a[n] }
        NR == 1 { first = $0 }
        { prev2 = prev1; prev1 = $0; n = NR }
        END {
            if (n != 3 || prev2 != "-c" || prev1 != ENVIRON["SWAYCONF"]) exit 1
            if (base(first) == "sway") exit 0
            exit 1
        }' "$_sc_cur"
    _sc_rc=$?
    rm -f "$_sc_cur"
    [ "$_sc_rc" = 0 ]
}
# failed_start_signal <state>: TERM the pid in sway.pid, but only while it
# is either still this start's launcher (its cmdline holds the 'exec sway'
# command string) or already the definitive sway of this state (exact
# sway -c <state>/sway.conf; the conf path is unique to this state and the
# pid file was written by this start's child). Never signal anything else
# the pid may have become.
failed_start_signal() {
    [ -s "$1/sway.pid" ] || return 0
    _fs_pid=$(cat "$1/sway.pid" 2>/dev/null) || _fs_pid=
    [ -n "$_fs_pid" ] || return 0
    [ -d "/proc/$_fs_pid" ] || return 0
    _fs_cmd=$(tr '\0' '\n' < "/proc/$_fs_pid/cmdline" 2>/dev/null) || _fs_cmd=
    case $_fs_cmd in
        *'exec sway'*) kill "$_fs_pid" 2>/dev/null || true ;;
        *) if sway_cmdline_matches "$_fs_pid" "$1"; then kill "$_fs_pid" 2>/dev/null || true; fi ;;
    esac
    return 0
}
# failed_start_cleanup <state>: give up on a start without leaving a sway
# this state cannot stop. The cancel marker comes FIRST: the launcher child
# checks it before writing sway.pid and again just after, so a child that
# has not reached sway yet exits instead of exec'ing it. Then signal the
# published pid, wait five tenths of a second (the documented bounded
# window) re-running the signal for a pid published inside that window, and
# only then remove the tracking files. sway.cancel stays in place after a
# failure (see the header invariant); the next start removes it only after
# proving no launcher of this state is alive, and a successful start
# removes it.
failed_start_cleanup() {
    : > "$1/sway.cancel"
    failed_start_signal "$1"
    _fc_i=0
    while [ "$_fc_i" -lt 5 ]; do
        sleep 0.1; _fc_i=$((_fc_i + 1))
        failed_start_signal "$1"
    done
    rm -f "$1/sway.pid" "$1/sway.identity"
}
# headless_state_path_ok <path>: only A-Z a-z 0-9 / . _ - are allowed.
headless_state_path_ok() {
    case $1 in
        ''|*[!A-Za-z0-9/._-]*) return 1 ;;
        *) return 0 ;;
    esac
}
die_bad_state_path() {
    die "headless: state path '$1' is not allowed: a state path may only contain A-Z a-z 0-9 / . _ -"
}
# state_launcher_alive <state>: 0 = a launcher or sway of this state is
# alive, 1 = none is, 2 = that cannot be told (a scan that cannot be
# completed counts as alive to the caller). Rule: (i) the pid in sway.pid,
# when present, is alive as the launcher form (its cmdline contains
# 'exec sway' with this state as its $1) or as the exact sway form
# sway -c <state>/sway.conf; (ii) a scan of /proc/*/cmdline finds any
# process whose argv contains this state's sway.conf path, or whose
# cmdline is the launcher sh -c ... exec sway ... with this state as $1
# (this finds a launcher that has not yet published sway.pid).
state_launcher_alive() {
    _la_state=$1
    _la_tmp=$(mktemp) || return 2
    if [ -f "$_la_state/sway.pid" ]; then
        _la_pid=$(cat "$_la_state/sway.pid" 2>/dev/null) || _la_pid=
        if [ -n "$_la_pid" ] && [ -d "/proc/$_la_pid" ]; then
            if sway_cmdline_matches "$_la_pid" "$_la_state"; then rm -f "$_la_tmp"; return 0; fi
            if tr '\0' '\n' < "/proc/$_la_pid/cmdline" > "$_la_tmp" 2>/dev/null; then
                if grep -Fq 'exec sway' "$_la_tmp" && grep -Fxq "$_la_state" "$_la_tmp"; then
                    rm -f "$_la_tmp"; return 0
                fi
            elif [ -d "/proc/$_la_pid" ]; then
                rm -f "$_la_tmp"; return 2
            fi
        fi
    fi
    [ -d /proc ] || { rm -f "$_la_tmp"; return 2; }
    _la_unknown=0
    for _la_entry in /proc/[0-9]*; do
        [ -d "$_la_entry" ] || continue
        if ! tr '\0' '\n' < "$_la_entry/cmdline" > "$_la_tmp" 2>/dev/null; then
            [ -d "$_la_entry" ] && _la_unknown=1
            continue
        fi
        [ -s "$_la_tmp" ] || continue
        if grep -Fq "$_la_state/sway.conf" "$_la_tmp"; then rm -f "$_la_tmp"; return 0; fi
        if grep -Fq 'exec sway' "$_la_tmp" && grep -Fxq "$_la_state" "$_la_tmp"; then
            rm -f "$_la_tmp"; return 0
        fi
    done
    rm -f "$_la_tmp"
    if [ "$_la_unknown" = 1 ]; then return 2; fi
    return 1
}
# Physical-path capture with a sentinel: a plain $(cd ... && pwd -P) (or
# $(dirname ...) / $(basename ...)) strips ALL trailing newlines, so a name
# ending in a newline would be silently truncated before the whitelist
# check below (a symlink to a directory named "state<LF>" would resolve to
# ".../state"). Capture with a trailing x inside the substitution, remove
# the x, then remove exactly one trailing newline -- the one the command
# itself adds -- so a real newline in the name survives in _phys.
_phys_dir() {
    _pd_raw=$(cd "$1" 2>/dev/null && pwd -P && printf x) || return 1
    _pd_raw=${_pd_raw%x}
    case $_pd_raw in
        *"$LF") _phys=${_pd_raw%?} ;;
        *) return 1 ;;
    esac
}
_phys_dirname() {
    _pd_raw=$(dirname "$1" && printf x) || return 1
    _pd_raw=${_pd_raw%x}
    case $_pd_raw in
        *"$LF") _phys=${_pd_raw%?} ;;
        *) return 1 ;;
    esac
}
_phys_basename() {
    _pd_raw=$(basename "$1" && printf x) || return 1
    _pd_raw=${_pd_raw%x}
    case $_pd_raw in
        *"$LF") _phys=${_pd_raw%?} ;;
        *) return 1 ;;
    esac
}
do_headless() {
    sub=${1:-}; state=${2:-}
    [ -n "$sub" ] && [ -n "$state" ] || die "usage: headless start|shot|stop <state> ..."
    # Whitelist first, before any side effect (before mkdir and before
    # reading or writing any file in the state dir): the path as given must
    # match it, and so must the pwd -P resolved path (an empty string and a
    # path with a .. component after resolution are fine). Resolving the
    # existing parent chain here keeps a disallowed resolved path from
    # creating anything either.
    headless_state_path_ok "$state" || die_bad_state_path "$state"
    case $state in
        /*) _hl_abs=$state ;;
        *) _phys_dir . || die_bad_state_path "$state"
           if [ "$_phys" = / ]; then _hl_abs=/$state; else _hl_abs=$_phys/$state; fi ;;
    esac
    _hl_work=$_hl_abs; _hl_suffix=
    while [ ! -d "$_hl_work" ]; do
        _phys_basename "$_hl_work" || die_bad_state_path "$state"
        _hl_suffix=/$_phys$_hl_suffix
        _phys_dirname "$_hl_work" || die_bad_state_path "$state"
        _hl_parent=$_phys
        [ "$_hl_parent" != "$_hl_work" ] || break
        _hl_work=$_hl_parent
    done
    _hl_resolved=$_hl_abs
    if [ -d "$_hl_work" ]; then
        _phys_dir "$_hl_work" || die_bad_state_path "$state"
        _hl_base=$_phys
        if [ "$_hl_base" = / ]; then _hl_resolved=$_hl_suffix; else _hl_resolved=$_hl_base$_hl_suffix; fi
        [ -n "$_hl_resolved" ] || _hl_resolved=/
        headless_state_path_ok "$_hl_resolved" || die_bad_state_path "$_hl_resolved"
    fi
    shift 2
    if [ "$sub" = start ]; then
        # Always scan for a launcher/sway of this state before touching
        # the state (before mkdir, before writing app/args/run.sh/
        # sway.conf, before removing anything): during a first start
        # that is still pending neither sway.pid nor sway.cancel may
        # exist yet although its launcher is already alive, so gating
        # the scan on those files would let a second start in and the
        # first launcher would later overwrite sway.pid, leaving a sway
        # untracked. Alive or unknown: refuse and touch nothing.
        # Stale-file removal happens only when the scan says none is
        # alive AND one of the stale files exists.
        _hl_alive_rc=0
        state_launcher_alive "$_hl_resolved" || _hl_alive_rc=$?
        if [ "$_hl_alive_rc" != 1 ]; then
            die "state $_hl_resolved still has a running sway or launcher; run \`headless stop $_hl_resolved\` or wait"
        fi
        if [ -e "$_hl_resolved/sway.pid" ] || [ -e "$_hl_resolved/sway.identity" ] || [ -e "$_hl_resolved/sway.cancel" ]; then
            echo "dayz-proton: removing stale sway files in $_hl_resolved" >&2
            rm -f "$_hl_resolved/sway.pid" "$_hl_resolved/sway.identity" "$_hl_resolved/sway.cancel"
        fi
    fi
    mkdir -p "$state"
    _phys_dir "$state" || die_bad_state_path "$state"
    state=$_phys
    headless_state_path_ok "$state" || die_bad_state_path "$state"
    case $sub in
    start)
        [ $# -ge 1 ] || die "usage: headless start <state> <Tool> [args...]"
        command -v sway >/dev/null || die "sway is needed for headless runs"
        command -v setsid >/dev/null || die "setsid is needed for headless runs"
        case ${DAYZ_PROTON_START_WAIT_TENTHS:-50} in ''|*[!0-9]*) die "DAYZ_PROTON_START_WAIT_TENTHS must be a non-negative integer (tenths of a second)" ;; esac
        # The launcher scan and the stale-file rule ran above, before
        # the state was touched (see do_headless, before mkdir -p).
        app=830640; [ "$1" = DayZDiag ] && app=221100
        if ! busy=$(prefix_wineserver "$(prefix_dir $app)"); then
            die "cannot tell whether prefix $(prefix_dir $app) is in use; treating it as busy: one display per prefix"
        fi
        [ -z "$busy" ] || die "prefix $(prefix_dir $app) is in use (wineserver $busy): one display per prefix; stop that session first"
        echo $app > "$state/app"
        : > "$state/args"; for a in "$@"; do printf '%s\n' "$a" >> "$state/args"; done
        cat > "$state/run.sh" <<EOF
#!/bin/sh
echo "\$WAYLAND_DISPLAY" > "$state/wayland-display"
set --
while IFS= read -r a; do set -- "\$@" "\$a"; done < "$state/args"
exec "$me" gui "\$@"
EOF
        chmod +x "$state/run.sh"
        printf 'output HEADLESS-1 resolution %s position 0 0\nxwayland enable\nexec %s/run.sh > %s/run.log 2>&1\n' \
            "${RES:-1600x900}" "$state" "$state" > "$state/sway.conf"
        rm -f "$state/wayland-display"
        # One launcher form only, with setsid required above (no nohup: a
        # setsid session is not reached by the terminal's SIGHUP anyway).
        # The child writes its own PID before exec, so the recorded PID is
        # the sway process itself even when setsid forks under job control.
        # It checks sway.cancel before writing sway.pid and again just after:
        # if a failed start has cancelled, it removes its pid and exits
        # instead of exec'ing a sway the parent can no longer track.
        WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 setsid sh -c '[ ! -e "$1/sway.cancel" ] || exit 0; echo $$ > "$1/sway.pid"; if [ -e "$1/sway.cancel" ]; then rm -f "$1/sway.pid"; exit 0; fi; exec sway -c "$1/sway.conf"' sh "$state" \
            > "$state/sway.log" 2>&1 &
        _hl_wait=${DAYZ_PROTON_START_WAIT_TENTHS:-50}
        case $_hl_wait in ''|*[!0-9]*) die "DAYZ_PROTON_START_WAIT_TENTHS must be a non-negative integer (tenths of a second)" ;; esac
        # Success requires the exec to have happened: comm is sway and the
        # argv is exactly sway -c <state>/sway.conf. Exhausting the wait is
        # a failed start, and no identity is published for the launcher.
        _hl_i=0; _hl_ready=0; pid=
        while [ "$_hl_i" -lt "$_hl_wait" ]; do
            sleep 0.1; _hl_i=$((_hl_i + 1))
            # Test-only hook: when DAYZ_PROTON_TEST_HOOK is set it names a
            # command run once per wait iteration with the iteration number
            # and the total, so a test can synchronise on the parent reaching
            # its last iteration. Inert when unset; not a user knob.
            if [ -n "${DAYZ_PROTON_TEST_HOOK:-}" ]; then
                "$DAYZ_PROTON_TEST_HOOK" "$_hl_i" "$_hl_wait" || true
            fi
            if [ -s "$state/sway.pid" ]; then
                pid=$(cat "$state/sway.pid" 2>/dev/null) || pid=
                if [ -n "$pid" ] && [ -d "/proc/$pid" ]; then
                    _hl_comm=$(cat "/proc/$pid/comm" 2>/dev/null) || _hl_comm=
                    if [ "$_hl_comm" = sway ] && sway_cmdline_matches "$pid" "$state"; then
                        _hl_ready=1; break
                    fi
                fi
            fi
        done
        if [ "$_hl_ready" != 1 ]; then
            # Cancel first, then signal only the child this start launched,
            # re-check for a pid published in the bounded window, and only
            # then remove tracking (see failed_start_cleanup). This is what
            # makes DAYZ_PROTON_START_WAIT_TENTHS=0 fail cleanly too: the
            # child sees sway.cancel and never execs sway.
            failed_start_cleanup "$state"
            die "sway did not start in $state (see $state/sway.log)"
        fi
        _hl_comm=$(cat "/proc/$pid/comm" 2>/dev/null) || _hl_comm=
        [ "$_hl_comm" = sway ] && sway_cmdline_matches "$pid" "$state" \
            || { failed_start_cleanup "$state"; die "sway did not start in $state (see $state/sway.log)"; }
        _hl_start=$(proc_starttime "$pid") || { failed_start_cleanup "$state"; die "sway did not stay up (see $state/sway.log)"; }
        {
            printf '%s\n' "$_hl_start"
            tr '\0' '\n' < "/proc/$pid/cmdline"
        } > "$state/sway.identity"
        rm -f "$state/sway.cancel"
        echo "headless sway $pid, log $state/run.log" ;;
    shot)
        [ -s "$state/wayland-display" ] || die "no session in $state"
        command -v grim >/dev/null || die "grim is needed for screenshots"
        WAYLAND_DISPLAY=$(cat "$state/wayland-display") grim "${1:?usage: headless shot <state> <out.png>}" ;;
    stop)
        [ -f "$state/sway.pid" ] || die "no session in $state"
        pid=$(cat "$state/sway.pid" 2>/dev/null) || die "no session in $state"
        if ! sway_identity_ok "$pid" "$state"; then
            echo "dayz-proton: the sway in $state is not verified as this session's (stale or foreign pid $pid); not signalling it, and leaving its wineserver alone" >&2
            rm -f "$state/sway.pid" "$state/sway.identity"
            return 0
        fi
        kill "$pid" 2>/dev/null || true
        rm -f "$state/sway.pid" "$state/sway.identity"
        if [ -f "$state/app" ]; then
            _hl_app=$(cat "$state/app" 2>/dev/null) || _hl_app=
            # The recorded display is its first line only. A file holding
            # just a newline has bytes, but $(...) strips it to empty, and
            # an empty display must signal no wineserver at all (an empty
            # display would otherwise mean "do not filter").
            _hl_disp=
            if [ -f "$state/wayland-display" ]; then
                _hl_disp=$(head -n 1 "$state/wayland-display" 2>/dev/null) || _hl_disp=
            fi
            if [ -n "$_hl_app" ] && [ -n "$_hl_disp" ]; then
                signal_session_wineservers "$(prefix_dir "$_hl_app")" "$_hl_disp"
            elif [ -n "$_hl_app" ]; then
                # Guard also lives in signal_session_wineservers; this
                # branch only chooses the one-line message.
                echo "dayz-proton: no recorded display for $state; leaving the wineserver alone" >&2
            else
                echo "dayz-proton: no recorded app for $state; leaving the wineserver alone" >&2
            fi
        else
            echo "dayz-proton: no recorded display for $state; leaving the wineserver alone" >&2
        fi ;;
    *) die "unknown headless command '$sub'" ;;
    esac
}

# ---------------------------------------------------------------- init / doctor
do_init() {
    if [ $# -ge 1 ]; then
        pr=$(cd "$1" && pwd -P) || die "$1 does not exist"
        mkdir -p "$H"; printf '%s\n' "$pr" > "$H/p-root"
    fi
    # Snapshot the wineservers of the prefixes this init actually uses
    # (830640 always; 221100 only when a P: root maps it) before creating
    # anything. At the end only wineservers that were not running when init
    # began are stopped, in those prefixes; an unknown snapshot never signals.
    if _in_snap830=$(prefix_wineserver "$(prefix_dir 830640)"); then _in_ok830=1; else _in_snap830=; _in_ok830=0; fi
    _in_use221=0; _in_snap221=; _in_ok221=0
    if [ -n "$(p_root)" ]; then
        _in_use221=1
        if _in_snap221=$(prefix_wineserver "$(prefix_dir 221100)"); then _in_ok221=1; else _in_snap221=; _in_ok221=0; fi
    fi
    ensure_prefix 830640
    import_registry
    [ "${DAYZ_PROTON_PREFIX:-}" = steam ] || install_vcredist
    appdir 221100 >/dev/null 2>&1 || echo "dayz-proton: DayZ (221100) not installed; game key skipped" >&2
    echo "tools prefix $STEAM_COMPAT_DATA_PATH: registry from installscript.vdf + DayZ 'main' imported"
    pr=$(p_root)
    if [ -n "$pr" ]; then
        for app in 830640 221100; do
            proton_env $app; ensure_prefix $app
            ln -sfn "$pr" "$STEAM_COMPAT_DATA_PATH/pfx/dosdevices/p:"
            echo "prefix $app: P: -> $pr"
        done
    else
        echo "no P: root given; run '$me init <dir>' to map P:"
    fi
    signal_new_wineservers "$(prefix_dir 830640)" "$_in_snap830" "$_in_ok830" ""
    if [ "$_in_use221" = 1 ]; then
        signal_new_wineservers "$(prefix_dir 221100)" "$_in_snap221" "$_in_ok221" ""
    fi
}

# check_dayzmake: the native packer is bzed's armake2 fork, renamed dayzmake at v1.0.0. Upstream
# armake2 is built for Arma (its V3 file hash omits *.c, and dayzmake adds DayZ-only functions);
# a fork build from before the rename is called armake2.
check_dayzmake() {
    url="https://github.com/bzed/dayzmake (v2.0.0 or later)"
    b=
    for c in dayzmake armake2; do command -v $c >/dev/null && { b=$c; break; }; done
    if [ -z "$b" ]; then echo "dayzmake:    missing (native PBO build/sign; $url)"; return 0; fi
    if ! $b -h 2>&1 | grep -q -- --proton-binarize; then
        echo "dayzmake:    '$b' is upstream armake2, whose V3 file hash omits *.c; install $url"
        return 0
    fi
    ver=$($b --version 2>&1 | grep -m1 -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
    case $ver in
        ''|0.*) echo "dayzmake:    '$b' is the fork from before the rename (v${ver:-?}); upgrade to $url" ;;
        1.*) echo "dayzmake:    $b v$ver (ok for building; upgrade to >= v2.0.0 before unpacking PBOs you did not build)" ;;
        *) echo "dayzmake:    $b v$ver (ok)" ;;
    esac
}

do_doctor() {
    echo "Steam root:  $STEAM_ROOT"
    echo "Proton:      $(find_proton 2>&1)"
    echo "Prefixes:    tools=$(prefix_dir 830640)  game=$(prefix_dir 221100)"
    echo "P: root:     $(p_root)"
    for app in 221100 223350 830640 1024020 1042420; do
        m=$(manifest $app)
        if [ -z "$m" ]; then printf '%-8s not installed\n' $app; continue; fi
        d=$(appdir $app); st=$(acf "$m" StateFlags)
        v=
        for b in "$d/DayZ_x64.exe" "$d/DayZServer"; do
            [ -f "$b" ] && v=$(strings -n7 "$b" 2>/dev/null | grep -m1 -oE '\b1\.[0-9]{2}\.[0-9]{6}\b' || true)
        done
        flag=; [ "$st" = 4 ] || flag="  (StateFlags $st: update pending or incomplete)"
        printf '%-8s %-26s build %-9s %s%s\n' $app "$(acf "$m" name)" "$(acf "$m" buildid)" "${v:+v$v}" "$flag"
    done
    check_dayzmake
    for c in sway grim; do command -v $c >/dev/null || echo "$c:        missing (needed for headless GUI runs)"; done
    echo "Client and server must report the same v1.30.xxxxxx, or the client is refused (0x00020013)."
}

cmd=${1:-}; [ $# -gt 0 ] && shift
case $cmd in
    doctor)   do_doctor ;;
    init)     do_init "$@" ;;
    winpath)  winpath "${1:?usage: winpath <path>}" ;;
    tool)     run_tool con "$@" ;;
    gui)      run_tool gui "$@" ;;
    binarize) do_binarize "$@" ;;
    headless) do_headless "$@" ;;
    *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$me" >&2; exit 2 ;;
esac
