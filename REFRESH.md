# Daily refresh — Tuktuki User Behaviour

Runs Mon–Fri at ~10:30 AM IST as a Claude scheduled task, or whenever Kshitij asks for a refresh.
Whichever runs first that day does the work; the other skips. Follow these steps in order.
The runbook and the two scripts in `tools/` are also kept in the dashboard store (`refresh/tools`), so a run works even if this repo can't be pushed.

Dashboard (Claude artifact): https://claude.ai/artifact/SCeuwRSPoiBG7gkpih9mZM
Public copy: this repo → GitHub Pages (`docs/index.html`).

## 0. Skip check and lock (always first, keep it cheap)
- IST today: `TZ=Asia/Kolkata date +%F`. yesterday = today − 1 day.
- Read the dashboard store doc `refresh/state` (ArtifactData `get`, collection `refresh`, doc_id `state`).
  Fields: `date` (IST day of the last finished refresh), `status` (`full` / `partial`), `at`, `by` (`scheduled` / `manual`),
  `lock` (ISO time a run started, or null).
- **Scheduled run**: if `date` == today and `status` == `full` → end silently (a manual refresh already ran).
  If `lock` is less than 90 minutes old → end silently (a refresh is running).
- **Manual run** (Kshitij asked): always run, even if one already ran today.
- Otherwise `update` the doc (pin `if_version`) with `lock` = now, then continue.

## 1. Adjust (live on the dashboard; refresh the repo copy)
The dashboard's Adjust sections query Adjust live and already run "up to and including yesterday".
For the repo copy: for each dataset `daily, events, cohorts, channels, backcamp, purchases, paycohort, paychan`,
read `datasets/<id>` from the dashboard store, run its `source.args.report_question` with the Adjust connector
(`reporting_tool`), take the CSV text (unwrap `{"result": "..."}` if present) and overwrite `data/<id>.csv`.
If an answer is not a CSV table with a `day`/`month`/`week` column, keep the old file and note it.

## 2. Tuktuki admin panel (copy refreshed here — the dashboard can't call it)
Needs Kshitij's Mac online with the Claude desktop app and the admin panel logged in, in the built-in browser.
0. Base files: the dashboard is the source of truth. For `admin_daily`, `series_daily`, `series_windows` read
   `datasets/<id>` → `source.url` (`/_blob/<asset id>`) and download each with Artifact `read` (`path` = the asset id)
   into `data/admin/<id>.csv` (overwrite the repo copy).
1. `python3 tools/admin_merge.py plan` → JSON `{from, to, windows}` (re-pulls the last 45 days + unique-viewer windows).
2. Browser tools (`mcp__remote-devices__Claude_Browser__*`): find the tab on
   `https://adminpanneloftuktuki-236950728917.asia-south1.run.app` (open `/dashboard` if none). If it shows the
   sign-in page, stop this step and report "admin panel logged out" — never type a password.
3. javascript_tool: `window.__TT_FROM='<from>'; window.__TT_TO='<to>'; window.__TT_WINDOWS=<windows JSON>;`
   then run the full text of `tools/admin_fetch.js`. Poll `({s: window.__TT.status, step: window.__TT.step, n: window.__TT.seriesDone, e: window.__TT.errors})`
   with short calls (each under ~40 s) until `done` or `error`.
4. Read `window.__TT.out.daily`, `window.__TT.out.series`, `window.__TT.out.windows` one per call. Big results are
   saved by the harness to a tool-results file: extract the string from there with Python, write `/tmp/ad.csv`,
   `/tmp/se.csv`, `/tmp/wi.csv`.
5. `python3 tools/admin_merge.py merge /tmp/ad.csv /tmp/se.csv /tmp/wi.csv`
6. Upload the three files in `data/admin/` to the dashboard as assets (Artifact publish, `asset: true`, url above),
   then `update` `datasets/admin_daily`, `datasets/series_daily`, `datasets/series_windows`: new `source.url` and
   `source.name`, `updated: {at, by: "Claude scheduled refresh (admin panel)"}`, `edit: {via: "claude", at}`.
   Then delete the asset each dataset pointed to before (only after the update succeeded).

## 3. Google Analytics
- Daily GA comes from the BigQuery export (`tuktuki-54fa9`, dataset `analytics_495378590`) and is live on the dashboard
  once wired — nothing to refresh there. For the repo copy, if `datasets/ga_daily*` exist, run each one's SQL with
  `{{start}}` = 2026-11-17 and `{{end}}` = yesterday via the BigQuery connector and save `data/ga/<id>.csv`.
- The monthly GA copy (`data/ga/*.json`, age/gender/interests) is not refreshed automatically.

## 4. Rebuild and push the repo
1. Copy the dashboard page: ArtifactData `get` `files/index.html` → its `text` → `source/dashboard.html`.
2. `python3 build.py build`
3. Commit `data/ source/ docs/` with message `Daily data refresh <IST date>` and push to `main`.
   If the push is refused, say so (the Claude GitHub App must be installed on the repo) — the dashboard is still updated.

## 5. Finish
`update` `refresh/state`: `date` = today, `at` = now, `by` = scheduled/manual, `lock` = null, `status` =
`full` if steps 1, 2 and 4 all succeeded, else `partial`, and `notes` = one line on anything that failed.
Send Kshitij a short message (SendUserMessage): admin data through <date>, what refreshed, anything that failed, then
ADMIN PANEL INSIGHTS (always, from data/admin/, after removing the broken days the dashboard leaves out: watch time
> 300 min per viewer, and performance-report days whose episode views are > 4x the surrounding fortnight's median
AND downloads > 2x that day's DAU):
- Yesterday vs the 7-day average before it: DAU, share of DAU who watched, minutes and episodes per viewer,
  subscription revenue, AdMob revenue and eCPM (₹ per 1,000 impressions), payers, paid DAU — call out moves over ~10%.
- Last 7 days vs the 7 before: same measures in one short table.
- Shows: top 3 by watch hours yesterday, and the biggest 3 gainers and 3 losers in watch hours (last 7 vs previous 7 days).
- Renewals: weekly pack renewed-by-day-7 for the latest purchase days old enough (7+ days), vs the previous week.
- New users: share who watched on day 0 and who watched again on day 1 (latest mature days) vs the week before.
- 2–3 one-line "what to do" points that follow from the moves (ad load vs eCPM, paid DAU trend, a fading or rising show).
Keep it phone-readable.
A scheduled run that skipped sends nothing.

Hard rules: read-only on the admin panel, Adjust, GA and BigQuery. Never type passwords. Never delete repo history.
