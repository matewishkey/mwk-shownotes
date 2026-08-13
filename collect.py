#!/usr/bin/env python3
"""Collect the show notes from this machine's Claude Code transcripts.

Runs on the guest's own computer, after a Mate Wish Key recording. It does the
mechanical half of COLLECT.md: find the sessions in the window, keep the typed
prompts and the assistant's answers, throw everything else away, drop anything
that smells of a credential, and write one file per project with timestamps.

It does NOT decide whether the notes get sent. That is COLLECT.md sections 5, 8
and 9 — read it, ask, then send — and it stays a conversation with the person
whose machine this is.

Stock-Mac rules: python3 stdlib only, no jq, no `date -d`, no network.
"""

import argparse
import getpass
import hashlib
import json
import os
import re
import socket
import sys
from datetime import datetime, timedelta, timezone

# The window is six hours. It can be narrowed on request and never widened —
# widening reaches into conversations nobody agreed to send.
MAX_MINUTES = 360

# ---------------------------------------------------------------------------
# What makes an exchange too dangerous to travel
#
# DROP takes the whole exchange out, question and answer both. FLAG keeps it and
# tells the agent to look at it first. The split exists because a show about
# building software says "token" and "API key" constantly, and a net that eats
# every one of those returns an empty bundle. The words alone are a flag; a word
# next to a value is a drop.
#
# This is a net, not the review. COLLECT.md section 5 is the review.
# Letter boundaries, not `\b`. `\bapi[ _-]?key` never matches inside
# GEMINI_API_KEY, because `_` is a word character and there is no boundary in
# front of API. Measured against 24 real keys on this fleet, 2026-08-13: with
# `\b`, 2 of 24 were caught when written as `NAME=value`; with these, 23 of 24.
_L = r"(?<![A-Za-z])"
_R = r"(?![A-Za-z])"
_CRED = (r"(?:api[ _-]?key|access[ _-]?key|secret[ _-]?key|auth[ _-]?token"
         r"|access[ _-]?token|api[ _-]?token|secret|token|password|passwd"
         r"|passphrase|credential)")

DROP_PATTERNS = [
    # The block itself, not the phrase. Saying "private key" out loud while
    # explaining a thing is not carrying one — same rule as password and token,
    # and it cost 2 real exchanges the day it was written.
    ("a private key block", r"BEGIN [A-Z ]*PRIVATE KEY|-----BEGIN|id_(?:rsa|ed25519)\s*[:=]"),
    ("a .env file", r"(?:^|[\s/\"'`])\.env\b"),
    ("an ssh config or key", r"\.ssh/|\bssh[ _-]?config\b|id_(?:rsa|ed25519)"),
    ("an auth header", r"\bbearer\s+[A-Za-z0-9._-]{8,}|authorization:\s*\S"),
    ("an AWS key", r"aws_(?:access|secret)_"),
    ("a one-time code", r"\b(?:2fa|otp|one[- ]time (?:code|password))\b"),
    ("a long hex string", r"\b[A-Fa-f0-9]{40,}\b"),

    # A key with a vendor's fingerprint on the front. `sk-`, `cfut_` and
    # `sntryu_` were read off real keys on this fleet; the rest are the
    # published prefixes. This is the high-precision tier — a string in this
    # shape is a key, there is no innocent reading.
    ("a vendor API key",
     r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{16,}|sk_live_[A-Za-z0-9]{16,}"
     r"|pk_live_[A-Za-z0-9]{16,}|rk_live_[A-Za-z0-9]{16,}|cfut_[A-Za-z0-9_-]{16,}"
     r"|sntryu_[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}"
     r"|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}"
     r"|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[A-Za-z0-9_-]{30,}|hf_[A-Za-z0-9]{20,}"
     r"|npm_[A-Za-z0-9]{30,}|glpat-[A-Za-z0-9_-]{16,}|shpat_[a-f0-9]{32}"
     r"|SG\.[A-Za-z0-9_-]{20,}|dop_v1_[a-f0-9]{32}|sbp_[a-f0-9]{40}"
     r"|AC[a-f0-9]{32}|SK[a-f0-9]{32})"),
    ("a JWT",
     r"(?<![A-Za-z0-9])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    # A webhook or a URL with the credential in the query string. The Discord
    # alert webhooks on this fleet are exactly this shape.
    ("a URL with a credential in it",
     r"https?://[^\s]*(?:/webhooks?/\d+/[A-Za-z0-9_-]{20,}"
     r"|[?&](?:api[_-]?key|key|token|access[_-]?token|auth|secret|password)"
     r"=[A-Za-z0-9_\-\.]{8,})"),

    # A credential-ish name assigned a long value: `GEMINI_API_KEY=...`,
    # `token: abc…`. This is the one that catches an env paste.
    ("a named secret with a value",
     _L + _CRED + r"s?" + _R + r"[A-Za-z0-9_\-]{0,20}\s*[:=]\s*[\"']?[A-Za-z0-9_\-\.\+/=]{16,}"),

    # The word beside a value in prose. Deliberately NOT the bare word: this
    # runs after a show about building software, where "the token limit" and
    # "it drops anything with a password in it" are ordinary sentences.
    # Measured on a real session, 2026-08-13: dropping on the bare word took out
    # 3 of 12 exchanges and not one held a secret — the agent had simply said
    # "password" while explaining this tool. Bare mentions are flagged instead.
    # "asks for a password, it is hunter2". Two guards, both measured: the gap
    # before "is" is at most 6 characters, and the value must contain a digit.
    # Without them this eats `client_credentials` grant, which is
    # server-to-server` — 8 hits in 2363 real texts, every one of them harmless
    # OAuth talk. The prose form for the key family was removed outright: it
    # cost "token is `iterm2`" and caught none of the 24 real keys that the
    # NAME=value rule above had not already caught.
    ("a password with a value",
     _L + r"(?:password|passwd|passphrase|credential)s?" + _R
     + r"[^\n]{0,6}\b(?:is|was)\s+[\"'`]?(?=\S*[0-9])\S{4,}"),
    ("a named secret",
     r"\b(?:my|your|his|her|their)\s+" + _CRED + r"s?" + _R),
]

FLAG_PATTERNS = [
    ("mentions a password or a credential", r"\b(?:pass(?:word|wd|phrase)|credential)s?\b"),
    ("mentions a private key", r"private key"),
    ("mentions a key, token or secret", _L + r"(?:api[ _-]?key|secret|token)s?" + _R),
    # Deliberately a flag and not a drop. Measured over 2359 real prompts and
    # answers: an opaque run of 32+ is a UUID, a migration filename or a
    # snapshot name far more often than it is a key. Dropping on it would eat
    # real content; showing it to the agent costs nothing.
    ("holds a long opaque string", r"\b(?![A-Za-z]+\b)[A-Za-z0-9_-]{24,}\b"),
    # Dotted keys break the run above into segments too short to notice. One
    # real key on this fleet is exactly that shape. Costs 0.42% of texts, all
    # of them SQL identifiers a reader dismisses at a glance.
    ("holds a dotted opaque string",
     r"(?<![A-Za-z0-9/_.-])(?=[A-Za-z0-9_.-]*[0-9])[A-Za-z0-9_-]{6,}"
     r"(?:\.[A-Za-z0-9_-]{6,})+(?![A-Za-z0-9])"),
]

# ---------------------------------------------------------------------------
# Personal detail that comes out of what is left


def scrubbers():
    """Ordered (name, compiled pattern, replacement). Home path goes first —
    it is the one that carries a real name most reliably."""
    out = []
    home = os.path.expanduser("~")
    if home and home not in ("/", ""):
        out.append(("home folder", re.compile(re.escape(home)), "~"))
    out.append(("home folder", re.compile(r"/(?:Users|home)/[^/\s\"'`:]+"), "~"))

    user = getpass.getuser()
    if user and len(user) >= 3:
        out.append(("username", re.compile(r"\b%s\b" % re.escape(user)), "<user>"))

    host = socket.gethostname()
    for name in {host, host.split(".")[0], host.replace(".local", "")}:
        if name and len(name) >= 3 and name != "localhost":
            out.append(("hostname", re.compile(r"\b%s\b" % re.escape(name)), "<host>"))

    out.append(("email address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<email>"))
    out.append(("MAC address",
                re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"))
    return out


# Loopback carries nothing about anybody; every other address is theirs.
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
HARMLESS_IPS = {"127.0.0.1", "0.0.0.0", "0.0.0.1", "255.255.255.255"}


def scrub(text, counts):
    for name, pattern, repl in SCRUBBERS:
        text, n = pattern.subn(repl, text)
        if n:
            counts[name] = counts.get(name, 0) + n

    def ip_sub(m):
        if m.group(0) in HARMLESS_IPS:
            return m.group(0)
        counts["IP address"] = counts.get("IP address", 0) + 1
        return "<ip>"

    return IPV4.sub(ip_sub, text)


SCRUBBERS = scrubbers()


# ---------------------------------------------------------------------------
# Time. Every record is stamped UTC with a Z; the show happened in local time.


def local_timezone():
    """Name, abbreviation and offset of this machine's timezone.

    The offset is what actually syncs the notes to the recording and it always
    comes out right. The IANA name is best effort: TZ if it is set, otherwise
    whatever /etc/localtime points at.

    Measured on macOS 26, 2026-08-13: /etc/localtime resolves through
    /private/var/db/timezone/tz/<version>/zoneinfo/Australia/Brisbane, not
    /usr/share/zoneinfo. Splitting on "zoneinfo/" is what makes it work on
    both platforms — do not tighten it to a fixed prefix.
    """
    now = datetime.now().astimezone()
    offset = now.utcoffset() or timedelta(0)
    total = int(offset.total_seconds())
    sign = "-" if total < 0 else "+"
    hh, mm = divmod(abs(total) // 60, 60)

    name = None
    env = os.environ.get("TZ", "").strip()
    if "/" in env:
        name = env
    elif os.path.exists("/etc/localtime"):
        real = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in real:
            name = real.split("zoneinfo/", 1)[1] or None

    return {
        "name": name,
        "abbreviation": now.tzname(),
        "utc_offset": "%s%02d:%02d" % (sign, hh, mm),
        "utc_offset_seconds": total,
    }


def parse_stamp(value):
    """'2026-08-13T02:46:34.322Z' -> aware datetime, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_clock(value, tzinfo, today):
    """'14:03' or '14:03:22' or a full ISO stamp -> aware datetime."""
    text = value.strip()
    try:
        stamp = datetime.fromisoformat(text)
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=tzinfo)
    except ValueError:
        pass
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            clock = datetime.strptime(text, fmt).time()
        except ValueError:
            continue
        return datetime.combine(today, clock, tzinfo=tzinfo)
    raise argparse.ArgumentTypeError(
        "%r is not a time — use HH:MM, HH:MM:SS or a full date and time" % value)


def count_of(number, word):
    return "%d %s" % (number, word if number == 1 else word + "s")


def elapsed(seconds):
    """T+ from the start of the recording. Negative when something was typed
    before the camera rolled, which happens and is worth seeing."""
    sign = "-" if seconds < 0 else "+"
    seconds = abs(int(seconds))
    return "T%s%02d:%02d:%02d" % (sign, seconds // 3600, seconds // 60 % 60, seconds % 60)


# ---------------------------------------------------------------------------
# Reading the transcripts


def session_files(projects_dir, since):
    """Every *.jsonl two levels down, touched since the window opened.

    Two levels is the same reason COLLECT.md gives for -maxdepth 2. The file
    time is a cheap first cut only — a session open for nine hours has a fresh
    file time and old records in it, so every record is checked again below.
    """
    found = []
    cutoff = since.timestamp()
    try:
        entries = sorted(os.scandir(projects_dir), key=lambda e: e.name)
    except FileNotFoundError:
        return found
    for entry in entries:
        if not entry.is_dir():
            continue
        for child in sorted(os.scandir(entry.path), key=lambda e: e.name):
            if not child.is_file() or not child.name.endswith(".jsonl"):
                continue
            try:
                if child.stat().st_mtime >= cutoff:
                    found.append(child.path)
            except OSError:
                continue
    return found


def prompt_text(record):
    """What they typed, or None if this record is not that.

    Typed prompts and nothing else: promptSource 'typed' leaves out the slash
    command scaffolding, the local-command caveats and the task notifications,
    all of which are the machine talking to itself.
    """
    if record.get("isMeta") or record.get("isSidechain"):
        return None
    if record.get("promptSource") != "typed":
        return None
    content = record.get("message", {}).get("content")
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content
                          if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text or text.startswith("<command-name>") or text.startswith("<local-command-"):
        return None
    return text


def answer_text(record):
    """The assistant's words. `text` blocks only — never `thinking`, never
    `tool_use`. That is where the file contents and the command output live."""
    if record.get("isSidechain"):
        return None
    content = record.get("message", {}).get("content")
    if not isinstance(content, list):
        return None
    parts = [b.get("text", "") for b in content
             if isinstance(b, dict) and b.get("type") == "text"]
    text = "\n".join(p for p in parts if p).strip()
    return text or None


def read_exchanges(paths, since, until):
    """One exchange = a typed prompt and the answers that followed it."""
    exchanges = []
    for path in paths:
        current = None
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                stamp = parse_stamp(record.get("timestamp"))
                if stamp is None or not since <= stamp <= until:
                    # Older than the window even though the file is fresh.
                    if record.get("type") == "user" and prompt_text(record):
                        current = None
                    continue

                kind = record.get("type")
                if kind == "user":
                    text = prompt_text(record)
                    if text is None:
                        continue
                    uid = record.get("uuid") or "%s:%s" % (path, stamp.isoformat())
                    current = {
                        "id": hashlib.sha1(uid.encode("utf-8")).hexdigest()[:8],
                        "when": stamp,
                        "cwd": record.get("cwd") or "",
                        "session": record.get("sessionId") or "",
                        "branch": record.get("gitBranch") or "",
                        "prompt": text,
                        "answers": [],
                    }
                    exchanges.append(current)
                elif kind == "assistant" and current is not None:
                    text = answer_text(record)
                    if text:
                        current["answers"].append(text)
    exchanges.sort(key=lambda e: e["when"])
    return exchanges


# ---------------------------------------------------------------------------
# Sorting the wheat


def matches(patterns, text):
    for reason, pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return reason
    return None


def sift(exchanges, dropped_ids):
    """Split into kept, dropped and flagged. Whole exchanges, never edited
    down — Mate's call: if it touches a password it is not shared, and
    redacting in place leaves the shape of the thing behind."""
    kept, dropped, flagged = [], [], []
    for exchange in exchanges:
        blob = "\n".join([exchange["prompt"]] + exchange["answers"])
        if exchange["id"] in dropped_ids:
            dropped.append((exchange, "you asked for it to go"))
            continue
        reason = matches(DROP_PATTERNS, blob)
        if reason:
            dropped.append((exchange, reason))
            continue
        kept.append(exchange)
        note = matches(FLAG_PATTERNS, blob)
        if note:
            flagged.append((exchange, note))
    return kept, dropped, flagged


def scrub_exchanges(exchanges, counts):
    """Scrub once, in place, before anything is written.

    Both the markdown and show.json are rendered from these same strings, so
    what the person reads in the review is exactly what travels. Scrubbing at
    render time instead is how the JSON ends up carrying an email address the
    markdown does not show.
    """
    for exchange in exchanges:
        exchange["prompt"] = scrub(exchange["prompt"], counts)
        exchange["answers"] = [scrub(answer, counts) for answer in exchange["answers"]]


def project_name(path):
    name = os.path.basename(path.rstrip("/")) or "unknown"
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"


def group_projects(kept, dropped, drop_projects):
    """Separate projects are separate subjects and separate consent."""
    order, by_path = [], {}
    for exchange in kept:
        path = exchange["cwd"] or "unknown"
        if path not in by_path:
            by_path[path] = {"path": path, "exchanges": [], "dropped": 0, "branch": ""}
            order.append(path)
        by_path[path]["exchanges"].append(exchange)
        if exchange["branch"]:
            by_path[path]["branch"] = exchange["branch"]
    for exchange, _ in dropped:
        path = exchange["cwd"] or "unknown"
        if path in by_path:
            by_path[path]["dropped"] += 1

    projects, used = [], {}
    for path in order:
        project = by_path[path]
        base = project_name(path)
        # Two projects can share a folder name. They are still two projects.
        used[base] = used.get(base, 0) + 1
        project["name"] = base if used[base] == 1 else "%s-%d" % (base, used[base])
        if project["name"] in drop_projects or base in drop_projects:
            continue
        projects.append(project)
    return projects


# ---------------------------------------------------------------------------
# Writing it out

INTRO_START = "<!-- intro:start -->"
INTRO_END = "<!-- intro:end -->"
INTRO_PLACEHOLDER = ("*A few lines here: what they set out to do, and how it went. "
                     "Written by the agent, after the drops are settled.*")


GENERATED = re.compile(r"^\d\d-.+\.md$")


def existing_intro(path):
    """The intro an agent wrote into a file from an earlier run."""
    try:
        with open(path, encoding="utf-8") as handle:
            body = handle.read()
    except OSError:
        return None
    if INTRO_START not in body or INTRO_END not in body:
        return None
    intro = body.split(INTRO_START, 1)[1].split(INTRO_END, 1)[0].strip()
    return intro if intro and intro != INTRO_PLACEHOLDER else None


def previous_intros(directory):
    """Keyed by project name, because dropping a project renumbers the files."""
    intros = {}
    for name in sorted(os.listdir(directory)):
        match = GENERATED.match(name)
        if not match:
            continue
        intro = existing_intro(os.path.join(directory, name))
        if intro:
            intros[name.split("-", 1)[1][:-3]] = intro
    return intros


def clear_previous(directory):
    """Take the last run's files away before writing this one's.

    Without this, dropping a project leaves its file behind and the next `gh
    gist create` picks it up — the person says "not that one" and it goes
    anyway. Only files this script names are touched; anything of theirs in
    the folder stays.
    """
    for name in sorted(os.listdir(directory)):
        if name == "show.json" or GENERATED.match(name):
            try:
                os.remove(os.path.join(directory, name))
            except OSError:
                pass


def render_exchange(exchange, tzinfo, origin):
    when = exchange["when"].astimezone(tzinfo)
    head = "### %s %s · %s · `%s`" % (
        when.strftime("%H:%M:%S"),
        when.strftime("%z")[:3] + ":" + when.strftime("%z")[3:],
        elapsed((exchange["when"] - origin).total_seconds()),
        exchange["id"],
    )
    lines = [head, "", "**They asked:**", ""]
    lines.extend("> " + line if line else ">"
                 for line in exchange["prompt"].splitlines())
    lines.append("")
    for answer in exchange["answers"]:
        lines.append("**The agent answered:**")
        lines.append("")
        lines.append(answer)
        lines.append("")
    return "\n".join(lines)


def write_project(directory, index, project, meta, tzinfo, origin):
    filename = "%02d-%s.md" % (index, project["name"])
    intro = project["intro"] or INTRO_PLACEHOLDER
    first = project["exchanges"][0]["when"].astimezone(tzinfo)
    last = project["exchanges"][-1]["when"].astimezone(tzinfo)

    lines = [
        "# %s" % project["name"],
        "",
        "%s to %s, %s (%s)" % (
            first.strftime("%Y-%m-%d %H:%M:%S"), last.strftime("%H:%M:%S"),
            meta["timezone"]["utc_offset"],
            meta["timezone"]["name"] or meta["timezone"]["abbreviation"]),
        "",
        "%s. %d left out." % (count_of(len(project["exchanges"]), "exchange"),
                              project["dropped"]),
        "",
        INTRO_START,
        intro,
        INTRO_END,
        "",
        "---",
        "",
    ]
    for exchange in project["exchanges"]:
        lines.append(render_exchange(exchange, tzinfo, origin))
        lines.append("---")
        lines.append("")
    with open(os.path.join(directory, filename), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    return filename


def write_summary(directory, projects, meta, dropped, tzinfo):
    window = meta["window"]
    start = datetime.fromisoformat(window["start_utc"]).astimezone(tzinfo)
    end = datetime.fromisoformat(window["end_utc"]).astimezone(tzinfo)
    tz = meta["timezone"]

    lines = [
        "# Mate Wish Key — show notes, %s" % meta["date"],
        "",
        "Written on the guest's machine from the last %d minutes of conversation."
        % window["minutes"],
        "",
        "| | |",
        "|---|---|",
        "| Window | %s to %s |" % (start.strftime("%Y-%m-%d %H:%M:%S"),
                                   end.strftime("%H:%M:%S")),
        "| Timezone | %s, %s (%s) |" % (tz["name"] or "unknown", tz["utc_offset"],
                                        tz["abbreviation"]),
        "| Times below | local, on the clock of the machine it was recorded on |",
    ]
    if meta["show_start"]:
        lines.append("| Recording started | %s — T+ is measured from there |"
                     % datetime.fromisoformat(
                         meta["show_start"]).astimezone(tzinfo).strftime("%H:%M:%S"))
    else:
        lines.append("| T+ | measured from the first prompt below |")
    lines += [
        "| Projects | %d |" % len(projects),
        "| Exchanges | %d |" % sum(len(p["exchanges"]) for p in projects),
        "| Left out | %d |" % len(dropped),
        "",
        "Prompts are exactly as they were typed. Answers are the agent's words with the",
        "tool calls, file contents and command output taken out — those never left the",
        "machine.",
        "",
        "## The projects",
        "",
    ]
    for project in projects:
        first = project["exchanges"][0]["when"].astimezone(tzinfo)
        lines += [
            "### %s — [%s](%s)" % (project["name"], project["file"], project["file"]),
            "",
            "From %s. %s, %d left out.%s" % (
                first.strftime("%H:%M:%S"),
                count_of(len(project["exchanges"]), "exchange"),
                project["dropped"],
                " Branch `%s`." % project["branch"] if project["branch"] else ""),
            "",
            INTRO_START,
            project["intro"] or INTRO_PLACEHOLDER,
            INTRO_END,
            "",
        ]

    if dropped:
        lines += [
            "## What was left out",
            "",
            "%s did not travel. Whole exchanges, question and answer both —"
            % count_of(len(dropped), "exchange"),
            "nothing was edited down and kept.",
            "",
        ]
        tally = {}
        for _, reason in dropped:
            tally[reason] = tally.get(reason, 0) + 1
        for reason, count in sorted(tally.items(), key=lambda kv: -kv[1]):
            lines.append("- %d × looked like %s" % (count, reason))
        lines.append("")

    # The intros live in the project files; this copies them, so there is only
    # ever one place to write them.
    with open(os.path.join(directory, "00-summary.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_show_json(directory, projects, meta, tzinfo, origin):
    """The same exchanges as the markdown, in a shape a replayer can read.

    Same set, same text, same drops — it is generated from what survived, so
    there is nothing in here the person has not been shown.
    """
    payload = dict(meta)
    payload["projects"] = []
    for project in projects:
        payload["projects"].append({
            "name": project["name"],
            "path": project["display_path"],
            "file": project["file"],
            "git_branch": project["branch"],
            "left_out": project["dropped"],
            "exchanges": [{
                "id": exchange["id"],
                "session": exchange["session"],
                "utc": exchange["when"].isoformat().replace("+00:00", "Z"),
                "local": exchange["when"].astimezone(tzinfo).isoformat(),
                "elapsed_seconds": int((exchange["when"] - origin).total_seconds()),
                "prompt": exchange["prompt"],
                "answers": exchange["answers"],
            } for exchange in project["exchanges"]],
        })
    path = os.path.join(directory, "show.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


# ---------------------------------------------------------------------------


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Collect Mate Wish Key show notes from this machine.",
        epilog="The window is six hours. It can be narrowed and never widened.")
    parser.add_argument("--minutes", type=int, default=MAX_MINUTES,
                        help="how far back to look, up to %d (default: %d)"
                             % (MAX_MINUTES, MAX_MINUTES))
    parser.add_argument("--since", metavar="HH:MM",
                        help="start at this local time instead, if it is inside the window")
    parser.add_argument("--show-start", metavar="HH:MM",
                        help="when the recording started — T+ times are measured from it")
    parser.add_argument("--out", metavar="DIR",
                        help="where to write (default: ~/mwk-show-notes-<date>)")
    parser.add_argument("--projects-dir", metavar="DIR",
                        default=os.path.expanduser("~/.claude/projects"),
                        help=argparse.SUPPRESS)
    parser.add_argument("--drop", metavar="ID", action="append", default=[],
                        help="leave this exchange out; repeatable")
    parser.add_argument("--drop-project", metavar="NAME", action="append", default=[],
                        help="leave this whole project out; repeatable")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.minutes < 1:
        sys.stderr.write("A window has to be at least a minute long.\n")
        return 2
    if args.minutes > MAX_MINUTES:
        sys.stderr.write(
            "%d minutes is wider than the six hours this is allowed to look at.\n"
            "Narrower is fine; wider is not. Nothing collected.\n" % args.minutes)
        return 2

    tz = local_timezone()
    now = datetime.now(timezone.utc)
    tzinfo = now.astimezone().tzinfo
    since = now - timedelta(minutes=args.minutes)
    local_today = now.astimezone(tzinfo).date()

    narrowed = None
    if args.since:
        asked = parse_clock(args.since, tzinfo, local_today).astimezone(timezone.utc)
        if asked > since:
            since, narrowed = asked, args.since
        else:
            sys.stderr.write(
                "%s is further back than six hours, so the window stays at six hours.\n"
                % args.since)

    show_start = None
    if args.show_start:
        show_start = parse_clock(args.show_start, tzinfo, local_today).astimezone(timezone.utc)

    paths = session_files(args.projects_dir, since)
    exchanges = read_exchanges(paths, since, now)

    if not exchanges:
        sys.stderr.write(
            "Nothing in the last %d minutes on this machine.\n\n"
            "That means the show is not on this computer, or it was recorded somewhere\n"
            "else. Stopping here — reaching further back would collect conversations\n"
            "nobody agreed to send.\n" % args.minutes)
        return 1

    kept, dropped, flagged = sift(exchanges, set(args.drop))
    projects = group_projects(kept, dropped, set(args.drop_project))
    if not projects:
        sys.stderr.write("Every project was left out, so there is nothing to write.\n")
        return 1

    origin = show_start or min(p["exchanges"][0]["when"] for p in projects)

    directory = args.out or os.path.expanduser(
        "~/mwk-show-notes-%s" % now.astimezone(tzinfo).strftime("%Y-%m-%d"))
    os.makedirs(directory, exist_ok=True)

    meta = {
        "tool": "mwk-shownotes",
        "format": 1,
        "date": now.astimezone(tzinfo).strftime("%Y-%m-%d"),
        "generated_utc": now.isoformat().replace("+00:00", "Z"),
        "generated_local": now.astimezone(tzinfo).isoformat(timespec="seconds"),
        "timezone": tz,
        "window": {
            "minutes": args.minutes,
            "narrowed_to": narrowed,
            "start_utc": since.isoformat(),
            "end_utc": now.isoformat(),
        },
        "show_start": show_start.isoformat() if show_start else None,
    }

    counts = {}
    scrub_exchanges(kept, counts)
    intros = previous_intros(directory)
    clear_previous(directory)

    home = os.path.expanduser("~")
    for index, project in enumerate(projects, start=1):
        path = project["path"]
        project["display_path"] = ("~" + path[len(home):]) if path.startswith(home) else path
        project["intro"] = intros.get(project["name"])
        project["file"] = write_project(directory, index, project, meta, tzinfo, origin)

    write_summary(directory, projects, meta, dropped, tzinfo)
    write_show_json(directory, projects, meta, tzinfo, origin)

    # ---- the report the agent reads before it shows anybody anything --------
    out = sys.stdout
    out.write("\nWrote %s\n\n" % directory)
    out.write("  Window     %s to %s (%s)\n" % (
        since.astimezone(tzinfo).strftime("%Y-%m-%d %H:%M:%S"),
        now.astimezone(tzinfo).strftime("%H:%M:%S"),
        tz["name"] or tz["abbreviation"]))
    out.write("  Timezone   %s %s%s\n" % (
        tz["name"] or "unknown", tz["utc_offset"],
        " (%s)" % tz["abbreviation"] if tz["abbreviation"] else ""))
    if show_start:
        out.write("  Recording  started %s — T+ counts from there\n"
                  % show_start.astimezone(tzinfo).strftime("%H:%M:%S"))
    out.write("\n")
    for project in projects:
        out.write("  %-28s %3d kept, %d left out  (%s)\n" % (
            project["file"], len(project["exchanges"]), project["dropped"],
            project["display_path"]))
    out.write("\n")

    if dropped:
        out.write("  Left out %s:\n" % count_of(len(dropped), "exchange"))
        for exchange, reason in dropped:
            out.write("    %s  %s  %s\n" % (
                exchange["id"], exchange["when"].astimezone(tzinfo).strftime("%H:%M:%S"),
                reason))
        out.write("\n")

    if counts:
        out.write("  Taken out of what is left: %s\n\n" % ", ".join(
            "%d × %s" % (n, name) for name, n in sorted(counts.items())))

    if flagged:
        out.write("  Read these first — kept, but they mention something:\n")
        for exchange, note in flagged:
            out.write("    %s  %s  %s\n" % (
                exchange["id"], exchange["when"].astimezone(tzinfo).strftime("%H:%M:%S"),
                note))
        out.write("\n")

    out.write("  This is the net, not the review. Read every exchange yourself:\n"
              "  real names are the one thing no pattern here can catch.\n"
              "  Use --drop <id> or --drop-project <name> and run it again.\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
