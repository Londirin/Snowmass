# Domain model

The engine's types, ahead of the TypeScript port. `CONTEXT.md` at the repo root is the glossary;
`docs/adr/0001` and `0002` record why this shape and not the old one.

```bash
npm --prefix domain install
npm --prefix domain run typecheck
npm --prefix domain run verify           # against recorded fixtures — deterministic, works off-season
npm --prefix domain run verify -- --live # against Aspen, to catch upstream drift
```

## The shape, in one paragraph

A pod's identity is the name Aspen's grooming feed uses for it, and that feed tags every run with
its pod on every fetch, so nothing translates between namespaces. What a pod *is* physically
(aspect, elevation, tree cover, exposure) lives in a terrain profile that changes per season.
What is *true of it today* (open runs, grooming, lift access, snow) is fetched every time and
never stored. Difficulty sits in the second group, not the first, because the feed is
authoritative for it and the hand-authored values were wrong for nine of eleven pods.

Every terrain-profile field is a `Field<T>` carrying where it came from — `fetched`, `surveyed`,
`estimated` with a stated basis, or `unsourced`. `unsourced` is a real state the scorer must
decide about, which is what stops an unmeasured attribute from being quietly defaulted into a
number shown to a skier.

## What is populated, and what is not

Fetched and real today: the eleven pod names, run-to-pod membership, per-run difficulty and
status, park and gated flags, the nineteen lifts with vertical and ride time, and eighteen of the
nineteen lift-to-pod access edges.

Not sourced yet, and deliberately left empty rather than guessed: **aspect, elevation range, tree
cover, and exposure for all eleven pods.** These need the trail map and a DEM. They are also the
inputs to most of the scoring physics, so this is the next data task, not a loose end.

Also open: how you reach Hanging Valley and Pipes/Parks. Neither has a lift filed under its own
name, so their access resolves to `unknown` rather than `no-access` — see `KNOWN_ACCESS_GAPS`.

## The retired files are still on disk on purpose

`backend/pods_snowmass_v1.json` and `backend/snowmass_run_crosswalk.csv` are superseded, but the
Python engine is the parity oracle for the port and still needs to run its 18 tests. They go when
the port passes parity, not before. `RETIRED_ENTRIES` in `src/catalog.ts` records what each of
the twelve old entries was, so the reconciliation is auditable rather than a silent deletion.
