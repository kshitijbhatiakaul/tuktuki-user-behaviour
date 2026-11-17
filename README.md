# TukTuki User Behaviour (public snapshot)

A phone-friendly copy of the "Tuktuki User Behaviour" Claude dashboard, published with GitHub Pages.

- `source/dashboard.html` – the dashboard page copied from the Claude artifact
- `data/` – Adjust report results (CSV) and Google Analytics files (JSON)
- `build.py build` – writes `docs/index.html`; `build.py merge <dataset> <new.csv> <key>` merges fresh rows
- `data/admin/` – Tuktuki admin panel copy (daily totals, viewing by show, unique viewers per window)
- `tools/` – admin panel fetch script and merge helper
- `REFRESH.md` – the daily refresh runbook (Mon–Fri ~10:30 AM IST Claude scheduled task; skipped if a manual refresh already ran that day)
