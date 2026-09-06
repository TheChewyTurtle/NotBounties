#!/usr/bin/env python3
"""
Convert BountyHunters (Indyuce) data + config into NotBounties.

Works on any server: point it at the BountyHunters plugin folder and the
NotBounties plugin folder. Nothing here is server specific.

What it produces
  1. <NotBounties>/bounties.yml   - NotBounties' legacy import file. NotBounties
     reads this file once on startup, converts it into data/*.json, and then
     ignores it. Contains: active bounties, player stats, and a UUID->name cache.
  2. Edits to NotBounties config files (config.yml, settings/*.yml) for the
     BountyHunters settings that have an equivalent. Comments are preserved.
     Use --no-config to skip this.
  3. A migration report printed to stdout (and saved next to bounties.yml)
     listing what was converted and what BountyHunters features have no
     NotBounties equivalent.

Usage
  python bountyhunters_to_notbounties.py <BountyHunters dir> <NotBounties dir>
        [--usercache <server>/usercache.json] [--jar NotBounties.jar]
        [--no-config] [--dry-run]

  --usercache  Improves UUID->name mapping (BountyHunters only caches names for
               players on its leaderboards).
  --jar        If the NotBounties folder has never been generated, default
               config files are extracted from this jar before editing.
  --dry-run    Print what would change, write nothing.

Stat mapping (BountyHunters -> NotBounties)
  claimed-bounties    -> kills   (bounties this player claimed as the hunter)
  successful-bounties -> set     (bounties this player placed that got claimed)
  Everything else (level, titles, animations, illegal kills, redeem heads) has
  no equivalent and is reported, not migrated.

Requires only the Python standard library (no PyYAML).
"""

import argparse
import io
import json
import os
import re
import sys
import uuid
import zipfile
from datetime import datetime

CONSOLE_UUID = "00000000-0000-0000-0000-000000000000"
CONSOLE_NAME = "Sheriff"  # NotBounties' default console-bounty-name


# ----------------------------------------------------------------------------
# Minimal YAML reader (enough for BountyHunters' simple files)
# ----------------------------------------------------------------------------

def _parse_scalar(text):
    text = text.strip()
    if text == "" or text == "~" or text.lower() == "null":
        return None
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1].replace("''", "'")
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?\d+\.\d*([eE][-+]?\d+)?", text):
            return float(text)
    except ValueError:
        pass
    return text


def load_simple_yaml(path):
    """Parse block-style YAML with nested maps, scalar values and simple lists."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    root = {}
    stack = [(-1, root)]  # (indent, container)
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        stripped = raw.split("#", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not stripped.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = stripped.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith("- "):
            # list item under the last key
            if isinstance(parent, list):
                parent.append(_parse_scalar(content[2:]))
            continue
        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip().strip("'\"")
        value = value.strip()
        if value == "":
            # look ahead: list or map?
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("- "):
                child = []
            else:
                child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root


# ----------------------------------------------------------------------------
# Comment-preserving YAML editing (for NotBounties config files)
# ----------------------------------------------------------------------------

def yaml_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            return repr(value)
        return str(value)
    if value is None:
        return "~"
    s = str(value)
    if re.search(r"[:#'\"{}\[\],&*!|>%@`]", s) or s.strip() != s or s == "":
        return "'" + s.replace("'", "''") + "'"
    return s


def set_yaml_key(lines, path, value):
    """
    Set path (list of keys) to a scalar value in a list of YAML lines,
    preserving all other lines and comments. Returns (lines, changed, old_text).
    Creates missing keys at the end of the parent section.
    """
    depth = 0
    parent_indent = -1
    start = 0
    end = len(lines)
    for depth, key in enumerate(path):
        found = None
        indent_here = None
        idx = start
        while idx < end:
            line = lines[idx]
            code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
            if code.strip():
                ind = len(line) - len(line.lstrip(" "))
                if ind <= parent_indent:
                    break  # left the parent section
                m = re.match(r"^\s*([^\s:#][^:]*?)\s*:(\s*(.*))?$", code.rstrip())
                if m and ind == (parent_indent + 2 if parent_indent >= 0 else 0) or (m and indent_here is None and ind > parent_indent and depth == 0 and ind == 0):
                    k = m.group(1).strip().strip("'\"")
                    if indent_here is None:
                        indent_here = ind
                    if ind == indent_here and k == key:
                        found = idx
                        break
            idx += 1
        section_end = idx  # first line outside parent section (or where search stopped)
        if found is None:
            # create the key
            new_indent = (parent_indent + 2) if parent_indent >= 0 else 0
            insert_at = section_end
            # back up over trailing blank lines so the key stays inside the section
            while insert_at > start and not lines[insert_at - 1].strip():
                insert_at -= 1
            if depth == len(path) - 1:
                lines.insert(insert_at, " " * new_indent + f"{key}: {yaml_scalar(value)}")
                return lines, True, None
            lines.insert(insert_at, " " * new_indent + f"{key}:")
            found = insert_at
            end = insert_at + 1
        if depth == len(path) - 1:
            line = lines[found]
            m = re.match(r"^(\s*[^:]+:)(\s*)(.*)$", line)
            prefix = m.group(1)
            rest = m.group(3)
            comment = ""
            body = rest
            # keep an inline comment
            cm = re.search(r"\s+#.*$", rest)
            if cm and not rest.lstrip().startswith("#"):
                comment = cm.group(0)
                body = rest[: cm.start()]
            elif rest.lstrip().startswith("#"):
                comment = " " + rest.lstrip()
                body = ""
            new_line = f"{prefix} {yaml_scalar(value)}{comment}"
            changed = new_line != line
            lines[found] = new_line
            return lines, changed, body.strip()
        # descend
        parent_indent = len(lines[found]) - len(lines[found].lstrip(" "))
        start = found + 1
        # find the end of this section
        j = start
        while j < len(lines):
            l = lines[j]
            if l.strip() and not l.lstrip().startswith("#"):
                if len(l) - len(l.lstrip(" ")) <= parent_indent:
                    break
            j += 1
        end = j
    return lines, False, None


# ----------------------------------------------------------------------------
# BountyHunters readers
# ----------------------------------------------------------------------------

def read_bh_names(bh_dir, usercache_path):
    names = {}
    cache_dir = os.path.join(bh_dir, "cache")
    for fname in ("leaderboard.yml", "bounty-leaderboard.yml"):
        p = os.path.join(cache_dir, fname)
        if os.path.isfile(p):
            for k, v in load_simple_yaml(p).items():
                if isinstance(v, dict) and v.get("name"):
                    names[k.lower()] = str(v["name"])
    if usercache_path and os.path.isfile(usercache_path):
        with open(usercache_path, "r", encoding="utf-8") as f:
            for entry in json.load(f):
                u = str(entry.get("uuid", "")).lower()
                n = entry.get("name")
                if u and n:
                    names[u] = n
    return names


def read_bh_bounties(bh_dir):
    p = os.path.join(bh_dir, "data.yml")
    if not os.path.isfile(p):
        return []
    data = load_simple_yaml(p)
    bounties = []
    for bid, b in data.items():
        if not isinstance(b, dict) or "target" not in b:
            continue
        contributions = b.get("up") or {}
        bounties.append({
            "id": bid,
            "target": str(b["target"]).lower(),
            "extra": float(b.get("extra") or 0.0),
            "last_modified": int(b.get("last-modified") or 0),
            "contributions": {str(k).lower(): float(v) for k, v in contributions.items()},
        })
    return bounties


def read_bh_players(bh_dir):
    udir = os.path.join(bh_dir, "userdata")
    players = {}
    if not os.path.isdir(udir):
        return players
    for fname in os.listdir(udir):
        if not fname.endswith(".yml"):
            continue
        u = fname[:-4].lower()
        try:
            uuid.UUID(u)
        except ValueError:
            continue
        d = load_simple_yaml(os.path.join(udir, fname))
        players[u] = {
            "level": int(d.get("level") or 0),
            "successful": int(d.get("successful-bounties") or 0),
            "claimed": int(d.get("claimed-bounties") or 0),
            "illegal_kills": int(d.get("illegal-kills") or 0),
            "redeem_heads": d.get("redeem-heads") or [],
            "title": d.get("title"),
            "animation": d.get("animation") or d.get("quote"),
        }
    return players


def is_offline_uuid(u):
    # BountyHunters/Bedrock style placeholder ids like 00000000-0000-0000-0009-...
    return u.startswith("00000000-0000-0000-0009-")


# ----------------------------------------------------------------------------
# NotBounties legacy bounties.yml writer
# ----------------------------------------------------------------------------

def q(s):
    return "'" + str(s).replace("'", "''") + "'"


def build_bounties_yml(bounties, players, names, console_name, now_ms):
    out = io.StringIO()
    out.write("# Generated by tools/bountyhunters_to_notbounties.py on %s\n" % datetime.now().isoformat(timespec="seconds"))
    out.write("# NotBounties imports this file once on startup and converts it to data/*.json.\n")
    out.write("server-id: %s\n" % uuid.uuid4())

    # name cache
    used = set()
    for b in bounties:
        used.add(b["target"])
        used.update(b["contributions"].keys())
    used.update(players.keys())
    out.write("logged-players:\n")
    for u in sorted(used):
        if u in names and not is_offline_uuid(u):
            out.write("  %s: %s\n" % (u, q(names[u])))

    # bounties
    out.write("bounties:\n")
    skipped = []
    written = 0
    for b in bounties:
        setters = []
        t_created = b["last_modified"] or now_ms
        for su, amt in b["contributions"].items():
            if amt <= 0:
                continue
            setters.append((su, names.get(su, "Unknown"), amt))
        if b["extra"] > 0:
            setters.append((CONSOLE_UUID, console_name, b["extra"]))
        if not setters:
            skipped.append((b["target"], "no positive contributions"))
            continue
        out.write("  %d:\n" % written)
        out.write("    uuid: %s\n" % b["target"])
        out.write("    name: %s\n" % q(names.get(b["target"], "Unknown")))
        for idx, (su, sname, amt) in enumerate(setters):
            out.write("    %d:\n" % idx)
            out.write("      uuid: %s\n" % su)
            out.write("      name: %s\n" % q(sname))
            out.write("      amount: %s\n" % repr(float(amt)))
            out.write("      time-created: %d\n" % t_created)
            out.write("      notified: true\n")
        written += 1

    # stats
    out.write("data:\n")
    stat_count = 0
    for u in sorted(players):
        p = players[u]
        if p["claimed"] == 0 and p["successful"] == 0:
            continue
        out.write("  %s:\n" % u)
        out.write("    kills: %d\n" % p["claimed"])
        out.write("    set: %d\n" % p["successful"])
        stat_count += 1
    return out.getvalue(), written, skipped, stat_count


# ----------------------------------------------------------------------------
# Config mapping
# ----------------------------------------------------------------------------

def get(d, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def plan_config_changes(bh):
    """Return list of (file, key-path, value, explanation) and list of unmapped notes."""
    changes = []
    notes = []

    # config.yml
    if get(bh, "inactive-bounty-removal", "enabled") is True:
        hours = float(get(bh, "inactive-bounty-removal", "time", default=0) or 0)
        if hours > 0:
            changes.append(("config.yml", ["bounty-expire", "time"], round(hours / 24.0, 4),
                            "inactive-bounty-removal.time %g h -> %g days" % (hours, hours / 24.0)))
    else:
        changes.append(("config.yml", ["bounty-expire", "time"], -1, "inactive-bounty-removal disabled"))
    own = get(bh, "claim-restrictions", "own-bounties")
    if own is not None:
        changes.append(("config.yml", ["setter-claim-own"], not own,
                        "claim-restrictions.own-bounties=%s (BountyHunters 'true' = may NOT claim own)" % own))
    upd = get(bh, "update-notify")
    if upd is not None:
        changes.append(("config.yml", ["update-notification"], bool(upd), "update-notify"))
    creator_head = get(bh, "drop-head", "creator", "enabled")
    killer_head = get(bh, "drop-head", "killer", "enabled")
    if creator_head is not None:
        changes.append(("config.yml", ["reward-heads", "setters"], bool(creator_head), "drop-head.creator.enabled"))
    if killer_head is not None:
        changes.append(("config.yml", ["reward-heads", "claimed"], bool(killer_head), "drop-head.killer.enabled"))

    # settings/immunity.yml
    cd = get(bh, "bounty-set-restriction")
    if cd is not None:
        changes.append(("settings/immunity.yml", ["bounty-cooldown"], int(cd), "bounty-set-restriction (seconds between /bounty)"))

    # settings/money.yml
    scale = get(bh, "bounty-tax", "bounty-creation", "scale")
    if scale is not None:
        changes.append(("settings/money.yml", ["bounty-tax"], round(float(scale) / 100.0, 4),
                        "bounty-tax.bounty-creation.scale %s%% -> decimal" % scale))
    flat = get(bh, "bounty-tax", "bounty-creation", "flat")
    if flat:
        notes.append("bounty-tax.bounty-creation.flat=%s: NotBounties has no flat tax, only a percentage." % flat)
    mn = get(bh, "min-reward")
    if mn is not None:
        changes.append(("settings/money.yml", ["minimum-bounty"], max(int(mn), 1), "min-reward (NotBounties minimum is 1)"))
    mx = get(bh, "max-reward")
    if mx is not None:
        changes.append(("settings/money.yml", ["maximum-bounty"], int(mx) if int(mx) > 0 else -1, "max-reward (0 -> -1 = no limit)"))
    fmt = get(bh, "formatted-numbers")
    if fmt is not None:
        changes.append(("settings/money.yml", ["number-formatting", "use-divisions"], bool(fmt), "formatted-numbers"))

    # settings/display.yml
    tr = get(bh, "player-tracking", "enabled")
    if tr is not None:
        changes.append(("settings/display.yml", ["bounty-tracker", "enabled"], bool(tr), "player-tracking.enabled"))
    own_track = get(bh, "player-tracking", "can-track-own-bounties")
    if own_track is not None:
        changes.append(("settings/display.yml", ["bounty-tracker", "give-own"], bool(own_track), "player-tracking.can-track-own-bounties"))
    if get(bh, "player-tracking", "price") is not None:
        notes.append("player-tracking.price/cooldown: NotBounties trackers are crafted items (see settings/display.yml bounty-tracker), no purchase price or cooldown option.")

    # settings/integrations.yml (team claim restrictions)
    for bh_key, nb_path in (
        ("town-members", ["teams", "towny-advanced", "town"]),
        ("lands", ["teams", "lands", "land"]),
        ("simple-clans", ["teams", "simple-clans", "clan"]),
        ("factions", ["teams", "factions", "faction"]),
        ("kingdoms", ["teams", "kingdoms-x", "kingdom"]),
    ):
        v = get(bh, "claim-restrictions", bh_key)
        if v is not None:
            changes.append(("settings/integrations.yml", nb_path, bool(v), "claim-restrictions.%s" % bh_key))
    for bh_key in ("friends", "guilds", "ultimate-clans", "bed-spawn-point", "targets-only"):
        if get(bh, "claim-restrictions", bh_key) not in (None, False) and not (isinstance(get(bh, "claim-restrictions", bh_key), dict) and not get(bh, "claim-restrictions", bh_key, "enabled")):
            notes.append("claim-restrictions.%s: no NotBounties equivalent." % bh_key)

    # settings/auto-bounties.yml
    if get(bh, "auto-bounty", "enabled") is True:
        reward = get(bh, "auto-bounty", "reward", default=0)
        changes.append(("settings/auto-bounties.yml", ["murder-bounty", "bounty-increase"], float(reward),
                        "auto-bounty.reward (bounty placed on players who kill an un-bountied player)"))
        if get(bh, "auto-bounty", "chance", default=100) != 100:
            notes.append("auto-bounty.chance: NotBounties murder bounties always apply (no chance option).")

    # Always-unmapped features
    # BountyHunters always has a level system; NotBounties never does.
    notes.append("Levels, hunter titles, quotes/animations and level rewards (levels.yml): NotBounties has no level system. Player levels are NOT migrated. Consider NotBounties challenges as a replacement.")
    if get(bh, "bounty-amount-restriction"):
        notes.append("bounty-amount-restriction=%s (max bounties one player can have open): no NotBounties equivalent (max-setters limits setters per bounty, not per player)." % get(bh, "bounty-amount-restriction"))
    if get(bh, "bounty-tax", "bounty-removal", "scale") or get(bh, "bounty-tax", "target-set", "scale"):
        notes.append("bounty-tax.bounty-removal / target-set: no equivalent. NotBounties has death-tax (paid by the target on death) in settings/money.yml if you want something similar.")
    if get(bh, "tax-bank-account", "name"):
        notes.append("tax-bank-account: NotBounties taxes are removed from the economy (no deposit account).")
    if get(bh, "head-hunting", "enabled"):
        notes.append("head-hunting: NotBounties reward-heads covers head drops but not the 'right-click head to claim' flow.")
    if get(bh, "target-login-message", "enabled"):
        notes.append("target-login-message: no direct equivalent; NotBounties announces via wanted tags / broadcast settings.")
    notes.append("language/messages.yml and items.yml: message keys differ completely; re-theme NotBounties' language.yml and gui.yml by hand.")
    notes.append("illegal-kills / illegal-kill-streak / redeem-heads per-player data: not migrated (no equivalent).")
    return changes, notes


def ensure_config_file(nb_dir, rel, jar_path):
    dest = os.path.join(nb_dir, rel)
    if os.path.isfile(dest):
        return True
    if jar_path and os.path.isfile(jar_path):
        with zipfile.ZipFile(jar_path) as z:
            name = rel.replace(os.sep, "/")
            if name in z.namelist():
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with z.open(name) as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                return True
    return False


def apply_config_changes(nb_dir, changes, jar_path, dry_run):
    report = []
    by_file = {}
    for f, path, value, why in changes:
        by_file.setdefault(f, []).append((path, value, why))
    for rel, items in by_file.items():
        if not ensure_config_file(nb_dir, rel, jar_path):
            report.append("SKIP %s: file not found (start the server once or pass --jar)" % rel)
            continue
        p = os.path.join(nb_dir, rel)
        with open(p, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for path, value, why in items:
            lines, changed, old = set_yaml_key(lines, path, value)
            report.append("%s %s: %s -> %s   (%s)" % ("SET " if changed else "KEEP", rel, ".".join(path) if old is None else ".".join(path) + " [was %s]" % old, yaml_scalar(value), why))
        if not dry_run:
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines) + "\n")
    return report


# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bountyhunters_dir")
    ap.add_argument("notbounties_dir")
    ap.add_argument("--usercache", help="path to the server's usercache.json for UUID->name mapping")
    ap.add_argument("--jar", help="NotBounties jar, used to extract default config files if missing")
    ap.add_argument("--no-config", action="store_true", help="only convert data, do not touch NotBounties config")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    bh_dir = args.bountyhunters_dir
    nb_dir = args.notbounties_dir
    if not os.path.isdir(bh_dir):
        sys.exit("BountyHunters folder not found: %s" % bh_dir)
    os.makedirs(nb_dir, exist_ok=True)

    bh_config = load_simple_yaml(os.path.join(bh_dir, "config.yml")) if os.path.isfile(os.path.join(bh_dir, "config.yml")) else {}
    names = read_bh_names(bh_dir, args.usercache)
    bounties = read_bh_bounties(bh_dir)
    players = read_bh_players(bh_dir)

    # console setter name from NotBounties settings if already configured
    console_name = CONSOLE_NAME
    ab = os.path.join(nb_dir, "settings", "auto-bounties.yml")
    if os.path.isfile(ab):
        v = load_simple_yaml(ab).get("console-bounty-name")
        if v:
            console_name = str(v)

    now_ms = int(datetime.now().timestamp() * 1000)
    yml, n_bounties, skipped, n_stats = build_bounties_yml(bounties, players, names, console_name, now_ms)

    lines = []
    lines.append("=== BountyHunters -> NotBounties migration report (%s) ===" % datetime.now().isoformat(timespec="seconds"))
    lines.append("BountyHunters folder : %s" % os.path.abspath(bh_dir))
    lines.append("NotBounties folder   : %s" % os.path.abspath(nb_dir))
    lines.append("")
    lines.append("Active bounties converted : %d (of %d in data.yml)" % (n_bounties, len(bounties)))
    for t, why in skipped:
        lines.append("  skipped bounty on %s: %s" % (t, why))
    for b in bounties:
        total = sum(v for v in b["contributions"].values()) + b["extra"]
        lines.append("  target %s (%s): %g from %d setter(s)%s" % (
            names.get(b["target"], "?"), b["target"], total, len(b["contributions"]),
            " + %g console" % b["extra"] if b["extra"] > 0 else ""))
    lines.append("Players with stats        : %d written (of %d userdata files; players with 0/0 are skipped)" % (n_stats, len(players)))
    lines.append("Names resolved            : %d UUIDs (%s)" % (len(names), "leaderboard caches" + (" + usercache.json" if args.usercache else "")))
    lines.append("Stat mapping              : claimed-bounties -> kills, successful-bounties -> set")
    lines.append("")

    if not args.dry_run:
        out_path = os.path.join(nb_dir, "bounties.yml")
        if os.path.exists(out_path):
            bak = out_path + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S")
            os.replace(out_path, bak)
            lines.append("Existing bounties.yml backed up to %s" % os.path.basename(bak))
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(yml)
        lines.append("Wrote %s" % out_path)
        if os.path.isdir(os.path.join(nb_dir, "data")):
            lines.append("NOTE: %s already has a data/ folder. Legacy bounties.yml is merged into it on startup; stop the server first and back up data/." % nb_dir)
    else:
        lines.append("[dry-run] would write %s (%d lines)" % (os.path.join(nb_dir, "bounties.yml"), yml.count("\n")))

    lines.append("")
    if args.no_config:
        lines.append("Config migration skipped (--no-config).")
        notes = []
    else:
        changes, notes = plan_config_changes(bh_config)
        lines.append("Config changes:")
        lines.extend("  " + r for r in apply_config_changes(nb_dir, changes, args.jar, args.dry_run))
    lines.append("")
    lines.append("Not migrated / no equivalent:")
    lines.extend("  - " + n for n in notes)

    text = "\n".join(lines)
    print(text)
    if not args.dry_run:
        with open(os.path.join(nb_dir, "bountyhunters-migration-report.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
