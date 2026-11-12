#!/usr/bin/env python3
"""Build the public TukTuki User Behaviour page.

Usage:
  python3 build.py merge <dataset> <new.csv> <key cols comma-separated>
      Merge freshly fetched rows into data/<dataset>.csv (rows with the same key
      are replaced, new keys added). Used by the daily refresh.
  python3 build.py build
      Write docs/index.html from source/dashboard.html + data/.
"""
import csv, io, json, os, sys, datetime, html

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
ADJUST = ["daily", "events", "cohorts", "channels", "backcamp", "purchases", "paycohort", "paychan"]
GA = ["ga_breakdowns", "ga_explore", "ga_monthly"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = list(csv.reader(f))
    return (r[0], r[1:]) if r else ([], [])


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def merge(name, newfile, keys):
    target = os.path.join(DATA, name + ".csv")
    nh, nrows = read_csv(newfile)
    if not nrows:
        sys.exit(f"{newfile} has no rows; nothing merged")
    if os.path.exists(target):
        oh, orows = read_csv(target)
    else:
        oh, orows = nh, []
    header = oh + [c for c in nh if c not in oh]
    keycols = keys.split(",")

    def k(h, row):
        d = dict(zip(h, row))
        return tuple(d.get(c, "") for c in keycols)

    merged = {}
    for row in orows:
        d = dict(zip(oh, row))
        merged[k(oh, row)] = d
    for row in nrows:
        d = dict(zip(nh, row))
        key = k(nh, row)
        merged[key] = {**merged.get(key, {}), **d}
    out = [[merged[key].get(c, "") for c in header] for key in sorted(merged)]
    write_csv(target, header, out)
    print(f"{name}: {len(orows)} -> {len(out)} rows")


def combine_daily_parts():
    parts = sorted(p for p in os.listdir(DATA) if p.startswith("daily_part") and p.endswith(".csv"))
    if not parts or os.path.exists(os.path.join(DATA, "daily.csv")):
        return
    for p in parts:
        merge("daily", os.path.join(DATA, p), "day")


THEME = """
:root{--color-bg:#fafaf7;--color-panel:#ffffff;--color-fg:#1f1e1c;--color-fg-muted:#6b6a65;--color-border-line:#e4e2dc;--color-bad:#c2410c;--color-ok:#15803d;
--cds-chart-grid:#ecebe6;--cds-chart-reference:#9a9890;--cds-chart-muted:#d6d4cd;--cds-chart-status-critical:#c2410c;--cds-surface-popover:#ffffff;--cds-border:#dcdad3;
--cds-shadow-popover:0 4px 16px rgba(0,0,0,.12);--cds-text-secondary:#6b6a65;
--cds-gap-xs:4px;--cds-gap-sm:8px;--cds-gap-md:12px;--cds-gap-lg:20px;--cds-gap-xl:28px;--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:16px;--cds-radius:10px;
--cds-font-size-caption:12.5px;--cds-font-size-body:15px;--cds-font-size-heading:18px;--cds-font-size-title:28px;--cds-font-weight-medium:600;--cds-dur-slow:.4s;
--font-anthropic-serif:Georgia,"Times New Roman",serif;--font-anthropic-sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--color-bg:#1b1a18;--color-panel:#252422;--color-fg:#eceae4;--color-fg-muted:#a3a19a;--color-border-line:#3a3936;
--cds-chart-grid:#33322f;--cds-chart-muted:#4a4945;--cds-surface-popover:#2c2b28;--cds-border:#44433f;--cds-text-secondary:#a3a19a;--color-bad:#f97316;--color-ok:#4ade80}}
:root[data-theme=dark]{--color-bg:#1b1a18;--color-panel:#252422;--color-fg:#eceae4;--color-fg-muted:#a3a19a;--color-border-line:#3a3936;
--cds-chart-grid:#33322f;--cds-chart-muted:#4a4945;--cds-surface-popover:#2c2b28;--cds-border:#44433f;--cds-text-secondary:#a3a19a;--color-bad:#f97316;--color-ok:#4ade80}
html,body{margin:0;background:var(--color-bg);color:var(--color-fg)}
#dash-root{max-width:1200px;margin:0 auto;padding:16px;box-sizing:border-box;overflow-x:hidden}
#dash-root a{color:inherit}
.snap{font:12.5px var(--font-anthropic-sans);color:var(--color-fg-muted);max-width:1200px;margin:0 auto;padding:12px 16px 0;box-sizing:border-box}
@media (max-width:600px){:root{--cds-font-size-title:22px;--cds-pad-lg:12px}}
"""

SHIM = r"""
window.dash = (function () {
  const RAW = window.__DASH_RAW || {};
  const loaders = {}, calcs = {}, draws = new Map(), onDataFns = [], cache = {};
  let params = {};
  const dark = () => matchMedia('(prefers-color-scheme: dark)').matches;
  const api = {
    colors: ['#2f6fd1', '#d9822b', '#1f9d8a', '#b8478f', '#7a5cc4', '#6b8e23'],
    loader(id, o) { loaders[id] = o; },
    calc(id, o) { calcs[id] = o; },
    data(id) {
      if (cache[id]) return cache[id];
      if (calcs[id]) {
        const c = calcs[id];
        const ins = (c.inputs || []).map((i) => { const d = api.data(i); return d.status === 'ok' ? d.data : []; });
        try { cache[id] = { status: 'ok', data: c.fn(...ins), refreshing: false, meta: {} }; }
        catch (e) { cache[id] = { status: 'error', data: null, message: String(e) }; }
        return cache[id];
      }
      const r = RAW[id];
      if (!r) return { status: 'missing', data: [], message: 'Not in this snapshot', refreshing: false, meta: {} };
      try {
        let rows, cols;
        if (loaders[id]) { const o = loaders[id].fn({ answer: r.text !== undefined ? r.text : r.data }); rows = o.rows || o; cols = o.columns || (rows[0] ? Object.keys(rows[0]) : []); }
        else { rows = r.data; cols = rows[0] ? Object.keys(rows[0]) : []; }
        rows.columns = cols;
        cache[id] = { status: 'ok', data: rows, columns: cols, refreshing: false, meta: {} };
      } catch (e) { console.error(id, e); cache[id] = { status: 'error', data: [], message: String(e), refreshing: false, meta: {} }; }
      return cache[id];
    },
    onData(fn) { onDataFns.push(fn); },
    draw(name, fn) { draws.set(name, fn); },
    params() { return Object.assign({}, params); },
    setParams(o) { Object.assign(params, o); render(); },
    resetParams() { params = {}; render(); },
    refresh() {}, setLink() {}
  };
  function render() {
    onDataFns.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
    draws.forEach((fn, name) => document.querySelectorAll('[data-draw="' + name + '"]').forEach((el) => { try { fn(el); } catch (e) { console.error(name, e); } }));
  }
  let lastW = 0, t;
  addEventListener('resize', () => { if (innerWidth === lastW) return; lastW = innerWidth; clearTimeout(t); t = setTimeout(render, 150); });
  document.addEventListener('DOMContentLoaded', () => { lastW = innerWidth; render(); });
  return api;
})();
"""


def build():
    combine_daily_parts()
    raw = {}
    for name in ADJUST:
        p = os.path.join(DATA, name + ".csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                raw[name] = {"text": f.read()}
    for name in GA:
        p = os.path.join(DATA, "ga", name + ".json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                raw[name] = {"data": json.load(f)}
    with open(os.path.join(ROOT, "source", "dashboard.html"), encoding="utf-8") as f:
        page = f.read()
    page = page.replace('<meta name="dash-one-writer">', "", 1)
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%-d %b %Y, %-I:%M %p IST")
    # Latest day with Adjust data, for the banner
    last = ""
    if "daily" in raw:
        rows = list(csv.reader(io.StringIO(raw["daily"]["text"])))
        last = max((r[0] for r in rows[1:] if r), default="")
    data_js = json.dumps(raw, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    missing = [n for n in ADJUST + GA if n not in raw]
    note = f"Snapshot refreshed {stamp}" + (f" · Adjust data up to {last}" if last else "")
    if missing:
        note += " · not in this snapshot: " + ", ".join(missing)
    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>TukTuki User Behaviour</title>
<style>{THEME}</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script>window.__DASH_RAW = {data_js};</script>
<script>{SHIM}</script>
</head>
<body>
<div class="snap">{html.escape(note)}</div>
<div id="dash-root">
{page}
</div>
</body>
</html>
"""
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    open(os.path.join(ROOT, "docs", ".nojekyll"), "w").close()
    print(f"built docs/index.html ({len(out)//1024} KB); {note}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        build()
    elif len(sys.argv) == 5 and sys.argv[1] == "merge":
        merge(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
