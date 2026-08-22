# Snowmass run recommender — working notes for agents

Recommends which pod of Snowmass to ski right now from live grooming, lift status, snow, and weather.

## Commands

```bash
npm --prefix domain install       # node_modules is gitignored; run this first in a fresh worktree
npm --prefix domain run typecheck # tsc --noEmit, strict + exactOptionalPropertyTypes
npm --prefix domain test          # node test runner via tsx
npm --prefix domain run verify    # reconciles the domain model against recorded Aspen fixtures
```

The Python backend is a parity oracle, not production. It needs 3.11+ (`uv venv --python 3.12`);
the system 3.9 fails test collection. Baseline is 18/18.

## Invariants — these are the bugs this rebuild exists to fix

1. **Never invent a value.** A missing cell, an unreachable source, or an unmapped label becomes
   `null` plus a diagnostic — never a plausible-looking number. The original defect was a parser
   that returned a fabricated `5.0` for 24-hour SWE from a page containing no data at all.
2. **The grooming feed is authoritative for pod identity.** Every run arrives tagged with its pod.
   Use `classifyGroomingGroup` in `domain/src/pod.ts`. Never add a second pod-name mapping, and
   never revive `snowmass_run_crosswalk.csv` or `OFFICIAL_POD_TO_ID` — both are superseded and
   both were wrong. See `docs/adr/0001`.
3. **Never join a lift to a pod on the lift feed's `area` field.** That field is a coarser, different
   partition — the Cirque Surface Lift is filed under Big Burn. Go through `ACCESS_EDGES`.
4. **Difficulty is fetched, never stored.** Derive it from the run list every time. See `docs/adr/0002`.
5. Off-season (roughly May–October) every run reads closed and ungroomed and the weather stations
   report nothing. That is correct data. Test against recorded fixtures, never against live state.

`CONTEXT.md` is the glossary — use its words. `docs/adr/` records why the model is shaped this way.
