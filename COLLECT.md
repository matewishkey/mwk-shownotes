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

## 2. Find the sessions

Claude Code writes every session to `~/.claude/projects/<folder>/<session-id>.jsonl`.

```
find ~/.claude/projects -maxdepth 2 -name '*.jsonl' -mmin -360
```

- `-mmin -360` is six hours, and it works on macOS as well as Linux. **Do not use `date -d`** — it
  does not exist on a Mac, and most of these machines are Macs.
- `-maxdepth 2` keeps the agent's own sub-conversations out of it.

**Work out which project each session belongs to by reading the `cwd` field inside the file**, not
by decoding the folder name. The folder name is the path with the slashes turned into dashes, which
is not reversible — two different projects can produce the same folder name.

**Use `python3` to read them, not `jq`.** `jq` is not on a stock Mac; `python3` arrives with the
developer tools this kit already installs. Check it is there before you rely on it.

## 3. Take the conversation and nothing else

From each file, keep two things:

- **What they typed.** Records where `type` is `user` **and** `promptSource` is `typed`. Skip
  anything with `isMeta` or `isSidechain` set, and skip content starting `<command-name>` or
  `<local-command-`.
- **What the agent answered.** Records where `type` is `assistant`, and only the `text` blocks
  inside `message.content`.

**Everything else stays behind.** Not `thinking` blocks, not `tool_use`, not `tool_result`, not
`toolUseResult`. That is where the file contents, the command output and the contents of whatever
got read that day are kept. A transcript holds far more than the person remembers saying.

These files are large and most of them is machinery. Do not read them end to end.

## 4. Read every exchange, and drop what should not travel

**This is the part that matters and it is not a search-and-replace.** Read what you kept, one
exchange at a time.

**Drop the whole exchange** — the question and the answer both — if it contains or refers to a
password, a key, a token, a credential, a `.env` file, an ssh config, or a private address. Do not
edit it down and keep the rest. **If you are not sure, drop it.**

Then, in what is left:

- **Replace their home folder path with `~`.** `/Users/their-name` carries their name.
- **Take out** real names, email addresses, IP addresses and hostnames.

**Say how many exchanges you dropped**, in the summary, per project. An omission nobody can see is
worse than the thing you left out.

## 5. Trim it to what actually mattered

They said it out loud, so keep **what they typed exactly as they typed it**. That is the useful
part — somebody at home is going to run those same words.

**Compress the answers.** Keep what the agent actually did or worked out. Drop the scrollback, the
file listings, the long code blocks — unless the code is the thing that was being built, in which
case it belongs.

**Never invent a line that was not said.** If a stretch is too tangled to summarise honestly, leave
the exchange out and count it with the rest.

## 6. One file per project, kept apart

Different projects are different subjects and they do not get mixed. Write them into
`~/mwk-show-notes-<today's date>/`:

```
00-summary.md     every project, a few lines each
01-<project>.md   the first project
02-<project>.md   the second, and so on
```

Numbered so they stay in order. Each project file opens with **a few lines** on what they set out to
do and how it went, then the trimmed conversation underneath, oldest first, with times.

`00-summary.md` is those same few lines for every project in one place, plus the dropped-exchange
count. That file is the thing Mate reads first.

## 7. Show them everything, then ask

Print the summary and **name every project by name**. Then say, in your own words but leaving none
of it out:

> This goes into an unlisted gist on your own GitHub account. Anyone with the link can read it, and
> the link goes to Mate for the show notes. Your files and the commands I ran are not in it. You can
> tell me to leave any project out, or say no and nothing goes anywhere. Send it?

**Wait for a yes.** If they name a project, take it out and show them again. If they say no, stop —
the folder stays where it is and that is a fine outcome.

## 8. Send it

```
gh gist create 00-summary.md 01-*.md -d "Mate Wish Key show — <date>"
```

**Gists are unlisted by default.** There is no `--secret` flag; asking for one is an error.

Give them the link it prints and one line: send that to **mate@matewishkey.com**.

**If `gh` is not set up**, or it does not have permission to make gists, do not make that their
problem. The folder is already written — tell them where it is and give them the address to send it
to, and they can attach it themselves.

## 9. Leave them with the folder

`~/mwk-show-notes-<date>/` stays. It is exactly what was sent, and it is theirs to read or delete.

It is deliberately not in `~/projects` — it is not a project, and nothing should try to save it.
