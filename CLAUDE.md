# Snowmass run recommender

Charter for the v1 rebuild: `~/Claude/Projects/command-center/prompts/snowmass-run-recommender-rebuild.md`.
Read it once at session start. This file holds only what must survive compaction.

## Deploys

Local git identity is `Londirin <72635659+Londirin@users.noreply.github.com>` and must stay that way.
Vercel silently rejects builds from unknown commit authors — a green push is not a green deploy.
The machine's global identity (`jacob@glprelief.com`) is the blocked one.

## The legacy Python engine

It is the parity oracle for the TypeScript port, not production code. It needs Python 3.11+:
`uv venv --python 3.12`. The system 3.9 fails test collection on a `datetime | None` annotation.
Baseline is 18/18 passing — if that changes, the oracle moved and the port's test vectors are stale.

## Live data sources — the params are load-bearing

Both Aspen feeds return misleading responses when called without query params. This is the single
easiest way to conclude an endpoint is dead when it isn't:

- Grooming: `.../AspenSnowmass/GroomingReport/Feed?mountain=Snowmass` — bare, returns `{"areas": []}`
- Lifts: `.../AspenSnowmass/LiftStatus/Feed?mountain=Snowmass&areas=&isSummer=False` — bare, 302s to an error page
- Station: `https://weather.aspensnowmass.com/snowmass-summary.html` — the old `SNOWMASS-SUMMARY.HTM` is a 404

Off-season (roughly May–October) every run reads closed and ungroomed. That is correct data, not a bug.
Test against recorded fixtures, never against whatever the mountain happens to be doing today.

## Pod identity — settled, see docs/adr/0001

The grooming feed is authoritative for what a pod is and which runs are in it. It tags every run
with its pod on every fetch, so nothing translates between namespaces. `pods_snowmass_v1.json`,
`snowmass_run_crosswalk.csv`, `OFFICIAL_POD_TO_ID`, and `RUN_ALIASES` are all superseded — the
crosswalk was a derived snapshot of the feed carrying no information the feed lacks (130/130 rows
identical, verified 2026-08-22). They stay on disk only until the port clears parity against the
Python oracle.

Eleven ski pods, plus three non-ski groups in the same array (Uphill Routes, Hike/XC Bike Trails,
Lost Forest) that must be dropped before scoring. `npm --prefix domain run verify` re-proves all
of this against fixtures; add `-- --live` to catch Aspen renaming something.

Difficulty is fetched, never stored: the retired hand-authored `difficulty_max` contradicted the
feed for 9 of 11 pods, 7 of them in the direction that admits a skier to terrain above their cap.

## Next.js / Tailwind

Unlayered CSS beats `@layer utilities` — `:where()` will not win a specificity fight.
`pkill -f "next start"` does not kill the dev server; find the pid with `lsof`.

## Web access

All browsing goes through the `/browse` skill. The daemon is shared and persistent, so clear logs and
isolate tabs before treating console or network output as evidence about a page.
