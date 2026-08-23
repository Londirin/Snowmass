import { maxDifficultyOf, toDifficulty } from '../conditions.js';
import type { Difficulty, FeedDifficulty, Run } from '../conditions.js';
import { classifyGroomingGroup } from '../pod.js';
import type { PodId } from '../pod.js';
import { timestamp } from '../provenance.js';
import type { SourceHealth, Timestamp } from '../provenance.js';

export interface GroomingFeedPayload {
  areas: readonly {
    name: string;
    isGatedTerrain: boolean;
    trails: readonly {
      name: string;
      difficulty: string;
      isOpen: boolean;
      isDayOpen: boolean;
      isGroomed: boolean;
    }[];
  }[];
}

export interface ParsedGrooming {
  readonly runs: readonly Run[];
  readonly pods: ReadonlyMap<PodId, readonly Run[]>;
  readonly gated: ReadonlySet<PodId>;
  readonly maxDifficulty: ReadonlyMap<PodId, Difficulty | null>;
  readonly diagnostics: readonly string[];
  readonly health: SourceHealth;
}

const URL = 'https://www.aspensnowmass.com/AspenSnowmass/GroomingReport/Feed?mountain=Snowmass';
const DIFFICULTIES = new Set<FeedDifficulty>([
  'beginner', 'intermediate', 'advanced', 'expert', 'extreme', 'terrain-park',
]);

/** Parse Aspen's grooming vocabulary without inventing runs or pod identities. */
export const parseGroomingFeed = (
  payload: GroomingFeedPayload,
  fetchedAt: Timestamp = timestamp(new Date().toISOString()),
): ParsedGrooming => {
  const diagnostics: string[] = [];
  const runs: Run[] = [];
  const pods = new Map<PodId, Run[]>();
  const gated = new Set<PodId>();

  for (const area of payload.areas) {
    const group = classifyGroomingGroup(area.name);
    if (group.kind === 'unrecognized') {
      diagnostics.push(`Unrecognized grooming group: ${group.name}`);
      continue;
    }
    if (group.kind === 'non-ski') continue;
    if (area.isGatedTerrain) gated.add(group.podId);
    const podRuns = pods.get(group.podId) ?? [];
    for (const trail of area.trails) {
      const known = DIFFICULTIES.has(trail.difficulty as FeedDifficulty);
      if (!known) diagnostics.push(`Unrecognized difficulty "${trail.difficulty}" on run "${trail.name}"`);
      const run: Run = {
        name: trail.name,
        pod: group.podId,
        feedDifficulty: trail.difficulty as FeedDifficulty,
        difficulty: known ? toDifficulty(trail.difficulty as FeedDifficulty) : null,
        open: trail.isOpen,
        openToday: trail.isDayOpen,
        groomed: trail.isGroomed,
      };
      runs.push(run);
      podRuns.push(run);
    }
    pods.set(group.podId, podRuns);
  }

  const maxDifficulty = new Map<PodId, Difficulty | null>();
  for (const [pod, podRuns] of pods) maxDifficulty.set(pod, maxDifficultyOf(podRuns));
  return { runs, pods, gated, maxDifficulty, diagnostics, health: { status: 'live', fetchedAt } };
};

export const groomingSource = (fetchedAt: Timestamp): SourceHealth => ({
  status: 'live', fetchedAt,
});

export { URL as GROOMING_FEED_URL };
