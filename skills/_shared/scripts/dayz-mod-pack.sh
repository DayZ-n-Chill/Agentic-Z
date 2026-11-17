#!/usr/bin/env bash
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Prepare a DayZ mod for the Steam Workshop with dayzmake: keys, PBOs, signatures, upload folder.
#
# Project layout (created by `init`, filled by `keygen` and `build`):
#   .dayzmod            MOD_NAME=MyMod (read by every command)
#   mod.cpp             OPTIONAL launcher metadata (not created by init); copied to the content folder if present
#   src/<Addon>/        one folder per PBO: config.cpp, $PREFIX$, scripts/, data/ ...
#   static/             copied verbatim into the content folder (logos, README, ...)
#   keys/<Key>.bikey    PUBLIC key, safe to commit; shipped to server owners
#   secrets/            PRIVATE key (<Key>.biprivatekey). Git-ignored, never copied anywhere.
#   workshop.toml       written by `workshop create`; kept in git, copied into the content folder
#   build/@<MyMod>/     the Workshop content folder: addons/*.pbo + *.bisign, keys/ (+ mod.cpp if you have one)
#
# Usage: dayz-mod-pack.sh [-C <projectdir>] <command> [options]
#   init <ModName> [--servermod]
#                           create the folders, .gitignore, .workshopignore; WORKSHOP_TAGS in .dayzmod
#                           defaults to "Mod" ("Server" with --servermod; exactly one of the two)
#   keygen                  create secrets/<Key>.biprivatekey and keys/<Key>.bikey (refuses to overwrite)
#   build [--no-bin] [--v2] [--binarize-models]
#                           build+sign every src/<Addon>/ and assemble build/@<ModName>/
#                           --no-bin  pack without rapifying config.cpp (dayzmake pack)
#                           --v2      sign with the older v2 signature instead of v3
#                           --binarize-models  convert .p3d/.rtm (MLOD -> ODOL) via dayzmake --proton-binarize
#                                    (BI's binarize.exe from DayZ Tools under Proton; Linux only,
#                                    see skills/dayz-pbo-build/references/dayzmake-linux.md). Sources stay untouched.
#   check                   verify nothing secret is tracked or staged, and the signatures verify
#   publish-hint            print the `workshop create` / `workshop update` commands
#
# Environment: DAYZMAKE (binary, default: dayzmake from PATH, else bzed's older armake2 fork; upstream armake2 is rejected),
#              KEY_NAME (default: ModName),
#              WORKSHOP_APP_ID (default 221100, the DayZ client app),
#              STEAM_ROOT, DAYZ_TOOLS, PROTON: passed through to dayzmake for --binarize-models.
# Nothing here talks to Steam: uploading stays a deliberate manual step.
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }
say() { printf '== %s\n' "$*"; }

PROJECT=.
if [ "${1:-}" = "-C" ]; then PROJECT=${2:?-C needs a directory}; shift 2; fi
CMD=${1:-}; [ $# -gt 0 ] && shift
[ -n "$CMD" ] || { sed -n '2,/^set -euo/p' "$0" | sed '$d;s/^# \{0,1\}//'; exit 2; }

DAYZMAKE=${DAYZMAKE:-${ARMAKE2:-$(command -v dayzmake || command -v armake2 || echo dayzmake)}}
APP_ID=${WORKSHOP_APP_ID:-221100}
case $APP_ID in ''|*[!0-9]*) die "WORKSHOP_APP_ID must contain digits only: $APP_ID" ;; esac

# Files that must never end up inside a PBO or the Workshop upload.
PBO_EXCLUDES=('*.psd' '*.xcf' '*.kra' '*.blend' '*.blend1' '*.bak' '*.tmp' '*.biprivatekey' 'Thumbs.db' '.DS_Store')

load_conf() {
    [ -f "$PROJECT/.dayzmod" ] || die "no $PROJECT/.dayzmod; run: $0 init <ModName>"
    # Parse .dayzmod as data, never source it: KEY=value, value bare or in one pair of
    # single/double quotes, no escapes, no $ ` ; | & , blank and # comment lines only.
    local _env_key_name=${KEY_NAME:-}
    MOD_NAME=; KEY_NAME=; WORKSHOP_TAGS=
    local _line _key _val _lineno=0 _seen=""
    while IFS= read -r _line || [ -n "$_line" ]; do
        _lineno=$((_lineno + 1))
        case $_line in ''|'#'*) continue ;; esac
        case $_line in *=*) ;; *) die ".dayzmod line $_lineno: unsupported syntax (expected KEY=value)" ;; esac
        _key=${_line%%=*}; _val=${_line#*=}
        case $_key in MOD_NAME|KEY_NAME|WORKSHOP_TAGS) ;; *) die ".dayzmod line $_lineno: unknown key '$_key'" ;; esac
        case " $_seen " in *" $_key "*) die ".dayzmod line $_lineno: duplicate key '$_key'" ;; esac
        _seen="$_seen $_key"
        case $_val in
            *'$'*|*'`'*|*';'*|*'|'*|*'&'*|*'\'*) die ".dayzmod line $_lineno: unsupported character in value" ;;
        esac
        if [ "${#_val}" -ge 2 ] && [ "${_val:0:1}" = "'" ] && [ "${_val: -1}" = "'" ]; then
            _val=${_val:1:-1}
            case $_val in *"'"*) die ".dayzmod line $_lineno: unsupported quote in value" ;; esac
        elif [ "${#_val}" -ge 2 ] && [ "${_val:0:1}" = '"' ] && [ "${_val: -1}" = '"' ]; then
            _val=${_val:1:-1}
            case $_val in *'"'*) die ".dayzmod line $_lineno: unsupported quote in value" ;; esac
        else
            case $_val in *[!A-Za-z0-9_.,:+-]*|'') die ".dayzmod line $_lineno: unsupported unquoted value" ;; esac
        fi
        printf -v "$_key" '%s' "$_val"
    done < "$PROJECT/.dayzmod"
    [ -n "${MOD_NAME:-}" ] || die ".dayzmod does not set MOD_NAME"
    KEY_NAME=${KEY_NAME:-${_env_key_name:-$MOD_NAME}}
    WORKSHOP_TAGS=${WORKSHOP_TAGS:-Mod}
    case $MOD_NAME in .|..) die "MOD_NAME must not be . or .." ;; esac
    case $MOD_NAME in *[!A-Za-z0-9_.-]*|'') die "MOD_NAME may only contain letters, digits, _ . -" ;; esac
    case $KEY_NAME in .|..) die "KEY_NAME must not be . or .." ;; esac
    case $KEY_NAME in *[!A-Za-z0-9_.-]*|'') die "KEY_NAME may only contain letters, digits, _ . -" ;; esac
    # Split the tags as data: read -a splits on blanks and, unlike an unquoted $WORKSHOP_TAGS, never expands
    # * ? [ against the current directory.
    read -r -a WORKSHOP_TAG_LIST <<< "$WORKSHOP_TAGS"
    local _tag
    for _tag in "${WORKSHOP_TAG_LIST[@]}"; do
        case $_tag in *[!A-Za-z0-9_-]*|'') die "WORKSHOP_TAGS tag '$_tag' may only contain letters, digits, _ -" ;; esac
    done
    CONTENT="$PROJECT/build/@$MOD_NAME"
}
# Refuse a symlinked build/content path before any rm -rf or delete under it.
check_content_confinement() {
    local _proj_real
    _proj_real=$(cd "$PROJECT" && pwd -P) || die "project $PROJECT not found"
    if [ -e "$PROJECT/build" ] || [ -L "$PROJECT/build" ]; then
        if [ ! -d "$PROJECT/build" ] || [ -L "$PROJECT/build" ]; then
            die "$PROJECT/build is not a real directory under the project; refusing"
        fi
        case "$(cd "$PROJECT/build" && pwd -P)/" in "$_proj_real"/*) ;; *) die "$PROJECT/build resolves outside the project; refusing" ;; esac
    fi
    if [ -e "$CONTENT" ] || [ -L "$CONTENT" ]; then
        if [ ! -d "$CONTENT" ] || [ -L "$CONTENT" ]; then
            die "$CONTENT is not a real directory under the project; refusing"
        fi
        case "$(cd "$CONTENT" && pwd -P)/" in "$_proj_real"/*) ;; *) die "$CONTENT resolves outside the project; refusing" ;; esac
    fi
}
scan_static() {
    [ -e "$PROJECT/static" ] || [ -L "$PROJECT/static" ] || return 0
    [ -L "$PROJECT/static" ] && die "static/ is a symlink; refusing to copy it"
    local _hit
    _hit=$(find "$PROJECT/static" -type l -print -quit) || die "scan of static/ failed"
    [ -z "$_hit" ] || die "static/ contains a symlink; refusing to copy it: $_hit"
    _hit=$(find "$PROJECT/static" -type f -iname '*.biprivatekey' -print -quit) || die "scan of static/ failed"
    [ -z "$_hit" ] || die "a .biprivatekey is inside static/; refusing before any copy: $_hit"
}

# Use the dayzmake found in PATH first (or $DAYZMAKE). bzed's fork (https://github.com/bzed/dayzmake) is detected by its --proton-binarize option:
#   dayzmake -h 2>&1 | grep -- --proton-binarize
need_dayzmake() {
    command -v "$DAYZMAKE" >/dev/null 2>&1 || die "dayzmake not found in PATH. Install dayzmake >= 1.0.0: the release binary from https://github.com/bzed/dayzmake/releases/tag/v1.0.0, or cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0; or set DAYZMAKE=/path/to/dayzmake"
    local help; help=$("$DAYZMAKE" --help 2>&1 || true)
    # Upstream armake2 leaves *.c files out of the PBO signature hash, so signed script mods fail the server's check.
    case "$help" in *--proton-binarize*) ;; *) die "$(command -v "$DAYZMAKE") is not bzed's fork (no --proton-binarize in -h); upstream armake2 signs wrongly. Install dayzmake >= 1.0.0: cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0" ;; esac
    # bzed's fork built before the rename (binary called armake2, version v0.3.0) still works, but may carry bugs fixed since.
    local ver
    ver=$("$DAYZMAKE" --version 2>/dev/null || true)
    ver=${ver%%$'\n'*}
    case "$ver" in
        v1.*|v[2-9].*|v[1-9][0-9].*|*" v1."* ) ;;
        *) echo "warning: $DAYZMAKE reports '$ver'; dayzmake >= 1.0.0 is recommended (the pre-rename armake2 binary may have bugs)" >&2 ;;
    esac
}

cmd_init() {
    local name=${1:?usage: init <ModName> [--servermod]} tags="Mod"
    [ "${2:-}" = "--servermod" ] && tags="Server"
    case "$name" in *[!A-Za-z0-9_]*|"") die "ModName may only contain letters, digits and _ (it becomes the key name and the PBO prefix)";; esac
    mkdir -p "$PROJECT/src" "$PROJECT/keys" "$PROJECT/secrets" "$PROJECT/static"
    # WORKSHOP_TAGS: Steam Workshop tags for app 221100: exactly one type tag (Mod, or Server for servermods) plus any content tags.
    [ -f "$PROJECT/.dayzmod" ] || printf 'MOD_NAME=%s\nWORKSHOP_TAGS="%s"\n' "$name" "$tags" > "$PROJECT/.dayzmod"

    # .gitignore: append only the lines that are missing, never rewrite the user's file.
    touch "$PROJECT/.gitignore"
    for line in 'secrets/' '*.biprivatekey' 'build/'; do
        grep -qxF "$line" "$PROJECT/.gitignore" || echo "$line" >> "$PROJECT/.gitignore"
    done
    # Belt and braces for the uploader: pass this with --ignore-file (see publish-hint).
    [ -f "$PROJECT/.workshopignore" ] || printf '*.biprivatekey\nsecrets/\n*.psd\n*.xcf\n*.kra\n*.blend\n*.blend1\n.git*\n' > "$PROJECT/.workshopignore"
    # A private key left in the project root by mistake should never be committed either.
    local addon
    for addon in "$PROJECT"/src/*/; do
        [ -d "$addon" ] || continue
        [ -f "$addon/\$PREFIX\$" ] || printf '%s\n' "$(basename "$addon")" > "$addon/\$PREFIX\$"
    done
    say "initialised $name in $PROJECT; put each addon in src/<Addon>/ (config.cpp + scripts/ + ...)"
    say "next: $0 keygen"
}

cmd_keygen() {
    load_conf; need_dayzmake
    local priv="$PROJECT/secrets/$KEY_NAME.biprivatekey" pub="$PROJECT/keys/$KEY_NAME.bikey"
    if [ -e "$priv" ] || [ -e "$pub" ]; then
        die "key $KEY_NAME already exists. Replacing it makes every server owner install a new .bikey and breaks existing signatures; delete both files by hand if you really mean it."
    fi
    git -C "$PROJECT" check-ignore -q "secrets/$KEY_NAME.biprivatekey" 2>/dev/null \
        || ! git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
        || die "secrets/ is not git-ignored; run init (or add 'secrets/' and '*.biprivatekey' to .gitignore) first"
    mkdir -p "$PROJECT/secrets" "$PROJECT/keys"
    ( umask 077; "$DAYZMAKE" keygen "$PROJECT/secrets/$KEY_NAME" )
    mv "$PROJECT/secrets/$KEY_NAME.bikey" "$pub"
    chmod 600 "$priv"
    say "private key: $priv  (BACK THIS UP outside the repo; losing it means a new key and new .bikey for all servers)"
    say "public key:  $pub  (commit this; server owners copy it into their keys/ folder)"
}

# meta.cpp is what the official DayZ Publisher adds to the upload (protocol, publishedid, name, timestamp).
# The `workshop` uploader (nozwock/steam-workshop-uploader) rewrites publishedid and timestamp on every DayZ upload.
# We still write it, so the folder is complete for local tests: publishedid is 0
# until workshop.toml holds an item_id, which is what the Windows tools upload on a first publish; 0 breaks client mods.
# timestamp = .NET DateTime.ToBinary() of the UTC time: (unix + 62135596800) * 1e7 + 2^62 (checked against CF's meta.cpp).
copy_atomic() {
    local _src=$1 _dst=$2 _tmp
    _tmp=$(mktemp "$(dirname "$_dst")/.pack.XXXXXX")
    cp -p -- "$_src" "$_tmp"
    mv -f -- "$_tmp" "$_dst"
}

write_meta() {
    local toml="$CONTENT/workshop.toml" id=0 _tmp_meta
    if [ -f "$toml" ] && [ ! -L "$toml" ]; then
        id=$(sed -n 's/^ *item_id *= *\([0-9][0-9]*\).*/\1/p' "$toml") || die "could not read $toml"
        id=${id%%$'\n'*}
        id=${id:-0}
    fi
    _tmp_meta=$(mktemp "$CONTENT/.meta.cpp.XXXXXX")
    printf 'protocol = 1;\npublishedid = %s;\nname = "%s";\ntimestamp = %s;\n' \
        "$id" "$MOD_NAME" "$(( ($(date -u +%s) + 62135596800) * 10000000 + 4611686018427387904 ))" > "$_tmp_meta"
    chmod 0644 "$_tmp_meta"
    mv -f -- "$_tmp_meta" "$CONTENT/meta.cpp"
    if [ "$id" = 0 ]; then say "meta.cpp written with publishedid = 0 (item not created yet)"
    else say "meta.cpp written for Workshop item $id"; fi
}

cmd_build() {
    local mode=build ver=() a binmodels=0
    for a in "$@"; do
        case "$a" in
            --no-bin) mode=pack ;;
            --v2) ver=(--v2) ;;
            --binarize-models) binmodels=1 ;;
            *) die "unknown option: $a" ;;
        esac
    done
    load_conf
    check_content_confinement
    # Clean stale private keys (regular files) and any symlinks inside the upload folder FIRST, before scanning static/.
    if [ -d "$CONTENT" ]; then
        local _stale_key _stale_link
        _stale_key=$(find "$CONTENT" -type f -iname '*.biprivatekey' -print -quit) || die "scan of $CONTENT failed"
        if [ -n "$_stale_key" ]; then
            echo "removing stale private key(s) from content folder: $CONTENT" >&2
            find "$CONTENT" -type f -iname '*.biprivatekey' -delete || die "removing stale private keys from $CONTENT failed"
        fi
        _stale_link=$(find "$CONTENT" -type l -print -quit) || die "scan of $CONTENT failed"
        if [ -n "$_stale_link" ]; then
            echo "removing symlink(s) from content folder: $CONTENT" >&2
            find "$CONTENT" -type l -delete || die "removing symlinks from $CONTENT failed"
        fi
    fi
    scan_static
    need_dayzmake
    local priv="$PROJECT/secrets/$KEY_NAME.biprivatekey"
    [ -f "$priv" ] || die "no private key at $priv; run: $0 keygen"
    local addons=()
    for a in "$PROJECT"/src/*/; do [ -d "$a" ] && addons+=("${a%/}"); done
    [ ${#addons[@]} -gt 0 ] || die "no addon folders in src/ (expected src/<Addon>/config.cpp)"

    # Rebuild addons/ and keys/ from scratch, but keep workshop.toml and anything else the uploader owns.
    rm -rf "$CONTENT/addons" "$CONTENT/keys"
    mkdir -p "$CONTENT/addons" "$CONTENT/keys"

    local excl=() e
    for e in "${PBO_EXCLUDES[@]}"; do excl+=(-x "$e"); done

    local dir addon pbo srcdir wq
    for dir in "${addons[@]}"; do
        addon=$(basename "$dir")
        [ -f "$dir/config.cpp" ] || echo "warning: src/$addon has no config.cpp; DayZ will not load it as an addon" >&2
        [ -f "$dir/\$PREFIX\$" ] || echo "note: src/$addon has no \$PREFIX\$; dayzmake falls back to the folder name '$addon' as prefix" >&2
        pbo="$CONTENT/addons/$addon.pbo"
        srcdir=$dir; wq=()
        if [ "$binmodels" = 1 ]; then
            [ "$mode" = build ] || die "--binarize-models cannot be combined with --no-bin"
            wq=(--proton-binarize)      # dayzmake runs binarize.exe under Proton
        fi
        say "$mode $addon"
        # Absolute include path so `#include "\MyMod\..."` style includes resolve from the project's src/.
        if [ "$mode" = build ]; then
            "$DAYZMAKE" build -f -i "$PROJECT/src" -e product=dayz "${wq[@]}" "${excl[@]}" "$srcdir" "$pbo"
        else
            "$DAYZMAKE" pack -f -e product=dayz "${excl[@]}" "$srcdir" "$pbo"
        fi
        "$DAYZMAKE" sign -f "${ver[@]}" "$priv" "$pbo"
        "$DAYZMAKE" verify "$PROJECT/keys/$KEY_NAME.bikey" "$pbo" "$pbo.$KEY_NAME.bisign" \
            || die "signature of $addon.pbo does not verify against keys/$KEY_NAME.bikey"
    done

    copy_atomic "$PROJECT/keys/$KEY_NAME.bikey" "$CONTENT/keys/$KEY_NAME.bikey"
    if [ -d "$PROJECT/static" ]; then cp -a "$PROJECT/static/." "$CONTENT/"; fi
    if [ -f "$PROJECT/mod.cpp" ]; then copy_atomic "$PROJECT/mod.cpp" "$CONTENT/mod.cpp"; fi
    if [ -f "$PROJECT/workshop.toml" ] && [ ! -e "$CONTENT/workshop.toml" ] && [ ! -L "$CONTENT/workshop.toml" ]; then
        copy_atomic "$PROJECT/workshop.toml" "$CONTENT/workshop.toml"
    fi
    write_meta

    # The one rule that matters: the private key must not be anywhere under the upload folder.
    local _final_leak
    _final_leak=$(find "$CONTENT" -iname '*.biprivatekey' -print -quit) || die "scan of $CONTENT failed"
    if [ -n "$_final_leak" ]; then
        die "a .biprivatekey is inside $CONTENT; refusing to continue"
    fi
    say "content folder ready: $CONTENT"
    ( cd "$CONTENT" && find . -type f | sort | sed 's|^\./|   |' )
}

# Type tags: exactly one of Mod / Server (Server = servermods only). Content tags: any number, combinable with either.
TYPE_TAGS="Mod Server"
CONTENT_TAGS="Animation Character Economy Environment Equipment Mechanics Sound Props Terrain Vehicle Weapon"
check_tags() {
    local t ntype=0 _check_list
    read -r -a _check_list <<< "${WORKSHOP_TAGS/Tag Review/}"
    for t in "${_check_list[@]}"; do
        case " $TYPE_TAGS " in *" $t "*) ntype=$((ntype + 1)); continue;; esac
        case " $CONTENT_TAGS " in *" $t "*) ;; *) echo "warn: tag '$t' is not a known DayZ tag ($TYPE_TAGS $CONTENT_TAGS)"; ;; esac
    done
    case " $WORKSHOP_TAGS " in *" Tag Review "*) echo "warn: 'Tag Review' is a moderation tag; do not set it yourself";; esac
    if [ "$ntype" = 1 ]; then echo "ok: tags: $WORKSHOP_TAGS"; else echo "FAIL: WORKSHOP_TAGS must contain exactly one of: $TYPE_TAGS (got $ntype)" >&2; return 1; fi
}

cmd_check() {
    load_conf; need_dayzmake
    local bad=0 f
    if [ -d "$PROJECT/.git" ] || git -C "$PROJECT" rev-parse --git-dir >/dev/null 2>&1; then
        local _tracked_keys
        _tracked_keys=$(git -C "$PROJECT" ls-files | awk 'tolower($0) ~ /biprivatekey/ { print }') || die "git ls-files failed"
        if [ -n "$_tracked_keys" ]; then
            echo "FAIL: a .biprivatekey is tracked by git:" >&2
            printf '%s\n' "$_tracked_keys" >&2; bad=1
        else echo "ok: no private key tracked by git"; fi
        if ( set +o pipefail; git -C "$PROJECT" log --all --name-only --format= 2>/dev/null | awk 'tolower($0) ~ /biprivatekey/ { found=1 } END { exit !found }' ); then
            echo "FAIL: a .biprivatekey exists in git history; treat the key as leaked and rotate it" >&2; bad=1
        else echo "ok: no private key in git history"; fi
        git -C "$PROJECT" check-ignore -q "secrets/$KEY_NAME.biprivatekey" \
            && echo "ok: secrets/ is git-ignored" || { echo "FAIL: secrets/$KEY_NAME.biprivatekey is not git-ignored" >&2; bad=1; }
    else
        echo "note: $PROJECT is not a git repository; skipping git checks"
    fi
    if [ -d "$CONTENT" ]; then
        local _chk_leak
        _chk_leak=$(find "$CONTENT" -iname '*.biprivatekey' -print -quit) || die "scan of $CONTENT failed"
        if [ -n "$_chk_leak" ]; then
            echo "FAIL: private key inside the content folder" >&2; bad=1
        fi
    fi
    # Rules the official Publisher enforces (strings in Publisher.exe): addons/ in the root, PBOs only under addons/.
    if [ -d "$CONTENT" ]; then
        if [ -d "$CONTENT/addons" ]; then echo "ok: addons/ is in the content root"; else echo "FAIL: no addons/ folder in the content root" >&2; bad=1; fi
        local _outside_pbo
        _outside_pbo=$(find "$CONTENT" -iname '*.pbo' -not -ipath "$CONTENT/addons/*" -print -quit) || die "scan of $CONTENT failed"
        if [ -n "$_outside_pbo" ]; then
            echo "FAIL: .pbo files outside addons/" >&2; bad=1; fi
        if [ -f "$CONTENT/mod.cpp" ] && grep -q '^ *name *=' "$CONTENT/mod.cpp"; then echo "ok: mod.cpp has a name"
        else echo "note: no mod.cpp with a name in the content folder (optional; the mod works without)"; fi
        if [ ! -f "$CONTENT/meta.cpp" ]; then echo "warn: no meta.cpp; run build"
        elif grep -q 'publishedid *= *0;' "$CONTENT/meta.cpp" && [ -f "$CONTENT/workshop.toml" ]; then
            echo "warn: meta.cpp still has publishedid = 0 but workshop.toml exists; run build again"; fi
    fi
    check_tags || bad=1
    for f in "$CONTENT"/addons/*.pbo; do
        [ -f "$f" ] || { echo "note: nothing built yet (run build)"; break; }
        "$DAYZMAKE" verify "$PROJECT/keys/$KEY_NAME.bikey" "$f" "$f.$KEY_NAME.bisign" >/dev/null \
            && echo "ok: $(basename "$f") signature verifies" || { echo "FAIL: $(basename "$f") signature" >&2; bad=1; }
    done
    [ "$bad" -eq 0 ] || exit 1
}

cmd_publish_hint() {
    load_conf
    case $APP_ID in ''|*[!0-9]*) die "WORKSHOP_APP_ID must contain digits only: $APP_ID" ;; esac
    local tagargs="" t
    for t in "${WORKSHOP_TAG_LIST[@]}"; do tagargs="$tagargs -t $(printf '%q' "$t")"; done
    local q_app q_content q_ignore q_mod q_ctoml q_ptoml q_tags
    q_app=$(printf '%q' "$APP_ID")
    q_content=$(printf '%q' "$CONTENT")
    q_ignore=$(printf '%q' "$PROJECT/.workshopignore")
    q_mod=$(printf '%q' "$MOD_NAME")
    q_ctoml=$(printf '%q' "$CONTENT/workshop.toml")
    q_ptoml=$(printf '%q' "$PROJECT/workshop.toml")
    q_tags=$(printf '%q' "$WORKSHOP_TAGS")
    cat <<EOF
Upload needs the Steam client running and logged in as the account that owns DayZ (app $q_app).
It is a deliberate manual step; review the content folder first:  $q_content

The app id ($q_app) is NOT part of mod.cpp: it is passed here and stored in workshop.toml.
EOF
    local wbin; wbin=$(command -v workshop 2>/dev/null || true)
    if [ -z "$wbin" ]; then echo "WARNING: 'workshop' not found in PATH. Install it: https://github.com/nozwock/steam-workshop-uploader"
    fi
    cat <<EOF

First upload (creates the item and writes $q_ctoml; copy it to $q_ptoml and commit it).
The uploader fills the new item id into meta.cpp before uploading the content. Create it private and make it public in
Steam after checking it:
  workshop create --app-id $q_app --content $q_content --title $q_mod \\
      --ignore-file $q_ignore --glob '!*.biprivatekey' --visibility private$tagargs -m "first upload"

Tags ($q_tags) are stored in workshop.toml by create; update reuses them (Steam drops tags that are not sent).
Updates (item id comes from workshop.toml in the content folder):
  workshop --no-prompt update --content $q_content --ignore-file $q_ignore --glob '!*.biprivatekey' -m "changelog"
EOF
}

case "$CMD" in
    init) cmd_init "$@" ;;
    keygen) cmd_keygen ;;
    build) cmd_build "$@" ;;
    check) cmd_check ;;
    publish-hint) cmd_publish_hint ;;
    *) die "unknown command: $CMD (init, keygen, build, check, publish-hint)" ;;
esac
