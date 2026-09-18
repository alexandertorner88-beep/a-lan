#!/usr/bin/env python3
"""Hämtar resultat från Simresults och bygger site/data.json.

Kör:  python3 build.py
Läser races.json, hämtar CSV-exporten för varje deltävling och skriver
site/data.json som sajten läser. Kräver inga externa paket.
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RACES = os.path.join(HERE, "races.json")
OUT = os.path.join(HERE, "site", "data.json")
CACHE = os.path.join(HERE, ".cache")
SEP = re.compile(r"^'[+=]{5,}")
SESSION_KEYS = {"Qualify": "qualify", "Race": "race1",
                "Race 1": "race1", "Race 2": "race2", "Race2": "race2"}


# --------------------------------------------------------------- hämtning
def fetch_csv(result_id):
    """Hämtar CSV-exporten. Sparas i .cache/ så ombyggen går snabbt."""
    os.makedirs(CACHE, exist_ok=True)
    cached = os.path.join(CACHE, result_id + ".csv")
    if os.path.exists(cached):
        return open(cached, encoding="utf-8", errors="replace").read()

    url = f"https://simresults.net/{result_id}/csv"
    req = urllib.request.Request(url, headers={
        "User-Agent": "liga-resultat/1.0 (+github actions)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8", errors="replace")
    with open(cached, "w", encoding="utf-8") as f:
        f.write(text)
    return text


# --------------------------------------------------------------- parsning
def cells(line):
    return [c.strip().lstrip("'").strip()
            for c in next(csv.reader(io.StringIO(line), skipinitialspace=True))]


def parse(text):
    lines = text.splitlines()
    meta, sessions, incidents = {}, {}, {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        m = re.match(r'^(Game|Date|Track):?,\s*(.*)$', line)
        if m and m.group(1).lower() not in meta:
            meta[m.group(1).lower()] = m.group(2).strip().strip('"').strip()

        m = re.match(r'^(Practice|Qualify|Race ?\d*) result$', line)
        if m:
            label = re.sub(r"\s+", " ", m.group(1)).strip()
            key = SESSION_KEYS.get(label)
            i += 1
            while i < len(lines) and SEP.match(lines[i].strip()):
                i += 1
            header = cells(lines[i])
            i += 1
            rows = []
            while i < len(lines) and lines[i].strip():
                row = dict(zip(header, cells(lines[i])))
                if row.get("Pos", "").isdigit():
                    rows.append(row)
                i += 1
            if key:
                sessions[key] = rows
            continue

        m = re.match(r'^Race ?(\d+) incidents$', line)
        if m:
            key = "race" + m.group(1)
            i += 1
            while i < len(lines) and SEP.match(lines[i].strip()):
                i += 1
            i += 1                      # rubrikraden
            items = []
            while i < len(lines) and lines[i].strip():
                c = cells(lines[i])
                inc = parse_incident(c[1] if len(c) > 1 else "")
                if inc:
                    items.append(inc)
                i += 1
            if items:
                incidents[key] = items
            continue

        i += 1
    return meta, sessions, incidents


def parse_incident(txt):
    """'LAP 8, Emil W, Ivan G, Car to car collision, Points: 4'"""
    m = re.match(r'^LAP (\d+),\s*(.*?),\s*Points:\s*(\d+)$', txt)
    if not m:
        return None
    parts = [p.strip() for p in m.group(2).split(",")]
    return {"lap": int(m.group(1)), "driver": parts[0],
            "other": parts[1] if len(parts) > 2 else "",
            "type": parts[-1], "points": int(m.group(3))}


def finished(t):
    return not re.match(r'^\s*(DNF|DNS|DSQ)', t or "", re.I)


def build_round(result_id, number, name, meta, sessions, incidents):
    out = {"id": result_id, "round": number,
           "source": f"https://simresults.net/{result_id}",
           "track": meta.get("track", ""),
           "date": (meta.get("date", "") or "")[:10],
           "sessions": {}, "incidents": incidents}
    out["name"] = name or out["track"].split(",")[0].strip() or result_id

    if "qualify" in sessions:
        out["sessions"]["qualify"] = [
            [int(r["Pos"]), r["Driver"], r["Vehicle"], int(r.get("Laps") or 0),
             r.get("Best lap", ""), r.get("Gap", "-")]
            for r in sessions["qualify"]]

    for key in ("race1", "race2"):
        rows = sessions.get(key)
        if not rows:
            continue
        top = max(int(r.get("Laps") or 0) for r in rows)
        built = []
        for r in rows:
            laps = int(r.get("Laps") or 0)
            t = r.get("Time/Retired", "")
            behind = top - laps
            if behind > 0 and finished(t):
                t = f"+{behind} varv"
            built.append([int(r["Pos"]), r["Driver"], r["Vehicle"], laps, t,
                          r.get("Best lap", ""), int(r.get("Led") or 0)])
        out["sessions"][key] = built
    return out


# --------------------------------------------------------------- main
def main():
    cfg = json.load(open(RACES, encoding="utf-8"))
    built, failed = [], []

    for entry in cfg.get("rounds", []):
        rid = entry["id"]
        try:
            text = fetch_csv(rid)
            meta, sessions, incidents = parse(text)
            if not sessions:
                raise ValueError("inga resultattabeller i filen")
            r = build_round(rid, entry.get("round", len(built) + 1),
                            entry.get("name", ""), meta, sessions, incidents)
            built.append(r)
            counts = ", ".join(f"{k} {len(v)}" for k, v in r["sessions"].items())
            print(f"  OK   {rid}  {r['name']}  ({counts})")
        except Exception as e:
            failed.append((rid, e))
            print(f"  FEL  {rid}  {e}", file=sys.stderr)

    if not built:
        print("Inga deltävlingar kunde byggas. Avbryter.", file=sys.stderr)
        sys.exit(1)

    built.sort(key=lambda r: r["round"])
    data = {"league": cfg.get("league", "Racing League"),
            "season": cfg.get("season", ""),
            "points": cfg.get("points", {}),
            "rounds": built}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"\nSkrev {OUT} med {len(built)} deltävling(ar).")
    if failed:
        print(f"{len(failed)} misslyckades — sajten byggs med resten.")


if __name__ == "__main__":
    main()
