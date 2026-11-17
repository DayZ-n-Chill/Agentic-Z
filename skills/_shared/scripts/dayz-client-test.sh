#!/bin/sh
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
# Run one automated client+server test: start a local server, start the DayZ client headless,
# wait until the mod's tests print a final line, report, tear everything down.
#
#   dayz-client-test.sh -t <server-tree> -s "<server -mod= list>" -c "<client -mod= list>" [options]
#
#   -e          experimental: use the experimental client (the tree must be an experimental server tree)
#   -t TREE     server tree from make-server-tree.sh (mods and keys already linked, BattlEye = 0)
#   -s MODS     value of the server's -mod=      e.g. "@CF;@AutoTest"
#   -c MODS     value of the client's -mod=      e.g. "@9dd22c91;@AutoTest" (folders in the DayZ client dir)
#   -w SECONDS  give up after this long (default 300; a cold client start alone takes ~60 s)
#   -d REGEX    line that ends the test run (default '\[AUTOTEST\] DONE')
#   -o DIR      keep screenshots/logs here (default: a new temp dir, path printed)
#   -k PREFIX   result-line prefix to print (default '[AUTOTEST]')
#   -m MISSION  server -mission=, relative to the tree (e.g. mpmissions/dayzOffline.chernarusplus);
#               needed with CF, whose path resolution reads it
#
# Exit status: 0 = the DONE line appeared and no result line contains FAIL, 1 = FAIL line or timeout.
# The mod decides what a test is; this only starts, waits, collects and stops (see
# skills/dayz-test-ingame/references/linux-headless-client.md for the RPC-driven harness the
# example mod, skills/dayz-test-ingame/assets/autotest-mod, uses).
set -eu

here=$(cd "$(dirname "$0")" && pwd -P)
eflag='' tree='' smods='' cmods='' mission='' wait_s=300 done_re='\[AUTOTEST\] DONE' out='' prefix='[AUTOTEST]'
while getopts et:s:c:w:d:o:k:m: o; do
    case $o in
        e) eflag=-e;; t) tree=$OPTARG;; s) smods=$OPTARG;; c) cmods=$OPTARG;; w) wait_s=$OPTARG;;
        d) done_re=$OPTARG;; o) out=$OPTARG;; k) prefix=$OPTARG;; m) mission=$OPTARG;;
        *) sed -n '2,18p' "$0" >&2; exit 2;;
    esac
done
[ -n "$tree" ] && [ -n "$smods" ] && [ -n "$cmods" ] || { sed -n '2,18p' "$0" >&2; exit 2; }
[ -x "$tree/DayZServer" ] || { echo "no DayZServer in $tree (make-server-tree.sh first)" >&2; exit 2; }
tree=$(cd "$tree" && pwd -P)
# One game at a time: check before spending a server start on a client that would be refused.
"$here/dayz-client-headless.sh" status >&2 || { echo "stop the running DayZ client first (one game at a time)" >&2; exit 1; }
[ -n "$out" ] || out=$(mktemp -d /var/tmp/dzct.XXXXXX)
mkdir -p "$out"

spid=
cleaned=0
cleanup() {
    [ "$cleaned" = 0 ] || return 0
    cleaned=1
    trap '' INT TERM
    "$here/dayz-client-headless.sh" stop "$out/client" 2>/dev/null || true
    if [ -n "$spid" ]; then
        kill "$spid" 2>/dev/null || true
        for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$spid" 2>/dev/null || break; sleep 1; done
        kill -9 "$spid" 2>/dev/null || true
    fi
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

# shellcheck disable=SC2046  # two ports, split on purpose
set -- $("$here/free-ports.sh" 2)
game=$1 query=$2
grep -q '^steamQueryPort' "$tree/serverDZ.cfg" || sed -i '1i steamQueryPort = 0;' "$tree/serverDZ.cfg"
sed -i "s/^steamQueryPort = .*/steamQueryPort = $query;/" "$tree/serverDZ.cfg"

stamp="$out/stamp"; : > "$stamp"

echo "== server: game port $game, mods $smods"
# shellcheck disable=SC3045  # dash and bash both have ulimit -c
(cd "$tree" && ulimit -c 0 && exec ./DayZServer -config=serverDZ.cfg -profiles=profiles \
    "-mod=$smods" ${mission:+"-mission=$mission"} -port="$game" -nosplash -nopause -dologs -adminlog) > "$out/server.log" 2>&1 &
spid=$!
n=0
until grep -q '__SERVER__ CREATED -> CONNECTED' "$out/server.log" 2>/dev/null; do
    kill -0 "$spid" 2>/dev/null || { echo "server exited early, see $out/server.log" >&2; exit 1; }
    n=$((n + 1)); [ "$n" -lt 120 ] || { echo "server not ready after 120 s" >&2; exit 1; }
    sleep 1
done

echo "== client: mods $cmods"
"$here/dayz-client-headless.sh" $eflag start "$out/client" -name=autotest "-mod=$cmods" -connect=127.0.0.1 -port="$game"

# The server's script log of THIS run: the newest one, created after the stamp.
n=0; log=
while :; do
    log=$(find "$tree/profiles" -maxdepth 1 -name 'script_*.log' -newer "$stamp" 2>/dev/null | head -1)
    if [ -n "$log" ] && grep -q "$done_re" "$log" 2>/dev/null; then break; fi
    n=$((n + 2)); [ "$n" -lt "$wait_s" ] || { echo "== timeout after ${wait_s}s, no '$done_re'" >&2
        "$here/dayz-client-headless.sh" shot "$out/client" "$out/timeout.png" 2>/dev/null || true
        [ -z "$log" ] || grep -F "$prefix" "$log" || true; echo "artifacts: $out"; exit 1; }
    sleep 2
done

"$here/dayz-client-headless.sh" shot "$out/client" "$out/final.png" 2>/dev/null || true
grep -F "$prefix" "$log" | sed -E "s/^[0-9:. ]*SCRIPT +: //"
echo "artifacts: $out (server.log, final.png; server script log: $log)"
if grep -F "$prefix" "$log" | grep -q ' FAIL '; then exit 1; fi
