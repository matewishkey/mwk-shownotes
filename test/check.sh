#!/usr/bin/env bash
# Checks the rules that are the product. Seconds, no Docker, no login.
#
# If you find yourself relaxing a check to make it pass, the bug is in the thing
# being checked. A check you cannot make go red is decoration.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

pass=0; fail=0
ok()   { printf '  \033[32mok\033[0m   %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# --- The files that ship -----------------------------------------------------
head_ "Files"
for f in README.md CLAUDE.md COLLECT.md prompts/notes.md; do
  [ -f "$f" ] && ok "$f exists" || bad "$f is missing"
done

# --- The paste has to survive a terminal -------------------------------------
head_ "The pasted prompt"
# It goes into a terminal window belonging to somebody who cannot tell a display
# artefact from something they broke. 60 columns, same rule as the kit's.
fence=$(awk '/^```/{n++; next} n==1' prompts/notes.md)
if [ -z "$fence" ]; then
  bad "prompts/notes.md has no fenced prompt"
else
  long=$(printf '%s\n' "$fence" | awk 'length > 60 {print NR": "length}')
  if [ -n "$long" ]; then
    bad "prompt has lines over 60 columns: $(printf '%s' "$long" | tr '\n' ' ')"
  else
    ok "prompt fits 60 columns ($(printf '%s\n' "$fence" | wc -l | tr -d ' ') lines)"
  fi
  printf '%s' "$fence" | grep -q 'COLLECT.md' \
    && ok "prompt points at COLLECT.md" \
    || bad "prompt does not name COLLECT.md — the agent has nothing to read"
fi

# --- The load-bearing rules --------------------------------------------------
head_ "The rules in COLLECT.md"
need() {  # need <description> <grep-pattern>
  grep -qiE -- "$2" COLLECT.md && ok "$1" || bad "$1 — missing from COLLECT.md"
}
need "six-hour window"                 'six hours'
need "never widens the window"         'never wider|cannot ask for more'
need "stops on an empty window"        'stop and tell them'
need "show-only gate"                  'not a log viewer|not a debugging tool'
need "keeps typed prompts only"        'promptSource'
need "excludes tool output"            'toolUseResult'
need "excludes thinking blocks"        'thinking'
need "drops the whole exchange"        'drop the whole exchange'
need "reports what it dropped"         'how many exchanges you dropped'
need "one file per project"            'one file per project|per project, kept apart'
need "waits for a yes"                 'wait for a yes'
need "names the destination address"   'mate@matewishkey\.com'
need "portable six-hour filter"        '\-mmin \-360'
need "reads cwd, not the folder name"  'cwd. field inside'

# --- Two commands that would ship broken -------------------------------------
head_ "Commands that must not come back"
# Both were caught before the first commit. Both look right, which is the problem.
#
# Grepping the whole file cannot tell a command being USED from one being warned
# against — COLLECT.md names all three in prose precisely to forbid them, so a
# naive grep goes red on the sentence telling you not to do it. Commands live in
# fences; warnings live in prose. Check the fences.
fences=$(awk '/^```/{f=!f; next} f' COLLECT.md)
[ -n "$fences" ] || bad "no fenced commands in COLLECT.md at all"

banned() {  # banned <description> <pattern> <why>
  if printf '%s\n' "$fences" | grep -qE -- "$2"; then
    bad "COLLECT.md runs $1 — $3"
  else
    ok "no $1 ($3)"
  fi
}
banned "gh gist create --secret" '--secret'    "that flag does not exist; gists are unlisted by default"
banned "date -d"                 'date +-d'    "measured broken on macOS, where this runs"
banned "jq"                      '(^|[^a-z])jq ' "not on a stock Mac; python3 is"

# --- Every URL handed to a stranger ------------------------------------------
head_ "URLs"
# Private by design; an anonymous fetch 404s and that is correct, not broken.
skip_url='mwk-replayer'
urls=$(grep -ohE 'https?://[a-zA-Z0-9./_%#?=&+-]*[a-zA-Z0-9/]' \
         README.md CLAUDE.md COLLECT.md prompts/notes.md | sort -u)
n=0
for u in $urls; do
  if printf '%s' "$u" | grep -qE -- "$skip_url"; then
    printf '  \033[90mskip\033[0m %s (private)\n' "$u"; continue
  fi
  n=$((n+1))
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$u")
  case "$code" in
    200) ok "$u" ;;
    30*) bad "$u redirects ($code) — a redirect holds until somebody claims the old path" ;;
    *)   bad "$u returned $code" ;;
  esac
done
[ "$n" -ge 3 ] && ok "checked $n URLs" || bad "only $n URLs found — the extraction is broken"

# --- Result ------------------------------------------------------------------
printf '\n\033[1m%d passed, %d failed\033[0m\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
