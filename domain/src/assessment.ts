/**
 * The join: terrain profile × today's conditions × forecast × the skier's constraints.
 *
 * This is the record the old model could not produce, because conditions never reached scoring.
 */
import type { PodId } from './pod.js';
import type { Difficulty } from './conditions.js';
import type { Provenance, Timestamp } from './provenance.js';

export interface SkierConstraints {
  /** Hard gate. Nothing above this is recommended. */
  readonly maxDifficulty: Difficulty;
  readonly groomersOnly: boolean;
  readonly avoidMoguls: boolean;
  /** Weights, 0–2, 1 being neutral. */
  readonly preferTrees: number;
  readonly preferGroomers: number;
  readonly at: Timestamp;
  readonly horizonHours: number;
}

/** One named term of the score, so the number shown can be taken apart. */
export interface ScoreTerm {
  readonly name: string;
  readonly delta: number;
  /** Plain sentence for the UI. "Wind on an exposed north face at 22 mph." */
  readonly explanation: string;
  readonly source: Provenance;
}

export interface TimeWindow {
  readonly start: Timestamp;
  readonly end: Timestamp;
}

/**
 * How much of the model actually ran for this pod.
 *
 * A pod scored without snow data is not the same answer as one scored with it, and the skier
 * should be able to tell which they are looking at.
 */
export interface Confidence {
  readonly level: 'high' | 'medium' | 'low';
  /** Which inputs were missing or stale, named. */
  readonly gaps: readonly string[];
}

export interface PodAssessment {
  readonly podId: PodId;
  readonly score: number;
  readonly bestWindow: TimeWindow;
  readonly terms: readonly ScoreTerm[];
  readonly confidence: Confidence;
}

/**
 * Why a pod is not in the answer. Three different things the old model flattened into one string.
 *
 * `insufficient-data` is the one that did not exist before, and it is the point of the exercise:
 * a pod we cannot honestly score drops out saying so, rather than scoring on defaults.
 */
export type Exclusion =
  | {
      readonly podId: PodId;
      readonly kind: 'constraint';
      readonly reason: string;
    }
  | {
      readonly podId: PodId;
      readonly kind: 'conditions';
      readonly reason: string;
    }
  | {
      readonly podId: PodId;
      readonly kind: 'insufficient-data';
      readonly reason: string;
      readonly missing: readonly string[];
    };

export interface Recommendation {
  readonly generatedAt: Timestamp;
  readonly ranked: readonly PodAssessment[];
  readonly excluded: readonly Exclusion[];
  readonly confidence: Confidence;
}
