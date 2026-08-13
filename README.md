# mwk-shownotes

Turns the conversation from a [Mate Wish Key](https://matewishkey.com) show into notes people can
follow at home — written on the guest's own machine, reviewed by them, sent only if they say yes.

**One paste, off camera, after the recording stops.** Nothing to install and nothing left behind.

## How it goes

1. Mate hands the guest the prompt in [`prompts/notes.md`](prompts/notes.md).
2. Their agent reads [`COLLECT.md`](COLLECT.md) and works through it.
3. It downloads [`collect.py`](collect.py) from this repo and runs it with `python3`.
4. That reads the last **six hours** of conversations on that machine and nothing older.
5. It keeps what they typed and what the agent answered — **not** the commands, the file contents or
   the tool output.
6. It drops any exchange that touches a password, a key or a token, and says how many it dropped.
7. It writes one file per project, kept separate, with the time on every exchange. The agent reads
   the lot, drops anything else that should not travel, and shows them.
8. They can drop a project by name, or say no.
9. On a yes it becomes an unlisted gist **on their own GitHub account**, and they send Mate the link.

## The times

Every exchange carries the local clock time, the UTC offset and a `T+` counted from the moment the
recording started — so the notes line up against the video. The transcripts themselves are stamped
in UTC, so **the machine's timezone is recorded with them**; without it the two clocks are a
guess.

Alongside the markdown there is a `show.json` with the same exchanges, the same drops and the same
timings, for anything that wants to replay the show rather than read it.

## What this is not

**Not a debugging tool and not a log exporter.** It exports a person's conversations off their
machine, and the only reason that is reasonable is that they just chose to be on a show about it.
`COLLECT.md` opens by checking exactly that, and stops if the answer is no.

**`collect.py` is a net, not the review.** It catches the shapes — passwords, keys, tokens, home
paths, email addresses, IP addresses. It cannot tell that "ask Sarah about the invoice" names
somebody. Reading every exchange is still a job for the person and their agent, and `COLLECT.md`
says so at the point where it matters.

For a record of what somebody has learnt, `/mwk-genie:learning` does that on their own machine and
sends it nowhere.

## Why it is not part of the kit

[`mwk-genie`](https://github.com/matewishkey/mwk-genie) is installed by people who will never be on
a show. A command that packages up their prompt history and mails it to Mate does not belong in the
list on the page they keep, however many times it asks permission first.

## Why this repo is public

So the guest can read what they are agreeing to before they run it. Everything here is instructions.
None of their data comes near it — the notes live in a gist on their account, and the copy on their
disk is theirs.

## For Mate

The bundle is curated markdown, not raw JSONL, so it does not drop straight into `mwk-replayer`
yet — but `show.json` is the shape to import: exchanges, ids, UTC and local stamps, and seconds
elapsed from the start of the recording.

`scan.py` in that repo is still the net before anything goes public — it cannot run on a guest's
machine, so the review in step 4 is a person-and-agent job, not a scanned one. Do not assume the
incoming gist has been through a scanner.

## Testing

```
bash test/check.sh
```
