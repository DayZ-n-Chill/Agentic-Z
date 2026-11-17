#!/usr/bin/env bash
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Extract the code files (scripts, configs) of the installed vanilla game PBOs with dayzmake.
#
# usage: extract-dayz-sources.sh [--force] <DayZ-install-dir | mod-dir> <out-dir>
#   e.g. extract-dayz-sources.sh ~/.steam/debian-installation/steamapps/common/DayZ /var/tmp/dayz-sources
#   a Workshop mod dir (steamapps/workshop/content/221100/<id>, with an addons/ folder) works the same way
#   --force allows replacing a non-empty <out-dir> that has no pbo-map.tsv (not an earlier extraction).
#
# Searches <install>/dta and <install>/Addons plus the DLC folders <install>/*/addons (case-insensitive).
# Workshop mods are symlinked into the install dir as @xxxx; find does not follow symlinks, so they are skipped.
# Only code is extracted: *.c *.cpp *.h *.hpp *.inc *.json *.cfg *.txt, and config.bin (derapified to config.cpp).
# Models, textures, sounds, layouts and shaders are never read. Files land in <out>/<pbo prefix>/<inner path>,
# e.g. prefix "scripts" -> <out>/scripts/3_Game/..., prefix "DZ\AI" -> <out>/DZ/AI/config.cpp.
# <out>/pbo-map.tsv lists "<prefix>\t<pbo path relative to the install dir>" for every PBO that yielded files
# (build-api-index.py, next to this script, reads it to tell `dayz-api.py src` which PBO holds a file).
# Needs dayzmake on PATH (>= 1.0.0 recommended). bzed's older armake2 fork (pre-rename, may have bugs) is accepted,
# upstream armake2 is not. Write <out-dir> below /var/tmp (/tmp can be a tmpfs and take up RAM), not below $HOME.
# Extraction goes to a staging directory next to <out-dir> and is promoted only on complete success,
# so a re-extraction after a game update drops removed files and never duplicates pbo-map.tsv rows.
set -eu
force=0
if [ "${1:-}" = "--force" ]; then force=1; shift; fi
[ $# -eq 2 ] || { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
install=$1 out=$2
while [ "${#install}" -gt 1 ] && [ "${install%/}" != "$install" ]; do install=${install%/}; done
while [ "${#out}" -gt 1 ] && [ "${out%/}" != "$out" ]; do out=${out%/}; done
[ "$out" != "/" ] || { echo "error: refusing '/' as output directory" >&2; exit 1; }
DZPBO=${DAYZMAKE:-}
if [ -z "$DZPBO" ]; then
  for c in dayzmake armake2; do
    if command -v "$c" >/dev/null 2>&1; then
      _dz_help=$("$c" -h 2>&1 || true)
      case $_dz_help in *--proton-binarize*) DZPBO=$c; break ;; esac
    fi
  done
fi
[ -n "$DZPBO" ] || { echo "dayzmake not found on PATH (upstream armake2 will not do: bzed's fork has --proton-binarize)" >&2; exit 1; }
[ "$DZPBO" = dayzmake ] || echo "note: using $DZPBO; dayzmake >= 1.0.0 is recommended (the pre-rename armake2 binary may have bugs)" >&2
if [ ! -d "$install" ] || [ ! -r "$install" ] || [ ! -x "$install" ]; then
  echo "error: $install is not a readable directory" >&2
  exit 1
fi

# Interrupted promotion from an earlier run: refuse and name the recovery.
for old in "$out".old.*; do
  [ -e "$old" ] || [ -L "$old" ] || continue
  echo "error: a previous promotion was interrupted; recover with: mv -- $(printf '%q' "$old") $(printf '%q' "$out")" >&2
  exit 1
done
if { [ -e "$out" ] || [ -L "$out" ]; } && [ ! -f "$out/pbo-map.tsv" ] && [ "$force" != 1 ]; then
  if [ -d "$out" ] && [ ! -L "$out" ]; then
    _nonempty=$(find "$out" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || echo unreadable)
    if [ -n "$_nonempty" ]; then
      echo "error: $out is non-empty and has no pbo-map.tsv (not an earlier extraction); refusing to replace it (use --force to override)" >&2; exit 1
    fi
  else
    echo "error: $out exists and is not an earlier extraction; refusing to replace it (use --force to override)" >&2; exit 1
  fi
fi

out_parent=$(dirname "$out")
mkdir -p "$out_parent"
lock="$out.lock"
if ! mkdir "$lock" 2>/dev/null; then echo "error: another extraction is running (lock $lock exists)" >&2; exit 1; fi
# The lock is ours from here on: install its cleanup before anything else can fail.
tmp=
cleanup() { if [ -n "$tmp" ]; then rm -rf "$tmp"; fi; rm -rf "$lock"; }
trap cleanup EXIT
tmp=$(mktemp -d /var/tmp/dayz-extract.XXXXXX) || { echo "error: could not create a temporary directory under /var/tmp" >&2; exit 1; }
staging=$(mktemp -d "$out.new.XXXXXX") || { echo "error: could not create staging directory next to $out" >&2; exit 1; }
if [ ! -d "$staging" ] || [ -L "$staging" ]; then
  echo "error: staging path is not a real directory: $staging" >&2
  exit 1
fi

failed=0
note_fail() { echo "error: $*" >&2; failed=1; }

# valid_name <name-after-backslash-conversion>: reject empty, absolute, drive, ./.. or empty segment, controls.
valid_name() {
  local s=$1
  [ -n "$s" ] || return 1
  case $s in /*|[A-Za-z]:*|*/) return 1 ;; esac
  case "/$s/" in */../*|*/./*|*//*) return 1 ;; esac
  if [[ $s =~ [[:cntrl:]] ]]; then return 1; fi
  return 0
}
# pbo_prefix_hex <pbo>: the bytes of the PBO's 'prefix' header extension as space-separated hex, read from the file
# itself: `dayzmake inspect` prints extension values unescaped, so an LF inside or at the end of a value only shows
# as an extra line. Layout as dayzmake v1.0.0 reads it (src/pbo.rs, PBOHeader::read and PBO::read): the first entry
# header is a C-string name and five little-endian u32; packing method "Vers" (bytes 73 72 65 56) makes it the
# version header, followed by key/value C strings up to an empty key. Prints nothing when there is no version header
# or no prefix; returns 1 when the block is cut off (end of file, or past the first 64 KiB) or 'prefix' appears twice
# (dayzmake would keep the last one).
pbo_prefix_hex() {
  od -An -v -tx1 -N 65536 < "$1" | awk '
    function cstr(   s) {
      s = ""
      while (p < n && b[p] != "00") { s = s " " b[p]; p++ }
      if (p >= n) { bad = 1; return "" }
      p++
      return s
    }
    { for (i = 1; i <= NF; i++) b[n++] = $i }
    END {
      p = 0; bad = 0; found = 0; pre = ""
      cstr()
      if (bad || p + 20 > n) exit 1
      if (b[p] b[p + 1] b[p + 2] b[p + 3] != "73726556") exit 0
      p += 20
      while (1) {
        k = cstr(); if (bad) exit 1
        if (k == "") break
        v = cstr(); if (bad) exit 1
        if (k == " 70 72 65 66 69 78") { if (found) exit 1; found = 1; pre = v }
      }
      print substr(pre, 2)
    }'
}
# dest_ok <dest>: resolved path under staging and no symlink on dest or any ancestor under staging.
dest_ok() {
  local dest=$1 resolved staging_resolved p
  staging_resolved=$(realpath -m "$staging")
  resolved=$(realpath -m "$dest")
  case $resolved in "$staging_resolved"/*) ;; *) return 1 ;; esac
  p=$dest
  while [ "$p" != "$staging" ] && [ "$p" != "/" ]; do
    if [ -L "$p" ]; then return 1; fi
    p=$(dirname "$p")
  done
  return 0
}

: > "$staging/pbo-map.tsv"
if ! find "$install" -maxdepth 2 -type d \( -name dta -o -iname addons \) -print0 > "$tmp/dirs"; then
  note_fail "failed to enumerate directories under $install"
fi
if [ "$failed" = 0 ] && [ ! -s "$tmp/dirs" ]; then
  note_fail "no dta/ or addons/ directories found under $install"
fi
sort -z "$tmp/dirs" > "$tmp/dirs.sorted"
total_pbos=0
if [ "$failed" = 0 ]; then
  while IFS= read -r -d '' dir; do
    if [ ! -r "$dir" ] || [ ! -x "$dir" ]; then
      note_fail "directory is not readable: $dir"
      continue
    fi
    if ! find "$dir" -maxdepth 1 -type f -name '*.pbo' -print0 > "$tmp/pbos"; then
      note_fail "failed to enumerate PBOs in $dir"
      continue
    fi
    sort -z "$tmp/pbos" > "$tmp/pbos.sorted"
    while IFS= read -r -d '' pbo; do
      total_pbos=$((total_pbos + 1))
      if ! "$DZPBO" inspect "$pbo" > "$tmp/list" 2>/dev/null; then note_fail "inspect failed (unreadable): $pbo"; continue; fi
      # The stored prefix is checked whole, from the header bytes: a C0 control or DEL anywhere in it (a final LF too,
      # which $() would drop) is refused. Without one, the value fills exactly one '- prefix=' line of the listing,
      # and that line carries dayzmake's own decoding of it (UTF-8, or windows-1252 when the bytes are not UTF-8:
      # src/pbo.rs decode_name), the same text as the entry names the listing gives.
      if ! prefix_hex=$(pbo_prefix_hex "$pbo"); then note_fail "unreadable or malformed PBO header in $pbo; skipping PBO"; continue; fi
      prefix=
      if [ -n "$prefix_hex" ]; then
        case " $prefix_hex " in
          *" "[01][0-9a-f]" "*|*" 7f "*)
            prefix_esc=$(printf '%s' "$prefix_hex" | sed 's/[0-9a-f][0-9a-f]/\\x&/g; s/ //g')
            prefix=$(printf '%b' "$prefix_esc"; printf x)
            note_fail "invalid PBO prefix $(printf '%q' "${prefix%x}") in $pbo (control character in the stored value); skipping PBO"
            continue ;;
        esac
        prefix_lines=$(grep -c '^- prefix=' "$tmp/list" || true)
        if [ "$prefix_lines" != 1 ]; then note_fail "the listing of $pbo has $prefix_lines '- prefix=' lines for one stored prefix; skipping PBO"; continue; fi
        prefix=$(sed -n 's/^- prefix=//p' "$tmp/list"; printf x)
        prefix=${prefix%x}
        prefix=${prefix%$'\n'}
        prefix=${prefix%$'\r'}
        prefix=${prefix//\\//}
      fi
      [ -n "$prefix" ] || prefix=$(basename "$pbo" .pbo)
      if ! valid_name "$prefix"; then note_fail "invalid PBO prefix $(printf '%q' "$prefix") in $pbo; skipping PBO"; continue; fi
      # Cross-check listing: parse '# Files: N', require exact row count after '====', shape, and unique normalised names.
      : > "$tmp/want"
      : > "$tmp/names"
      listing_bad=0
      seen_rows=0
      has_expected=0
      expected_rows=0
      actual_rows=0
      while IFS= read -r row || [ -n "$row" ]; do
        row=${row%$'\r'}
        if [ "$seen_rows" = 0 ]; then
          if [[ $row =~ ^#[[:space:]]*Files:[[:space:]]*([0-9]+)$ ]]; then
            if [ "$has_expected" = 1 ]; then listing_bad=1; else expected_rows=${BASH_REMATCH[1]}; has_expected=1; fi
          else
            case $row in ====*) seen_rows=1 ;; esac
          fi
          continue
        fi
        actual_rows=$((actual_rows + 1))
        if [[ $row =~ [[:cntrl:]] ]]; then listing_bad=1; continue; fi
        if [[ $row =~ ^(.*)[[:space:]]+([^[:space:]]+)[[:space:]]+([0-9]+)[[:space:]]+([0-9]+)[[:space:]]*$ ]]; then
          inner_raw=${BASH_REMATCH[1]}
          orig_size=${BASH_REMATCH[3]}
          inner_raw=${inner_raw%"${inner_raw##*[![:space:]]}"}
          if [ -z "$inner_raw" ]; then listing_bad=1; continue; fi
          norm_name=$(printf '%s' "$inner_raw" | tr '\\' '/')
          while [[ $norm_name == *//* ]]; do norm_name="${norm_name%%//*}/${norm_name#*//}"; done
          printf '%s\n' "$norm_name" >> "$tmp/names"
          printf '%s\t%s\n' "$orig_size" "$inner_raw" >> "$tmp/want"
        else
          listing_bad=1
        fi
      done < "$tmp/list"
      if [ "$seen_rows" != 1 ] || [ "$has_expected" != 1 ] || [ "$actual_rows" -ne "$expected_rows" ]; then
        listing_bad=1
      fi
      if [ "$listing_bad" = 0 ]; then
        unique_rows=$(LC_ALL=C sort -u "$tmp/names" | wc -l)
        unique_rows=${unique_rows//[[:space:]]/}
        if [ "$unique_rows" -ne "$actual_rows" ]; then listing_bad=1; fi
      fi
      if [ "$listing_bad" = 1 ]; then note_fail "invalid listing structure in $pbo; skipping PBO"; continue; fi
      n=0
      pbo_failed=0
      while IFS=$'\t' read -r orig_size inner; do
        rel=$(printf '%s' "$inner" | tr '\\' '/')
        lower=${rel,,}
        case $lower in
          *.c|*.cpp|*.h|*.hpp|*.inc|*.json|*.cfg|*.txt|*config.bin) ;;
          *) continue ;;
        esac
        if ! valid_name "$rel"; then note_fail "invalid entry name '$inner' in $pbo; skipping entry"; pbo_failed=1; continue; fi
        is_config=0
        dest_rel=$rel
        case $lower in *config.bin) is_config=1; dest_rel=${rel%.*}.cpp ;; esac
        dest="$staging/$prefix/$dest_rel"
        if ! dest_ok "$(dirname "$dest")"; then note_fail "destination escapes staging for '$inner' in $pbo"; pbo_failed=1; continue; fi
        if [ -L "$dest" ]; then note_fail "destination is a symlink for '$inner' in $pbo"; pbo_failed=1; continue; fi
        mkdir -p "$(dirname "$dest")"
        if [ -L "$dest" ]; then note_fail "destination is a symlink for '$inner' in $pbo"; pbo_failed=1; continue; fi
        if [ "$is_config" = 1 ]; then
          rm -f "$tmp/config.bin"
          cat_rc=0
          cat_out=$("$DZPBO" cat "$pbo" "$inner" "$tmp/config.bin" 2>&1) || cat_rc=$?
          if [ "$cat_rc" -ne 0 ] || [[ $cat_out == *"not found"* ]] || [ ! -f "$tmp/config.bin" ] || { [ "$orig_size" != 0 ] && [ ! -s "$tmp/config.bin" ]; }; then
            rm -f "$tmp/config.bin"
            note_fail "cat failed (exit $cat_rc): $pbo $inner"; pbo_failed=1; continue
          fi
          if ! "$DZPBO" derapify -f "$tmp/config.bin" "$dest" >/dev/null 2>&1 || [ ! -f "$dest" ]; then
            rm -f "$dest"
            note_fail "derapify failed: $pbo $inner"; pbo_failed=1; continue
          fi
        else
          rm -f "$dest"
          cat_rc=0
          cat_out=$("$DZPBO" cat "$pbo" "$inner" "$dest" 2>&1) || cat_rc=$?
          if [ "$cat_rc" -ne 0 ] || [[ $cat_out == *"not found"* ]] || [ ! -f "$dest" ] || { [ "$orig_size" != 0 ] && [ ! -s "$dest" ]; }; then
            rm -f "$dest"
            note_fail "cat failed (exit $cat_rc): $pbo $inner"; pbo_failed=1; continue
          fi
        fi
        n=$((n + 1))
      done < "$tmp/want"
      if [ "$pbo_failed" = 1 ]; then failed=1; fi
      [ "$n" -gt 0 ] || continue
      echo "$n files  $prefix  <- ${pbo#"$install"/}"
      printf '%s\t%s\n' "$prefix" "${pbo#"$install"/}" >> "$staging/pbo-map.tsv"
    done < "$tmp/pbos.sorted"
  done < "$tmp/dirs.sorted"
fi
if [ "$failed" = 0 ] && [ "$total_pbos" -eq 0 ]; then
  note_fail "no .pbo files found under $install"
fi

if [ "$failed" != 0 ]; then
  echo "error: extraction failed; partial staging kept at $staging (nothing was promoted)" >&2
  # Keep staging: disable its removal (it is only removed on promotion below); trap only cleans tmp/lock.
  exit 1
fi

# Promote: move old aside to a unique non-existent backup name, rename new in, then remove old.
old_backup=
if [ -e "$out" ] || [ -L "$out" ]; then
  old_backup=$(mktemp -u "$out.old.XXXXXX") || { echo "error: could not allocate backup name for $out" >&2; exit 1; }
  if [ -e "$old_backup" ] || [ -L "$old_backup" ]; then
    echo "error: backup path already exists ($old_backup); leaving $out intact" >&2
    exit 1
  fi
  if ! mv -- "$out" "$old_backup"; then echo "error: could not move $out aside; leaving it intact" >&2; exit 1; fi
fi
if ! mv -- "$staging" "$out"; then
  echo "error: could not promote $staging to $out" >&2
  if [ -n "$old_backup" ]; then mv -- "$old_backup" "$out" || echo "error: restore failed; old tree is at $old_backup" >&2; fi
  exit 1
fi
if [ -n "$old_backup" ]; then rm -rf "$old_backup"; fi
