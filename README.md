# TukTuki User Behaviour (public snapshot)

A phone-friendly copy of the "Tuktuki User Behaviour" Claude dashboard, published with GitHub Pages.

- `source/dashboard.html` – the dashboard page copied from the Claude artifact
- `data/` – Adjust report results (CSV) and Google Analytics files (JSON)
- `build.py build` – writes `docs/index.html`; `build.py merge <dataset> <new.csv> <key>` merges fresh rows
- A daily Claude task on the Mac refreshes the data, rebuilds and pushes.
