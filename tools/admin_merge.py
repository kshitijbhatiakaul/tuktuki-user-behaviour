#!/usr/bin/env python3
"""Admin panel refresh helpers.

  python3 tools/admin_merge.py plan [YESTERDAY]
      Print JSON {from, to, windows} for admin_fetch.js: re-pull the last 45 days
      (renewals and D30 return keep maturing) and the unique-viewer windows the
      dashboard presets use (last 7/30/90 days, since relaunch, this month, last month).
  python3 tools/admin_merge.py merge DAILY.csv SERIES.csv WINDOWS.csv
      Merge fresh pulls into data/admin/*.csv: re-pulled days replace old rows,
      rolling windows are replaced, calendar-month windows are kept.
"""
import calendar, csv, datetime as dt, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = os.path.join(ROOT, "data", "admin")
RELAUNCH = "2026-09-07"


def ist_yesterday():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    return (now.date() - dt.timedelta(days=1)).isoformat()


def plan(y):
    yd = dt.date.fromisoformat(y)
    d = lambda n: (yd - dt.timedelta(days=n - 1)).isoformat()
    wins = [[d(7), y], [d(30), y], [d(90), y]]
    if (yd - dt.date.fromisoformat(RELAUNCH)).days <= 95:
        wins.append([RELAUNCH, y])
    first = yd.replace(day=1)
    wins.append([first.isoformat(), y])
    pm_end = first - dt.timedelta(days=1)
    wins.append([pm_end.replace(day=1).isoformat(), pm_end.isoformat()])
    uniq = []
    for w in wins:
        if w not in uniq:
            uniq.append(w)
    return {"from": (yd - dt.timedelta(days=44)).isoformat(), "to": y, "windows": uniq}


def read(path):
    if not os.path.exists(path):
        return [], []
    with open(path, newline="", encoding="utf-8") as f:
        r = list(csv.reader(f))
    return (r[0], r[1:]) if r else ([], [])


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def full_month(s, e):
    a, b = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
    return a.day == 1 and a.year == b.year and a.month == b.month and b.day == calendar.monthrange(b.year, b.month)[1]


def merge(daily_new, series_new, windows_new):
    # daily: key = day, columns unioned
    oh, orows = read(os.path.join(ADMIN, "admin_daily.csv"))
    nh, nrows = read(daily_new)
    if not nrows:
        sys.exit("daily pull is empty; nothing merged")
    header = (oh or ["day"]) + [c for c in nh if c not in (oh or ["day"])]
    m = {r[0]: dict(zip(oh, r)) for r in orows}
    for r in nrows:
        m[r[0]] = {**m.get(r[0], {}), **dict(zip(nh, r))}
    write(os.path.join(ADMIN, "admin_daily.csv"), header, [[m[k].get(c, "") for c in header] for k in sorted(m)])
    print(f"admin_daily: {len(orows)} -> {len(m)} days")
    # series daily: drop re-pulled days, append new
    sh, srows = read(os.path.join(ADMIN, "series_daily.csv"))
    nh2, nrows2 = read(series_new)
    newdays = {r[0] for r in nrows} | {r[0] for r in nrows2}
    kept = [r for r in srows if r[0] not in newdays]
    out = sorted(kept + nrows2, key=lambda r: (r[0], r[1]))
    write(os.path.join(ADMIN, "series_daily.csv"), nh2 or sh, out)
    print(f"series_daily: {len(srows)} -> {len(out)} rows")
    # windows: keep full calendar months not re-pulled; replace the rest
    wh, wrows = read(os.path.join(ADMIN, "series_windows.csv"))
    nh3, nrows3 = read(windows_new)
    newwins = {(r[0], r[1]) for r in nrows3}
    kept = [r for r in wrows if (r[0], r[1]) not in newwins and full_month(r[0], r[1])]
    out = kept + nrows3
    write(os.path.join(ADMIN, "series_windows.csv"), nh3 or wh, out)
    print(f"series_windows: {len(wrows)} -> {len(out)} rows; windows now: {sorted({(r[0], r[1]) for r in out})}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        print(json.dumps(plan(sys.argv[2] if len(sys.argv) > 2 else ist_yesterday())))
    elif len(sys.argv) == 5 and sys.argv[1] == "merge":
        merge(*sys.argv[2:5])
    else:
        sys.exit(__doc__)
