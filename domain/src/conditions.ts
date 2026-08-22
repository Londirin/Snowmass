/**
 * What is true of the mountain today. Always fetched, never stored as a constant.
 */
import type { PodAccess } from './access.js';
import type { LiftId } from './access.js';
import type { PodId } from './pod.js';
import type { Field, SourceHealth, Sourced, Timestamp } from './provenance.js';

/** The feed's own difficulty vocabulary, verbatim. Six values, all observed live. */
export type FeedDifficulty =
  | 'beginner'
  | 'intermediate'
  | 'advanced'
  | 'expert'
  | 'extreme'
  | 'terrain-park';

/**
 * Skiable difficulty, ordered. `terrain-park` is excluded because it is not a point on this
 * scale — a park run is not harder than an expert chute, it is a different question — and
 * folding it in is what let a park pod be labelled `black` and admitted by a difficulty gate.
 */
export type Difficulty = 'green' | 'blue' | 'black' | 'double-black' | 'extreme';

export const DIFFICULTY_ORDER: Record<Difficulty, number> = {
  green: 0,
  blue: 1,
  black: 2,
  'double-black': 3,
  extreme: 4,
};

export const toDifficulty = (feed: FeedDifficulty): Difficulty | null => {
  switch (feed) {
    case 'beginner':
      return 'green';
    case 'intermediate':
      return 'blue';
    case 'advanced':
      return 'black';
    case 'expert':
      return 'double-black';
    case 'extreme':
      return 'extreme';
    case 'terrain-park':
      return null;
  }
};

export interface Run {
  /** Exactly as the grooming feed spells it. Unique across the mountain — verified 2026-08-22. */
  readonly name: string;
  readonly pod: PodId;
  readonly difficulty: Difficulty | null;
  readonly feedDifficulty: FeedDifficulty;
  readonly open: boolean;
  /** The feed's `isDayOpen` — open for today specifically, as against open for the season. */
  readonly openToday: boolean;
  readonly groomed: boolean;
}

export type LiftStatus = 'open' | 'closed' | 'on-hold';

export interface Lift {
  readonly id: LiftId;
  readonly status: LiftStatus;
  /** Verbatim, so an unmapped status string can be reported rather than coerced to `closed`. */
  readonly statusRaw: string;
  readonly verticalFt: number;
  readonly rideMinutes: number;
  readonly hoursOfOperation: string;
}

/**
 * Snow state. None of this existed in the previous model — half the original concept.
 *
 * Base depth comes from a SNOTEL station, new snow from the Aspen station page. They are
 * different instruments at different elevations, so they stay separate fields with separate
 * provenance rather than being blended into one "snow" number.
 */
export interface SnowState {
  /** Settled base depth, inches. */
  readonly baseDepthIn: Field<number>;
  readonly newSnow24hIn: Field<number>;
  readonly newSnow72hIn: Field<number>;
  /** Snow water equivalent, inches — density, which decides whether new snow skis deep or heavy. */
  readonly sweIn: Field<number>;
  /**
   * Whether the base is thin enough that rocks are the binding constraint. Derived, not fetched,
   * and it needs a per-pod term: a foot covers a groomed cruiser and does not cover Cirque.
   */
  readonly thinCoverRisk: Field<number>;
}

/** One pod's fetched state today. */
export interface PodConditions {
  readonly podId: PodId;
  readonly runs: readonly Run[];
  readonly access: PodAccess;
  /** Derived from `runs` on every fetch — never stored. See docs/adr/0002. */
  readonly maxDifficulty: Sourced<Difficulty | null>;
  readonly openRunCount: number;
  readonly groomedRunCount: number;
  /** Aspen's `isGatedTerrain` on the grooming group. */
  readonly gated: boolean;
}

/** Everything fetched for one moment, with per-source health so the UI can say what it is missing. */
export interface MountainConditions {
  readonly fetchedAt: Timestamp;
  readonly pods: ReadonlyMap<PodId, PodConditions>;
  readonly lifts: readonly Lift[];
  readonly snow: SnowState;
  readonly health: {
    readonly grooming: SourceHealth;
    readonly lifts: SourceHealth;
    readonly station: SourceHealth;
    readonly snotel: SourceHealth;
    readonly forecast: SourceHealth;
  };
  /**
   * Anything the feed said that the model did not recognize — a renamed pod, an unmapped
   * difficulty or lift status. Carried to the response so it is visible without reading logs.
   */
  readonly diagnostics: readonly string[];
}

/** The maximum difficulty actually present in a run list, ignoring park runs. */
export const maxDifficultyOf = (runs: readonly Run[]): Difficulty | null =>
  runs.reduce<Difficulty | null>((max, run) => {
    if (run.difficulty === null) return max;
    if (max === null) return run.difficulty;
    return DIFFICULTY_ORDER[run.difficulty] > DIFFICULTY_ORDER[max] ? run.difficulty : max;
  }, null);
