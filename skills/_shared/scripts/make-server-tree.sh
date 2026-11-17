#!/bin/sh
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Build (or refresh) a private DayZ Server directory tree that symlinks into the Steam install.
#
# The Steam install is never written to. Everything the server or you write lands in the tree:
#   <tree>/serverDZ.cfg          copied once, yours to edit
#   <tree>/profiles/             use as -profiles=profiles
#   <tree>/mpmissions/<m>/       real directories with per-file symlinks, so the server's
#                                storage_1/ persistence is written here, not into Steam
#   <tree>/keys/, battleye/      real directories with per-file symlinks (add your own .bikey)
#   <tree>/@Mod                  your mods: symlinks to builds or workshop items (not created here)
#   everything else              one symlink per top-level entry of the Steam install
#
# To edit a Steam-provided file, replace its symlink with a copy:
#   cp --remove-destination "$(readlink <tree>/mpmissions/<m>/init.c)" <tree>/mpmissions/<m>/init.c
# Re-running refreshes the symlinks after a Steam update; real files in the tree are kept.
#
# Usage: make-server-tree.sh <tree> [<steam DayZServer dir>]   (default: find-dayzserver.sh)
set -eu

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
    echo "usage: $0 <tree> [<steam DayZServer dir>]" >&2
    exit 2
fi
tree=$1
src=${2:-$("$(dirname "$0")/find-dayzserver.sh")}
src=$(cd "$src" && pwd -P)
src_slash=${src%/}/

# Resolve deepest existing ancestor BEFORE any mkdir: refuse '..' in non-existing tail or a tree inside Steam.
case $tree in /*) _abs=$tree ;; *) _abs=$(pwd -P)/$tree ;; esac
_work=$_abs; _suffix=
while [ ! -d "$_work" ]; do
    _base=$(basename "$_work")
    case $_base in
        ..) echo "error: tree path contains '..' in a non-existing component: $tree" >&2; exit 2 ;;
        .|'') ;;
        *) _suffix=/$_base$_suffix ;;
    esac
    _parent=$(dirname "$_work")
    [ "$_parent" != "$_work" ] || break
    _work=$_parent
done
if [ -d "$_work" ]; then
    _anc=$(cd "$_work" && pwd -P)
    if [ "$_anc" = / ]; then _resolved=$_suffix; else _resolved=$_anc$_suffix; fi
    [ -n "$_resolved" ] || _resolved=/
    case "${_resolved%/}/" in "$src_slash"*) echo "error: the tree must be outside the Steam install" >&2; exit 2;; esac
fi
mkdir -p "$tree"
tree=$(cd "$tree" && pwd -P)
case "${tree%/}/" in "$src_slash"*) echo "error: the tree must be outside the Steam install" >&2; exit 2;; esac

# resolved_link_target <link>: print resolved target path (best effort).
resolved_link_target() {
    _t=$(readlink "$1") || { printf '%s\n' ""; return; }
    case $_t in /*) _b=$_t ;; *) _b=$(dirname "$1")/$_t ;; esac
    _p=$(dirname "$_b")
    if [ -d "$_p" ]; then _p=$(cd "$_p" && pwd -P); printf '%s/%s\n' "$_p" "$(basename "$_b")"; else printf '%s\n' "$_b"; fi
}
into_src() {
    [ -L "$1" ] || return 1
    if [ -d "$1" ]; then
        _r=$(cd "$1" 2>/dev/null && pwd -P) || _r=$(resolved_link_target "$1")
    else
        _r=$(resolved_link_target "$1")
    fi
    case "${_r%/}/" in "$src_slash"*) return 0 ;; *) return 1 ;; esac
}
# ensure_real_dir <path>: replace a symlink (into src, or any symlink for private dirs) with a real dir.
ensure_real_dir() {
    if [ -L "$1" ]; then
        echo "replacing symlink $1 with a real directory (never write through it into the Steam install)" >&2
        rm "$1"
    fi
    mkdir -p "$1"
}
refuse_if_into_src() {
    if into_src "$1"; then echo "error: writable tree target $1 resolves into the Steam install; refusing to continue" >&2; exit 2; fi
    if [ -d "$1" ] && [ ! -L "$1" ]; then
        _r=$(cd "$1" && pwd -P)
        case "${_r%/}/" in "$src_slash"*) echo "error: writable tree target $1 resolves into the Steam install; refusing to continue" >&2; exit 2;; esac
    fi
}

# sanitize_private_children <dir>: review every existing directory entry under a private dir
# (mpmissions, keys, battleye). Any directory symlink resolving into Steam is replaced with a
# real directory of per-file links so later writes (such as storage_1) never land in Steam.
sanitize_private_children() {
    if [ ! -d "$1" ] || [ -L "$1" ]; then return 0; fi
    for _e in "$1"/* "$1"/.[!.]* "$1"/..?*; do
        [ -e "$_e" ] || [ -L "$_e" ] || continue
        if [ -L "$_e" ] && [ -d "$_e" ] && into_src "$_e"; then
            _target=$(cd "$_e" && pwd -P)
            echo "replacing directory symlink $_e -> $_target with a real directory of per-file links" >&2
            link_contents "$_target" "$_e"
        elif [ -d "$_e" ] && [ ! -L "$_e" ]; then
            refuse_if_into_src "$_e"
        fi
    done
}

link_entry() {
    if [ -L "$2" ] || [ ! -e "$2" ]; then
        ln -sfn "$1" "$2"
    fi
}
link_contents() {
    [ -L "$2" ] && rm "$2"
    mkdir -p "$2"
    for f in "$1"/* "$1"/.[!.]*; do
        [ -e "$f" ] || [ -L "$f" ] || continue
        case "${f##*/}" in storage_*) continue;; esac
        link_entry "$f" "$2/${f##*/}"
    done
    # Persistence already in the destination must be private, never a link into src.
    for s in "$2"/storage_*; do
        [ -e "$s" ] || [ -L "$s" ] || continue
        if [ -L "$s" ]; then ensure_real_dir "$s"; fi
    done
}

for f in "$src"/*; do
    name=${f##*/}
    case "$name" in
        core|core.*|@*|profiles) continue ;;
        serverDZ.cfg)
            if [ -L "$tree/$name" ]; then rm "$tree/$name"; fi
            [ -e "$tree/$name" ] || cp "$f" "$tree/$name" ;;
        keys|battleye) link_contents "$f" "$tree/$name" ;;
        mpmissions)
            ensure_real_dir "$tree/mpmissions"
            for m in "$f"/*/; do
                m=${m%/}
                link_contents "$m" "$tree/mpmissions/${m##*/}"
            done ;;
        *) link_entry "$f" "$tree/$name" ;;
    esac
done
ensure_real_dir "$tree/profiles"
for _pdir in "$tree/mpmissions" "$tree/keys" "$tree/battleye"; do
    if [ -L "$_pdir" ]; then ensure_real_dir "$_pdir"; fi
done
# serverDZ.cfg must be a real file of the tree.
if [ -L "$tree/serverDZ.cfg" ]; then rm "$tree/serverDZ.cfg"; cp "$src/serverDZ.cfg" "$tree/serverDZ.cfg"; fi
for _w in "$tree/profiles" "$tree/keys" "$tree/battleye" "$tree/mpmissions" "$tree/serverDZ.cfg"; do
    [ -e "$_w" ] || [ -L "$_w" ] || continue
    refuse_if_into_src "$_w"
done
for _pdir in "$tree/mpmissions" "$tree/keys" "$tree/battleye"; do
    sanitize_private_children "$_pdir"
done
for _m in "$tree/mpmissions"/* "$tree/mpmissions"/.[!.]* "$tree/mpmissions"/..?*; do
    [ -d "$_m" ] || continue
    refuse_if_into_src "$_m"
    for s in "$_m"/storage_*; do
        [ -e "$s" ] || [ -L "$s" ] || continue
        if [ -L "$s" ]; then ensure_real_dir "$s"; fi
        refuse_if_into_src "$s"
    done
done

find "$tree" -path "$tree/profiles" -prune -o -type l ! -exec test -e {} \; -print | while IFS= read -r l; do
    case "$(readlink "$l")/" in "$src_slash"*) rm "$l" ;; *)
        _r=$(resolved_link_target "$l"); case "${_r%/}/" in "$src_slash"*) rm "$l" ;; esac ;;
    esac
done

echo "$tree"
