# mwk-shownotes — agent notes

Show notes out of a guest's own machine, after a Mate Wish Key recording. `README.md` is the front
door; this is the stuff that will bite you.

## Everything follows from where it runs

**The guest runs it, on their own box, off camera.** Three consequences, and every one of them
killed an approach that looked fine on paper:

- **It cannot email.** There are no AWS credentials on a stranger's machine. SES works from Mate's
  dev box and only from there. That is why the bundle travels as a gist and the guest sends the
  link — and why there is no zip: a gist holds text files, one per project, which is also exactly
  how a guest says "not that one".
- **It cannot come from a private repo.** They cannot read one. Public or pasted, no third option.
- **It cannot assume Mate's tooling.** See the portability table below.

## No plugin, and it is not in mwk-genie

**A plugin is three steps off camera** — install, restart, run — and leaves a mail-Mate-my-logs
command on somebody's machine forever, for a thing they do once. A paste is one step and leaves
nothing.

**It is not a sixth `/mwk-genie:` command** (Mate's call, 2026-08-13). That kit is installed by
people who will never be on a show, and its bookmark page is the one artefact they keep. A command
that packages their prompt history and sends it to us does not belong on it, however many consent
gates it has. Moving it in there later is a regression, not a convenience.

**The short-paste-points-at-a-long-file shape is `prompts/setup.md`'s**, from the kit. All the care
lives in a versioned file; the paste stays short enough not to wrap in a terminal.

## The kit offers the clone. It never installs it

Mate's call, 2026-08-13: *"Ask it if they will be on the show, so they probably have to download.
some other might use this library, i do not want to enforce it."*

So `mwk-genie`'s `SETUP.md` ends by cloning this repo to `~/projects/mwk-shownotes` — **only for
somebody who has already said they are coming on a show**, and skipped in silence for everybody
else. Most people who install that kit are not guests and never will be; a tool for collecting
somebody's conversations is not something you put in front of them on the off-chance.

That is the same shape as step 13's iTerm2 offer, and `SETUP.md`'s "three things are theirs to
decide" rule now says so explicitly, so nobody counts it as a fourth question.

**Both paths have to keep working.** `COLLECT.md` looks for `~/projects/mwk-shownotes/collect.py`
before it downloads anything, and `prompts/notes.md` reads the local `COLLECT.md` when it is there.
A guest who was set up for a show fetches nothing on the day; anybody else still gets it from a
single `curl`. Break either half and one of the two populations is stranded.

## Measured on a real Mac, so nobody re-derives them

Read off the fleet's macOS box on 2026-08-13 (`Darwin arm64`). The guest is almost certainly on a
Mac, and this box is a dev Linux box — **anything you write here that you tested only locally is a
guess.**

| Thing | Result | Consequence |
|---|---|---|
| `find -mmin -360` | works | this is the six-hour filter |
| `date -d "6 hours ago"` | **fails** | never use it; `COLLECT.md` says so out loud |
| `jq` | Homebrew only | not on a stock Mac — do not depend on it |
| `python3` | present, 3.14.6 | via the Xcode tools the kit installs — use this |
| `curl`, `zip` | `/usr/bin` | system, always there |

**The whole suite has been run on that box, not just read about**: 51/51 on macOS 26.5.2 arm64,
2026-08-13, the repo copied over and `bash test/check.sh` run in a temp dir. Do that again after any
change to `collect.py` — this is a Linux box and the guests are all on Macs, so a green run here is
half an answer.

## Two commands that would have shipped broken

- **`gh gist create` has no `--secret` flag.** Gists are unlisted by default and `--public` is the
  opt-out. The obvious-looking command errors in front of a guest.
- **The project folder name is not reversible.** `~/.claude/projects/<folder>` is the path with
  slashes turned to dashes, and it is lossy — read `cwd` out of the records instead.

## The split: `collect.py` is the net, `COLLECT.md` is the review

Mate's call, 2026-08-13, reversing the original "no script at all". The mechanical half — find the
sessions, keep the typed prompts and the assistant text, drop the credential shapes, stamp the
times — is `collect.py`. The judgement half stays prose, because it is judgement: **real names are
the thing no pattern catches**, and consent is a conversation.

Say that split out loud wherever it matters. An agent that thinks the script did the review will
skip the review.

**The script must stay readable by the guest**, because "the repo is public and they can read it
before they run it" is one of the things keeping this off the phishing pile. Stdlib only, no
network, no install.

## The rules that are the product

These are the load-bearing lines. `test/check.sh` pins each one, and `test/fixture.py` builds a
fake `~/.claude/projects` where everything that must not travel carries a `CANARY_` string — so
"did the thinking block leak" is a grep, not an opinion. **Mutation-tested: making `collect.py`
emit `thinking` blocks does turn that check red.**

- **Six hours, narrower on request, never wider.** If the window is empty it **stops**. This is
  deliberately the opposite of `/mwk-genie:learning`, which widens when today is empty. Do not let
  the two converge — widening here reaches into conversations nobody agreed to send.
- **Prompts and assistant `text` only.** Never `thinking`, `tool_use`, `tool_result`,
  `toolUseResult`. That is where file contents and command output live. `mwk-replayer`'s README is
  the evidence: one of its transcripts holds five real server IPs, because a single Bash call read
  `~/.ssh/config`.
- **Drop the whole exchange, do not redact and keep.** Mate's call: if it touches a password, it is
  not shared. Redacting leaves the shape of the thing and invites a judgement call per line.
- **The word is a flag; the word beside a value is a drop.** Mate's call, 2026-08-13, after a dry
  run on a real session: dropping on the bare word "password" took out **3 of 12 exchanges and not
  one of them held a secret** — the agent had been saying "password" while explaining this very
  tool. Any show where somebody explains what a thing does hits this. So `collect.py` drops on
  `password: hunter2`, `my password`, `password is hunter2` and every concrete key shape, and
  **flags** a bare mention for the agent to read. **The agent's own rule in `COLLECT.md` section 5
  did not loosen** — it still drops the whole exchange for anything that so much as refers to a
  credential. The net got a wider mesh; the review did not.
- **Report the count of dropped exchanges.** An invisible omission is worse than the omission.
- **Projects stay apart.** Separate projects are separate subjects and separate consent.
- **Consent names every project and waits for a yes.** No is a fine outcome and the folder stays.
- **Every output carries the time, and the timezone with it.** The records are stamped UTC with a
  `Z`; the show happened on a wall clock. Ship one without the other and nothing syncs to the video.

## Three things measured on the real records, 2026-08-13

Read off 1041 real session files on the dev box, not guessed:

- **`promptSource: 'typed'` is exactly right.** Out of the user records that carry text: 43 `typed`,
  13 slash-command scaffolding, 9 `isMeta` local-command caveats, 8 `system`/`sdk` task
  notifications. The one field separates the human from the machinery.
- **A fresh file is not a fresh conversation.** `-mmin -360` finds files; a session left open since
  yesterday has old records inside it. `collect.py` filters on **every record's** timestamp, which
  is narrower than the documented `find`, never wider.
- **`timestamp` is UTC with a `Z`.** Hence the timezone block in `show.json`. The IANA name comes
  from `TZ` or `/etc/localtime`. **Verified on the real Mac, 2026-08-13** — `local_timezone()` run
  unmodified there returns `Australia/Brisbane / AEST / +10:00`. The catch worth keeping: macOS
  resolves `/etc/localtime` through `/private/var/db/timezone/tz/<version>/zoneinfo/…`, **not**
  `/usr/share/zoneinfo`, so the split on `zoneinfo/` is load-bearing on that platform and must not
  be tightened to a fixed prefix.

## The bugs the guest would have paid for

Both found by testing, both silent, both about consent rather than crashes:

- **`show.json` shipped unscrubbed.** Scrubbing ran at markdown-render time, so the JSON in the same
  gist still carried the email address and the IP the markdown had replaced. Scrub once, in place,
  before anything is written — `scrub_exchanges()` — so the person reviews the exact words that
  travel.
- **A dropped project left its file behind.** Re-running after `--drop-project` wrote the new set
  but the stale `02-*.md` stayed on disk, and `gh gist create` globs the folder. They say "not that
  one" and it goes anyway. Every run now clears its own previous output first.

And the send command was wrong from the start: `gh gist create 00-summary.md 01-*.md` only ever
matched the **first** project. It is `*.md show.json` now.

## The pattern to be suspicious of

This asks a beginner to paste a prompt that makes their agent fetch instructions from a URL and
upload their conversation history somewhere. **That is phishing-shaped**, and the only things making
it legitimate are that Mate hands it over in person, the repo is public and readable before they run
it, and nothing leaves without a shown-and-approved summary.

**Every one of those is load-bearing.** A version of this that fetches from a shortener, or sends
without showing, or lives in a private repo they cannot inspect, is the real thing wearing our name.

## Cross-repo

- **[mergodon/mwk-replayer](https://github.com/mergodon/mwk-replayer)** — private, consumes the
  notes. It reads raw JSONL; this produces curated markdown, so an importer is still missing. Its
  `scan.py` cannot run guest-side. Never edit it from here — `gh issue create -R mergodon/mwk-replayer`.
- **[matewishkey/mwk-genie](https://github.com/matewishkey/mwk-genie)** — the kit the guest already
  has. `COLLECT.md` points at `/mwk-genie:learning` as the thing to use instead when this is the
  wrong tool. Same rule: file an issue, do not edit.
