#!/bin/bash
# Wall time and CPU time (user + sys of the command and every child it waited for) of one or two commands.
#
# Usage:
#   measure.sh [-n ROUNDS] [-o OUT.csv] -- COMMAND ...            one command, ROUNDS times (default 1)
#   measure.sh [-n ROUNDS] [-o OUT.csv] -a "CMD A" -b "CMD B"     alternate A1 B1 A2 B2 ... (fair on a shared machine)
#
# Prints one line per run and a summary per variant; with -o, appends CSV rows:
#   variant,round,exit,wall_s,user_s,sys_s,cpu_s,load1,started_at
# Notes: CPU of daemons the command did not wait for (a Docker VM, a browser left running) is not counted.
#        Compare CPU, not wall, when the load average moves between runs.
set -u
ROUNDS=1; OUT=""; A=""; B=""
while getopts "n:o:a:b:" opt; do case $opt in n) ROUNDS=$OPTARG;; o) OUT=$OPTARG;; a) A=$OPTARG;; b) B=$OPTARG;; *) exit 2;; esac; done
shift $((OPTIND-1)); [ "${1:-}" = "--" ] && shift
if [ -z "$A" ]; then [ $# -gt 0 ] || { echo "usage: measure.sh [-n N] [-o out.csv] -- command ...   or   -a CMD -b CMD" >&2; exit 2; }; A=$(printf '%q ' "$@"); fi
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
[ -n "$OUT" ] && [ ! -s "$OUT" ] && echo "variant,round,exit,wall_s,user_s,sys_s,cpu_s,load1,started_at" > "$OUT"
load1() { uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/'; }
one() {  # variant round command
  local v=$1 r=$2 c=$3 l s e
  l=$(load1); s=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  /usr/bin/time -p -o "$TMP/t" bash -c "$c" > "$TMP/$v$r.log" 2>&1; e=$?
  read -r wall user sys < <(awk '/^real/{r=$2}/^user/{u=$2}/^sys/{s=$2}END{print r,u,s}' "$TMP/t")
  cpu=$(awk -v u="$user" -v s="$sys" 'BEGIN{printf "%.2f", u+s}')
  printf '%s%s exit=%s wall=%ss cpu=%ss (user %s sys %s) load=%s\n' "$v" "$r" "$e" "$wall" "$cpu" "$user" "$sys" "$l"
  [ "$e" = 0 ] || { echo "  last lines of output:"; tail -5 "$TMP/$v$r.log" | sed 's/^/  /'; }
  [ -n "$OUT" ] && echo "$v,$r,$e,$wall,$user,$sys,$cpu,$l,$s" >> "$OUT"
  echo "$v $wall $cpu" >> "$TMP/all"
}
for r in $(seq 1 "$ROUNDS"); do one A "$r" "$A"; [ -n "$B" ] && one B "$r" "$B"; done
awk '{n[$1]++; w[$1]+=$2; c[$1]+=$3} END{for(v in n) printf "%s: %d run(s), mean wall %.1fs, mean cpu %.1fs\n", v, n[v], w[v]/n[v], c[v]/n[v]}' "$TMP/all" | sort
