// Run inside the logged-in Tuktuki admin panel tab
// (https://adminpanneloftuktuki-236950728917.asia-south1.run.app) with the browser's javascript tool.
// Step 1: set window.__TT_FROM / window.__TT_TO (YYYY-MM-DD, IST days) and window.__TT_WINDOWS
//         (array of [start,end]) before pasting this file, or edit the defaults below.
// Step 2: paste this whole file; it starts the pulls in the background and returns 'started'.
// Step 3: poll `window.__TT.status` with short calls until it is 'done' (or 'error').
// Step 4: read `window.__TT.out.daily`, `.series`, `.windows` (CSV strings). Large returns are saved
//         to a tool-results file by the harness; read them from there.
(() => {
  const API = 'https://adminpannelbackend-236950728917.asia-south1.run.app/api/dashboard/';
  const tok = localStorage.getItem('auth_token');
  const F = window.__TT_FROM, T = window.__TT_TO, WINS = window.__TT_WINDOWS || [];
  const S = (window.__TT = { status: 'running', step: 'start', errors: [], out: {} });
  if (!tok) { S.status = 'error'; S.errors.push('not logged in (no auth_token)'); return 'not logged in'; }
  if (!F || !T) { S.status = 'error'; S.errors.push('set __TT_FROM/__TT_TO'); return 'missing dates'; }
  const days = []; for (let t = Date.parse(F + 'T00:00:00Z'); t <= Date.parse(T + 'T00:00:00Z'); t += 864e5) days.push(new Date(t).toISOString().slice(0, 10));
  const get = async (p, tries = 3) => {
    for (let a = 0; a < tries; a++) {
      try {
        const ctl = new AbortController(); const tm = setTimeout(() => ctl.abort(), 120000);
        const r = await fetch(API + p, { headers: { Authorization: `Bearer ${tok}` }, signal: ctl.signal }); clearTimeout(tm);
        if (r.status === 401 || r.status === 403) throw new Error('auth ' + r.status);
        const j = await r.json(); if (!Array.isArray(j.data)) throw new Error(r.status + ' ' + JSON.stringify(j).slice(0, 120));
        return j.data;
      } catch (e) { if (a === tries - 1) throw e; await new Promise((r) => setTimeout(r, 2000)); }
    }
  };
  const csvCell = (v) => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const num = (v) => { if (v == null || v === '') return ''; const n = +v; return Number.isFinite(n) ? (Number.isInteger(n) ? String(n) : String(Math.round(n * 10000) / 10000)) : ''; };
  (async () => {
    try {
      // ---- daily totals (one call per report, whole span) ----
      S.step = 'daily';
      const f1 = `from=${F}&to=${T}`, f2 = `fromDate=${F}&toDate=${T}`;
      const calls = { dau: `dau?view=day&${f1}`, pft: `dau?view=day&metric=paid_free_total&${f1}`, life: `dau?view=day&metric=lifetime_paid_dau&${f1}` };
      for (const m of ['total_viewers', 'avg_watch_time', 'avg_videos', 'completion_rate']) calls['eng_' + m] = `engagement?view=day&metric=${m}&${f1}`;
      for (const m of ['total_revenue', 'total_payers', 'avg_paid_amount', 'bucket2_sales', 'conversion_rate']) calls['rev_' + m] = `revenue?view=day&metric=${m}&${f1}`;
      for (const m of ['downloads', 'episodeViews', 'razorpayRevenue', 'admobRevenue', 'admobImpressions']) calls['perf_' + m] = `performance-report?metric=${m}&view=day&${f2}`;
      calls.ie = `install-engagement?view=day&${f2}`;
      for (const m of ['total_paid', 'no_of_payers', 'avg_spend']) calls['ir_' + m] = `install-revenue?view=day&metric=${m}&${f2}`;
      for (const ty of ['d1', 'd7', 'd30']) calls['ret_' + ty] = `retention?view=day&type=${ty}&${f2}`;
      for (const ty of ['weekly7', 'weekly14', 'weekly21', 'day15', 'month30']) calls['sub_' + ty] = `subscription-retention?view=day&type=${ty}&${f1}`;
      const A = {}; await Promise.all(Object.entries(calls).map(async ([k, p]) => { A[k] = await get(p); }));
      const TT = {}; const put = (d, k, v) => { (TT[d] = TT[d] || {})[k] = v; };
      for (const [k, arr] of Object.entries(A)) {
        const dated = arr.some((r) => /^\d{4}-\d\d-\d\d$/.test(String(r.label ?? r.report_date)));
        if (!dated && arr.length !== days.length) S.errors.push(`${k}: ${arr.length} rows for ${days.length} days, skipped`);
        if (!dated && arr.length !== days.length) continue;
        arr.forEach((r, i) => { const d = dated ? (r.label ?? r.report_date) : days[i];
          for (const [f, v] of Object.entries(r)) { if (f === 'label' || f === 'report_date') continue;
            const name = f === 'value' ? k : /^(ret_|sub_|dau|pft|ie|rev_bucket)/.test(k) ? k + '_' + f : f; put(d, name, v); } });
      }
      const cols = [...new Set(Object.values(TT).flatMap((o) => Object.keys(o)))].filter((c) => !/registered_and_visited|rev_bucket1/.test(c));
      S.out.daily = ['day,' + cols.join(','), ...Object.keys(TT).sort().map((d) => d + ',' + cols.map((c) => num(TT[d][c])).join(','))].join('\n');
      // ---- per-show daily ----
      S.step = 'series';
      const rows = []; const q = days.slice(); S.seriesDone = 0;
      const worker = async () => { while (q.length) { const d = q.shift();
        const data = await get(`engagement-report?metric=watchTime&fromDate=${d}&toDate=${d}`);
        for (const x of data) { if (x.city_name != null || x.state_name != null) continue;
          rows.push([d, x.series_name || '(unnamed)', x.category_name || '', +x.accessed_users, +x.total_views, (+x.total_watchtime_hours).toFixed(2)]); }
        S.seriesDone++; } };
      await Promise.all([...Array(6)].map(worker));
      S.out.series = ['day,series,category,viewers,views,hours', ...rows.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)).map((r) => r.map(csvCell).join(','))].join('\n');
      // ---- unique viewers for fixed windows (one at a time; >~3 months times out) ----
      S.step = 'windows'; const wr = [];
      for (const [a, b] of WINS) {
        try { const data = await get(`engagement-report?metric=watchTime&fromDate=${a}&toDate=${b}`, 2);
          for (const x of data) { if (x.city_name != null || x.state_name != null) continue; wr.push([a, b, x.series_name || '(unnamed)', x.category_name || '', +x.accessed_users, +x.total_views, (+x.total_watchtime_hours).toFixed(2)]); }
        } catch (e) { S.errors.push(`window ${a}..${b}: ${e.message}`); }
      }
      S.out.windows = ['start,end,series,category,viewers,views,hours', ...wr.map((r) => r.map(csvCell).join(','))].join('\n');
      S.status = 'done'; S.step = 'done';
    } catch (e) { S.status = 'error'; S.errors.push(S.step + ': ' + e.message); }
  })();
  return 'started';
})();
