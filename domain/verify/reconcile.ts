/**
 * Proves the domain model against Aspen's feeds.
 *
 * Runs on the recorded fixtures by default so it is deterministic and works off-season. Pass
 * `--live` to re-fetch and catch upstream drift: a renamed pod, a new lift, a difficulty label
 * we do not handle. That is the check worth running on a schedule, because the failure it catches
 * is silent — the app keeps answering, just about a mountain that has moved.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { POD_IDS, OFFICIAL_POD_NAME, classifyGroomingGroup } from '../src/pod.js';
import { ACCESS_EDGES, KNOWN_ACCESS_GAPS, RETIRED_ENTRIES } from '../src/catalog.js';
import { maxDifficultyOf, toDifficulty } from '../src/conditions.js';
import type { Run, FeedDifficulty } from '../src/conditions.js';
import type { PodId } from '../src/pod.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, '..', '..');

const GROOMING_URL =
  'https://www.aspensnowmass.com/AspenSnowmass/GroomingReport/Feed?mountain=Snowmass';
const LIFT_URL =
  'https://www.aspensnowmass.com/AspenSnowmass/LiftStatus/Feed?mountain=Snowmass&areas=&isSummer=False';

interface FeedTrail {
  name: string;
  difficulty: string;
  isOpen: boolean;
  isDayOpen: boolean;
  isGroomed: boolean;
}
interface FeedArea {
  name: string;
  isGatedTerrain: boolean;
  trails: FeedTrail[];
}
interface FeedLift {
  liftName: string;
  area: string;
  status: string;
  elevationGainFeet: string;
}

const live = process.argv.includes('--live');

const load = async (url: string, fixture: string): Promise<unknown> => {
  if (!live) {
    return JSON.parse(readFileSync(join(HERE, '..', 'fixtures', fixture), 'utf8'));
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return res.json();
};

const failures: string[] = [];
const check = (ok: boolean, label: string, detail = ''): void => {
  if (ok) {
    console.log(`  ok    ${label}`);
    return;
  }
  failures.push(`${label}${detail ? ` - ${detail}` : ''}`);
  console.log(`  FAIL  ${label}${detail ? ` - ${detail}` : ''}`);
};

const grooming = (await load(GROOMING_URL, 'grooming-feed.2026-08-22.json')) as {
  areas: FeedArea[];
};
const liftFeed = (await load(LIFT_URL, 'lift-status.2026-08-22.json')) as {
  liftStatuses: FeedLift[];
};

console.log(`\nSnowmass domain reconciliation  (${live ? 'LIVE' : 'fixtures'})\n`);

// 1. Every grooming group is one the model knows about.
console.log('Pod vocabulary');
const seenPods = new Set<PodId>();
const unrecognized: string[] = [];
for (const area of grooming.areas) {
  const group = classifyGroomingGroup(area.name);
  if (group.kind === 'pod') seenPods.add(group.podId);
  if (group.kind === 'unrecognized') unrecognized.push(area.name);
}
check(unrecognized.length === 0, 'every grooming group classifies', unrecognized.join(', '));
const missingPods = POD_IDS.filter((id) => !seenPods.has(id));
check(missingPods.length === 0, 'all eleven pods present in the feed', missingPods.join(', '));

// 2. Runs.
console.log('\nRuns');
const runs: Run[] = [];
const nameCount = new Map<string, number>();
const unknownDifficulties = new Set<string>();
const gated: string[] = [];
const KNOWN_DIFFICULTIES = [
  'beginner',
  'intermediate',
  'advanced',
  'expert',
  'extreme',
  'terrain-park',
] as const;

for (const area of grooming.areas) {
  const group = classifyGroomingGroup(area.name);
  if (area.isGatedTerrain) gated.push(area.name);
  if (group.kind !== 'pod') continue;
  for (const trail of area.trails) {
    nameCount.set(trail.name, (nameCount.get(trail.name) ?? 0) + 1);
    const known = KNOWN_DIFFICULTIES.includes(trail.difficulty as FeedDifficulty);
    if (!known) unknownDifficulties.add(trail.difficulty);
    runs.push({
      name: trail.name,
      pod: group.podId,
      feedDifficulty: trail.difficulty as FeedDifficulty,
      difficulty: known ? toDifficulty(trail.difficulty as FeedDifficulty) : null,
      open: trail.isOpen,
      openToday: trail.isDayOpen,
      groomed: trail.isGroomed,
    });
  }
}
const dupes = [...nameCount].filter(([, n]) => n > 1).map(([n]) => n);
check(
  dupes.length === 0,
  'run names are unique mountain-wide, so a run implies its pod',
  dupes.join(', '),
);
check(
  unknownDifficulties.size === 0,
  'every difficulty label maps',
  [...unknownDifficulties].join(', '),
);
console.log(
  `        ${runs.length} pod runs across ${seenPods.size} pods; gated groups: ${gated.join(', ')}`,
);

// 3. The retired crosswalk added nothing the feed does not already carry (ADR-0001).
console.log('\nRetired crosswalk (docs/adr/0001)');
const csvPath = join(REPO, 'backend', 'snowmass_run_crosswalk.csv');
let csvRows: { pod: string; run: string; difficulty: string }[] = [];
try {
  csvRows = readFileSync(csvPath, 'utf8')
    .split(/\r?\n/)
    .slice(1)
    .filter((line) => line.trim().length > 0)
    .map((line) => {
      const [pod = '', run = '', difficulty = ''] = line.split(',');
      return { pod: pod.trim(), run: run.trim(), difficulty: difficulty.trim() };
    });
} catch {
  console.log('  skip  crosswalk already deleted');
}

if (csvRows.length > 0) {
  // NUL delimiter: it cannot occur in a pod or run name, so the composite key is unambiguous.
  const key = (pod: string, run: string): string => `${pod}\u0000${run}`;
  const byPair = new Map(runs.map((r) => [key(OFFICIAL_POD_NAME[r.pod], r.name), r]));
  const orphans = csvRows.filter((r) => !byPair.has(key(r.pod, r.run)));
  check(
    orphans.length === 0,
    `all ${csvRows.length} crosswalk rows are present in the feed`,
    orphans.map((o) => `${o.pod}/${o.run}`).join(', '),
  );
  const LABEL: Record<string, string> = {
    beginner: 'Beginner',
    intermediate: 'Intermediate',
    advanced: 'Advanced',
    expert: 'Expert',
    extreme: 'Extreme Terrain',
    'terrain-park': 'Terrain Park',
  };
  const diffMismatch = csvRows.filter((r) => {
    const run = byPair.get(key(r.pod, r.run));
    return run !== undefined && LABEL[run.feedDifficulty] !== r.difficulty;
  });
  check(
    diffMismatch.length === 0,
    'crosswalk difficulties agree with the feed',
    diffMismatch.map((m) => m.run).join(', '),
  );
}

// 4. Lift access.
console.log('\nLift access');
const feedLifts = new Set(liftFeed.liftStatuses.map((l) => l.liftName.trim()));
const edgeLifts = new Set(ACCESS_EDGES.map((e) => e.lift as string));
const unmappedLifts = [...feedLifts].filter((l) => !edgeLifts.has(l));
const phantomLifts = [...edgeLifts].filter((l) => !feedLifts.has(l));
check(
  unmappedLifts.length === 0,
  'every lift in the feed has an access edge',
  unmappedLifts.join(', '),
);
check(phantomLifts.length === 0, 'every access edge names a real lift', phantomLifts.join(', '));

const podsWithAccess = new Set(ACCESS_EDGES.map((e) => e.pod));
const unexplained = POD_IDS.filter(
  (id) => !podsWithAccess.has(id) && KNOWN_ACCESS_GAPS[id] === undefined,
);
check(
  unexplained.length === 0,
  'every pod has an access edge or a declared gap',
  unexplained.join(', '),
);
for (const [pod, why] of Object.entries(KNOWN_ACCESS_GAPS)) {
  console.log(`        gap: ${pod} - ${why}`);
}

// 5. Fetched difficulty vs the retired hand-authored values (ADR-0002).
console.log('\nDifficulty: fetched vs retired hand-authored (docs/adr/0002)');
/**
 * What the retired catalog would actually have used for each pod, resolved through the broken
 * OFFICIAL_POD_TO_ID map -- so Cirque reads Hanging Valley's row and Pipes/Parks reads the row
 * labelled "Cirque". This is the value the difficulty gate ran on, not the value anyone intended.
 */
const AUTHORED: Record<PodId, string> = {
  'alpine-springs': 'blue',
  'big-burn': 'black',
  campground: 'black',
  cirque: 'double-black',
  'coney-express': 'blue',
  'elk-camp': 'green',
  'hanging-valley': 'double-black',
  'high-alpine': 'black',
  'pipes-parks': 'black',
  'sams-knob': 'double-black',
  'two-creeks': 'blue',
};
let disagreements = 0;
for (const id of POD_IDS) {
  const podRuns = runs.filter((r) => r.pod === id);
  if (podRuns.length === 0) continue;
  const actual = maxDifficultyOf(podRuns);
  const authored = AUTHORED[id];
  const name = OFFICIAL_POD_NAME[id].padEnd(16);
  const agree = authored === actual;
  if (!agree) disagreements += 1;
  console.log(
    `  ${agree ? 'same ' : 'DIFF '} ${name} feed=${String(actual).padEnd(13)} authored=${authored}`,
  );
}
console.log(
  `        ${disagreements} of ${Object.keys(AUTHORED).length} pods: the gate ran on a value the feed contradicts`,
);

// 6. The retirement ledger accounts for all twelve old entries.
console.log('\nRetirement ledger');
check(RETIRED_ENTRIES.length === 12, 'all twelve retired entries recorded');
const resolved = RETIRED_ENTRIES.flatMap((e) => (e.resolvesTo === null ? [] : [e.resolvesTo]));
check(
  new Set(resolved).size === resolved.length,
  'no two retired entries resolve to the same pod',
  'a collision here is the original bug',
);

if (failures.length > 0) {
  console.error(
    `\n${failures.length} check(s) failed:\n${failures.map((f) => `  - ${f}`).join('\n')}\n`,
  );
  process.exit(1);
}
console.log('\nAll checks passed.\n');
