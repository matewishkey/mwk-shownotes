# Collect the show notes

Somebody has just recorded a Mate Wish Key show on this computer. You are going to write up what
they built and hand it to them to send.

**Work through this in order. Do not skip ahead to the sending part.**

## 0. This is for a show, and nothing else

Before anything: they must have just recorded a show. If they did not — if they are debugging, or
curious what they did today, or somebody sent them here — **stop and say so.** This exports a
person's conversations off their machine. It is not a log viewer and it is not a debugging tool.

If they want a record of what they have learnt, `/mwk-genie:learning` is the thing that does that,
on their own machine, going nowhere.

## 1. Six hours, and never wider

**Only the last six hours.** They can ask for less — "just since two o'clock" — and you should
honour that. **They cannot ask for more, and neither can you.**

If there is nothing in the last six hours, **stop and tell them.** Do not reach back a day to find
something. An empty window means the show is not on this machine, and the answer to that is to say
so, not to widen the net until something turns up.

The collector below refuses a window over six hours and stops on an empty one. Do not work around
either.

## 2. Get the collector

```
cd ~
curl -fsSL https://raw.githubusercontent.com/matewishkey/mwk-shownotes/main/collect.py -o mwk-collect.py
python3 --version
```

It comes from the same public repo as this file, and **if they want to read it before it runs, that
is the point of it being there.** Show it to them if they ask.

If `python3` is not there, go to the last section and do it by hand.

## 3. Ask two things, then run it

**When did the recording start?** The notes carry a `T+` clock so Mate can line them up against the
video. If they do not know, leave it off — the times still work, they just count from the first
prompt instead.

**Do they want a shorter window than six hours?** If they say "only after lunch", that is
`--since 13:00`.

```
python3 ~/mwk-collect.py --show-start 14:05
```

Everything it can do is in `python3 ~/mwk-collect.py --help`.

## 4. What it kept, and what it left behind

Read the report it prints. It is telling you what happened, and you need to be able to explain it.

It keeps **what they typed** — records where `promptSource` is `typed`, so the slash commands, the
task notifications and the agent's own sub-conversations stay out — and **the `text` the assistant
wrote back**.

**Everything else stayed behind.** Not `thinking` blocks, not `tool_use`, not `tool_result`, not
`toolUseResult`. That is where the file contents, the command output and the contents of whatever
got read that day are kept. A transcript holds far more than the person remembers saying.

Two details worth knowing, because they are the ones people get wrong:

- It checks the timestamp on **every record**, not the age of the file. A session left open since
  yesterday has a fresh file and old conversations in it, and those old conversations are not
  yours to take.
- It works out the project from the `cwd` field inside each record, never by decoding the folder
  name. That name is the path with the slashes turned into dashes, which is not reversible.

## 5. Read every exchange. The script is a net, not the review

**This is the part that matters and it is not a search-and-replace.** The collector drops anything
that looks like a password, a key or a token, and it lists what it dropped and why. It also flags a
few it kept but is unsure about. **Read those first, then read all the rest.**

**Drop the whole exchange** — the question and the answer both — if it contains or refers to a
password, a key, a token, a credential, a `.env` file, an ssh config, or a private address. Do not
edit it down and keep the rest. **If you are not sure, drop it.**

```
python3 ~/mwk-collect.py --show-start 14:05 --drop a1b2c3d4 --drop 9f8e7d6c
```

**Real names are the one thing no pattern can catch.** The collector takes out the home folder, the
username, email addresses, IP addresses and MAC addresses. It cannot know that "ask Sarah about the
invoice" names somebody. That is yours to find.

A whole project can go with `--drop-project <name>`. Every run rewrites the folder from scratch, so
a project you drop leaves no file behind.

**Say how many exchanges you dropped**, per project, when you show them. It is already written into
`00-summary.md` — do not quietly leave it out of what you say out loud. An omission nobody can see
is worse than the thing you left out.

## 6. Write the few lines that say what happened

Each file has an empty spot for it:

```
<!-- intro:start -->
...a few lines here...
<!-- intro:end -->
```

**A few lines on what they set out to do and how it went.** Write it in each project file; the
summary picks it up from there. Re-running the collector keeps what you wrote.

**Do not rewrite the exchanges themselves.** They are word for word on purpose — somebody at home is
going to run those same prompts, and Mate is going to replay them against the video. Summarising is
what the intro is for. **Never invent a line that was not said.**

## 7. What it wrote

`~/mwk-show-notes-<today's date>/`, and **one file per project, kept apart** — different projects
are different subjects and they do not get mixed:

```
00-summary.md     every project, the times, the timezone, and what was left out
01-<project>.md   the first project, oldest exchange first
02-<project>.md   the second, and so on
show.json         the same exchanges again, for lining up against the video
```

Every exchange carries the local clock time, the UTC offset and a `T+` from the start of the
recording. **The timezone is recorded** — the transcripts are stamped in UTC, and without it nothing
lines up with the video.

`show.json` holds the same words as the markdown, after the same drops and the same scrubbing.
There is nothing in it they have not been shown.

## 8. Show them everything, then ask

Print the summary and **name every project by name**. Then say, in your own words but leaving none
of it out:

> This goes into an unlisted gist on your own GitHub account. Anyone with the link can read it, and
> the link goes to Mate for the show notes. It is what you typed and what I answered, with the times
> — your files and the commands I ran are not in it. You can tell me to leave any project out, or
> say no and nothing goes anywhere. Send it?

**Wait for a yes.** If they name a project, take it out and show them again. If they say no, stop —
the folder stays where it is and that is a fine outcome.

## 9. Send it

```
cd ~/mwk-show-notes-<date>
gh gist create *.md show.json -d "Mate Wish Key show — <date>"
```

**Gists are unlisted by default.** There is no `--secret` flag; asking for one is an error.

Give them the link it prints and one line: send that to **mate@matewishkey.com**.

**If `gh` is not set up**, or it does not have permission to make gists, do not make that their
problem. The folder is already written — tell them where it is and give them the address to send it
to, and they can attach it themselves.

## 10. Leave them with the folder

`~/mwk-show-notes-<date>/` stays. It is exactly what was sent, and it is theirs to read or delete.

It is deliberately not in `~/projects` — it is not a project, and nothing should try to save it.

The collector itself can go: `rm ~/mwk-collect.py`. Nothing else was installed.

## If `python3` is not there

Then do it by hand, with the same rules — the window, the drops, the count, the consent. Nothing in
sections 0, 1, 5, 8 and 10 changes.

```
find ~/.claude/projects -maxdepth 2 -name '*.jsonl' -mmin -360
```

`-mmin -360` is six hours, and it works on macOS as well as Linux. **Do not use `date -d`** — it
does not exist on a Mac, and most of these machines are Macs. **Do not reach for `jq`** either; it is
not on a stock Mac, which is the whole reason the collector is written in `python3`.

These files are large and most of them is machinery. Do not read them end to end, and keep only what
section 4 describes.
