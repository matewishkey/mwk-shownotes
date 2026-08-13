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

## Two commands that would have shipped broken

- **`gh gist create` has no `--secret` flag.** Gists are unlisted by default and `--public` is the
  opt-out. The obvious-looking command errors in front of a guest.
- **The project folder name is not reversible.** `~/.claude/projects/<folder>` is the path with
  slashes turned to dashes, and it is lossy — read `cwd` out of the records instead.

## The rules that are the product

`COLLECT.md` is not a script, it is a review procedure, and these are the load-bearing lines.
`test/check.sh` pins each one:

- **Six hours, narrower on request, never wider.** If the window is empty it **stops**. This is
  deliberately the opposite of `/mwk-genie:learning`, which widens when today is empty. Do not let
  the two converge — widening here reaches into conversations nobody agreed to send.
- **Prompts and assistant `text` only.** Never `thinking`, `tool_use`, `tool_result`,
  `toolUseResult`. That is where file contents and command output live. `mwk-replayer`'s README is
  the evidence: one of its transcripts holds five real server IPs, because a single Bash call read
  `~/.ssh/config`.
- **Drop the whole exchange, do not redact and keep.** Mate's call: if it touches a password, it is
  not shared. Redacting leaves the shape of the thing and invites a judgement call per line.
- **Report the count of dropped exchanges.** An invisible omission is worse than the omission.
- **Projects stay apart.** Separate projects are separate subjects and separate consent.
- **Consent names every project and waits for a yes.** No is a fine outcome and the folder stays.

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
