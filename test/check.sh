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
for f in README.md CLAUDE.md COLLECT.md prompts/notes.md collect.py; do
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

# --- The collector, against a fake machine -----------------------------------
head_ "The collector"
# test/fixture.py builds a ~/.claude/projects tree where everything that must not
# travel carries a canary string. So "did the thinking block leak" is a grep, not
# a judgement — and a check you cannot make go red is decoration.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# Brisbane has no daylight saving, so the offset is +10:00 every day of the year.
TZ=Australia/Brisbane; export TZ

python3 -c 'import ast,sys; ast.parse(open("collect.py").read())' 2>/dev/null \
  && ok "collect.py parses" || bad "collect.py does not parse"
python3 collect.py --help >/dev/null 2>&1 \
  && ok "--help works" || bad "--help does not work"

python3 test/fixture.py "$tmp/projects" >"$tmp/canaries.json" 2>"$tmp/fixture.err" \
  && ok "fixture built" || bad "fixture failed: $(cat "$tmp/fixture.err")"

if python3 collect.py --projects-dir "$tmp/projects" --out "$tmp/out" \
     --show-start 09:00 >"$tmp/report.txt" 2>&1; then
  ok "collects from the fixture"
else
  bad "collector failed: $(tail -2 "$tmp/report.txt" | tr '\n' ' ')"
fi

# The whole product, in one grep: none of it may reach the bundle.
leaked=$(grep -roh 'CANARY_[A-Z_]*' "$tmp/out" 2>/dev/null | sort -u | tr '\n' ' ')
if [ -n "$leaked" ]; then
  bad "the bundle leaked: $leaked"
else
  ok "no thinking, tool output, sidechain, slash command or out-of-window record"
fi

grep -q 'jane.doe@example.com\|192\.168\.1\.44' -r "$tmp/out" 2>/dev/null \
  && bad "an email address or IP survived into the bundle" \
  || ok "email addresses and IPs taken out"
grep -q "$HOME" -r "$tmp/out" 2>/dev/null \
  && bad "the home folder path survived — it carries their name" \
  || ok "home folder replaced with ~"

# show.json travels in the gist too, so it gets the same words the person read.
python3 - "$tmp/out" <<'PY' && ok "show.json matches the markdown it was shown with" \
                            || bad "show.json disagrees with the markdown"
import json, os, sys
out = sys.argv[1]
data = json.load(open(os.path.join(out, "show.json")))
for project in data["projects"]:
    body = open(os.path.join(out, project["file"]), encoding="utf-8").read()
    for exchange in project["exchanges"]:
        if exchange["prompt"].splitlines()[0] not in body:
            sys.exit(1)
        if exchange["id"] not in body:
            sys.exit(1)
sys.exit(0)
PY

# Timestamps and the timezone: without them nothing lines up with the video.
grep -qE '· T[+-][0-9]{2}:[0-9]{2}:[0-9]{2} ·' "$tmp/out"/0[1-9]-*.md 2>/dev/null \
  && ok "exchanges carry a T+ from the start of the recording" \
  || bad "no T+ times — the notes cannot be synced to the recording"
grep -qE '^### [0-9]{2}:[0-9]{2}:[0-9]{2} \+10:00 ·' "$tmp/out"/0[1-9]-*.md 2>/dev/null \
  && ok "exchanges carry local clock time and offset" \
  || bad "exchanges have no local clock time — nothing to sync against"
grep -q 'Australia/Brisbane' "$tmp/out/00-summary.md" \
  && ok "timezone named in the summary" || bad "summary does not name the timezone"
grep -q '+10:00' "$tmp/out/00-summary.md" \
  && ok "UTC offset in the summary" || bad "summary has no UTC offset"
python3 - "$tmp/out" <<'PY' && ok "show.json carries timezone, offset and both clocks" \
                            || bad "show.json is missing timing detail"
import json, os, sys
from datetime import datetime
data = json.load(open(os.path.join(sys.argv[1], "show.json")))
tz = data.get("timezone", {})
if not tz.get("utc_offset") or tz.get("utc_offset_seconds") is None:
    sys.exit(1)
if not data.get("show_start"):
    sys.exit(1)
exchange = data["projects"][0]["exchanges"][0]
if not all(k in exchange for k in ("utc", "local", "elapsed_seconds")):
    sys.exit(1)
# T+ is measured from the recording, and the two clocks are the same instant.
start = datetime.fromisoformat(data["show_start"])
when = datetime.fromisoformat(exchange["utc"].replace("Z", "+00:00"))
if int((when - start).total_seconds()) != exchange["elapsed_seconds"]:
    sys.exit(1)
sys.exit(0 if datetime.fromisoformat(exchange["local"]) == when else 1)
PY

# An AI show says "token limit" all day. A net that eats those returns nothing.
grep -q 'token limit' -r "$tmp/out" 2>/dev/null \
  && ok "talking about tokens is not treated as carrying one" \
  || bad "the secret net ate an ordinary sentence about tokens"
grep -q 'a password or passphrase' "$tmp/report.txt" \
  && ok "the password exchange was dropped, and said so" \
  || bad "the password exchange was not reported as dropped"
grep -qi 'left out' "$tmp/out/00-summary.md" \
  && ok "the summary reports what was left out" \
  || bad "the summary hides what was left out"

# The window. Wider is the one thing it must never do.
python3 collect.py --minutes 500 --projects-dir "$tmp/projects" --out "$tmp/wide" \
  >/dev/null 2>&1
[ $? -ne 0 ] && [ ! -d "$tmp/wide" ] \
  && ok "refuses a window wider than six hours" \
  || bad "it widened the window past six hours"
python3 collect.py --minutes 120 --projects-dir "$tmp/projects" --out "$tmp/narrow" \
  >/dev/null 2>&1 \
  && ok "narrower on request is fine" || bad "it will not narrow the window"
mkdir -p "$tmp/nothing"
python3 collect.py --projects-dir "$tmp/nothing" --out "$tmp/none" >/dev/null 2>&1
[ $? -ne 0 ] \
  && ok "stops on an empty window instead of reaching further back" \
  || bad "an empty window did not stop it"

# Consent has to survive a second run: dropping means gone, not renumbered.
python3 - "$tmp/out" <<'PY' >"$tmp/id.txt"
import json, os, sys
data = json.load(open(os.path.join(sys.argv[1], "show.json")))
print(data["projects"][0]["exchanges"][0]["id"])
PY
dropped_id=$(cat "$tmp/id.txt")
python3 collect.py --projects-dir "$tmp/projects" --out "$tmp/out" \
  --drop "$dropped_id" --drop-project second-thing >/dev/null 2>&1
if grep -rq "$dropped_id" "$tmp/out" 2>/dev/null; then
  bad "a dropped exchange came back on the next run"
else
  ok "--drop takes the exchange out of the markdown and the json"
fi
ls "$tmp/out" | grep -q 'second-thing' \
  && bad "a dropped project left its file behind for gh gist to pick up" \
  || ok "--drop-project leaves no file behind"

# The agent writes the intro, then a drop forces a re-run. Losing it every time
# is how you end up with a bundle nobody bothered to introduce.
python3 - "$tmp/out" <<'PY'
import glob, os, sys
path = sorted(glob.glob(os.path.join(sys.argv[1], "0[1-9]-*.md")))[0]
body = open(path, encoding="utf-8").read()
head, rest = body.split("<!-- intro:start -->", 1)
_, tail = rest.split("<!-- intro:end -->", 1)
open(path, "w", encoding="utf-8").write(
    head + "<!-- intro:start -->\nTHE_AGENTS_OWN_WORDS\n<!-- intro:end -->" + tail)
PY
python3 collect.py --projects-dir "$tmp/projects" --out "$tmp/out" >/dev/null 2>&1
grep -rq 'THE_AGENTS_OWN_WORDS' "$tmp/out/00-summary.md" \
  && ok "an intro written by the agent survives a re-run, and reaches the summary" \
  || bad "re-running threw away the intro the agent wrote"

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
