#!/usr/bin/env python3
"""Build a fake ~/.claude/projects tree for the checks.

Every record here exists to prove one line of COLLECT.md. The dangerous ones —
the thinking block, the tool output, the password — carry canary strings, so a
check can simply look for the canary in the output and go red if it is there.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

CANARIES = {
    "thinking": "CANARY_THINKING_BLOCK",
    "tool_use": "CANARY_TOOL_USE",
    "tool_result": "CANARY_TOOL_RESULT",
    "tool_use_result": "CANARY_TOOLUSERESULT",
    "sidechain": "CANARY_SIDECHAIN",
    "meta": "CANARY_META",
    "command": "CANARY_SLASH_COMMAND",
    "old": "CANARY_OUT_OF_WINDOW",
    "secret": "CANARY_SECRET_EXCHANGE",
    "untyped": "CANARY_UNTYPED",
}

now = datetime.now(timezone.utc)


def stamp(minutes_ago):
    return (now - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")


def base(kind, minutes_ago, cwd, **extra):
    record = {
        "type": kind,
        "uuid": "uuid-%s-%s" % (kind, minutes_ago),
        "parentUuid": None,
        "isSidechain": False,
        "timestamp": stamp(minutes_ago),
        "userType": "external",
        "entrypoint": "cli",
        "cwd": cwd,
        "sessionId": "11111111-2222-3333-4444-555555555555",
        "version": "2.1.231",
        "gitBranch": "main",
    }
    record.update(extra)
    return record


def typed(minutes_ago, cwd, text, **extra):
    return base("user", minutes_ago, cwd, promptSource="typed",
                message={"role": "user", "content": text}, **extra)


def answer(minutes_ago, cwd, blocks, **extra):
    return base("assistant", minutes_ago, cwd,
                message={"role": "assistant", "content": blocks}, **extra)


def build(root):
    home = os.path.expanduser("~")
    one = "%s/projects/kitchen-timer" % home
    two = "%s/projects/second-thing" % home

    # --- project one, inside the window ------------------------------------
    first = [
        typed(90, one, "make me a kitchen timer that shouts when the pasta is done"),
        answer(89, one, [
            {"type": "thinking", "thinking": "the user wants %s" % CANARIES["thinking"]},
            {"type": "text", "text": "Right — a timer it is. Starting with the countdown."},
        ]),
        answer(89, one, [
            {"type": "tool_use", "id": "toolu_1", "name": "Bash",
             "input": {"command": "cat /etc/passwd # %s" % CANARIES["tool_use"]}},
        ]),
        base("user", 88, one, message={"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1",
             "content": "root:x:0:0 %s" % CANARIES["tool_result"]}]},
             toolUseResult={"stdout": CANARIES["tool_use_result"]}),
        answer(88, one, [{"type": "text", "text": "Done. The countdown ticks and it beeps."}]),

        # Personal detail that has to be scrubbed out of a kept exchange.
        typed(80, one,
              "it broke — I ran it from %s/projects/kitchen-timer and the box at "
              "192.168.1.44 could not reach it. mail me at jane.doe@example.com" % home),
        answer(79, one, [{"type": "text",
                          "text": "That path is %s/projects/kitchen-timer on your disk." % home}]),

        # Whole exchange has to go: it names a password.
        typed(70, one, "the deploy asks for a password, it is hunter2 %s" % CANARIES["secret"]),
        answer(69, one, [{"type": "text", "text": "Noted, %s" % CANARIES["secret"]}]),

        # Kept, but flagged: talks about tokens without carrying one.
        typed(60, one, "why does it say the token limit was exceeded?"),
        answer(59, one, [{"type": "text", "text": "That is the model's context window, not a key."}]),

        # None of these are a typed prompt.
        base("user", 55, one, isMeta=True, promptSource="typed",
             message={"role": "user", "content": "<local-command-caveat>%s" % CANARIES["meta"]}),
        base("user", 54, one, promptSource="typed",
             message={"role": "user", "content": "<command-name>/clear</command-name> %s"
                      % CANARIES["command"]}),
        base("user", 53, one, message={"role": "user", "content": CANARIES["untyped"]}),
        base("user", 52, one, isSidechain=True, promptSource="typed",
             message={"role": "user", "content": CANARIES["sidechain"]}),
        answer(51, one, [{"type": "text", "text": CANARIES["sidechain"]}], isSidechain=True),
    ]

    # --- the same file, but from before the window opened -------------------
    # The file's own mtime is fresh; only the record timestamps say otherwise.
    stale = [
        typed(600, one, "yesterday's work %s" % CANARIES["old"]),
        answer(599, one, [{"type": "text", "text": CANARIES["old"]}]),
    ]

    # --- project two --------------------------------------------------------
    second = [
        typed(45, two, "now the other one: a script that renames my photos"),
        answer(44, two, [{"type": "text", "text": "Renaming by date taken. Here is the loop."}]),
    ]

    write(root, "-home-someone-projects-kitchen-timer", "session-one.jsonl", stale + first)
    write(root, "-home-someone-projects-second-thing", "session-two.jsonl", second)


def write(root, folder, name, records):
    directory = os.path.join(root, folder)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    build(sys.argv[1])
    print(json.dumps(CANARIES, indent=2))
