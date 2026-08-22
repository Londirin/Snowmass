/**
 * Where a value came from. Every number this app shows a skier carries one.
 *
 * The project's original defect was a hardcoded per-pod float presented as if it were today's
 * grooming report. Provenance makes that shape unrepresentable: a value and its origin travel
 * together, and a value without an origin cannot be constructed.
 */
export type Provenance =
  /** Read from a named source at a named time. */
  | {
      readonly kind: 'fetched';
      /** The exact URL including query params — the params are load-bearing on both Aspen feeds. */
      readonly url: string;
      /** Field path within the payload, e.g. `areas[].trails[].isGroomed`. */
      readonly field: string;
      readonly fetchedAt: Timestamp;
    }
  /** Read off an official map, dataset, or published table. Stable between seasons. */
  | {
      readonly kind: 'surveyed';
      /** What was read — "Aspen Snowmass winter trail map, 2025-26" or "USGS 3DEP 1m DEM". */
      readonly document: string;
      readonly surveyedOn: IsoDate;
      readonly note?: string | undefined;
    }
  /** Derived from a documented model term. Legitimate, but must say what it rests on. */
  | {
      readonly kind: 'estimated';
      /** The reasoning, in a sentence. "Tree cover from the ratio of glade runs to total runs." */
      readonly basis: string;
    };

/** ISO 8601 instant, UTC. */
export type Timestamp = string & { readonly __brand: 'Timestamp' };
/** ISO 8601 calendar date, `YYYY-MM-DD`. */
export type IsoDate = string & { readonly __brand: 'IsoDate' };

export const timestamp = (iso: string): Timestamp => iso as Timestamp;
export const isoDate = (iso: string): IsoDate => iso as IsoDate;

/** A value bound to its origin. */
export interface Sourced<T> {
  readonly value: T;
  readonly source: Provenance;
}

/**
 * A value we have not sourced yet.
 *
 * Deliberately not `undefined`: an unsourced field is a state the scorer has to make a decision
 * about — degrade the score's confidence, or exclude the pod with a stated reason — and a bare
 * `undefined` invites `?? someDefault`, which is how a guess becomes a displayed number.
 */
export interface Unsourced {
  readonly value: null;
  readonly source: { readonly kind: 'unsourced'; readonly intendedSource: string };
}

/** A profile field: either sourced, or explicitly not yet. */
export type Field<T> = Sourced<T> | Unsourced;

export const fetched = <T>(
  value: T,
  url: string,
  field: string,
  fetchedAt: Timestamp,
): Sourced<T> => ({ value, source: { kind: 'fetched', url, field, fetchedAt } });

export const surveyed = <T>(
  value: T,
  document: string,
  surveyedOn: IsoDate,
  note?: string,
): Sourced<T> => ({ value, source: { kind: 'surveyed', document, surveyedOn, note } });

export const estimated = <T>(value: T, basis: string): Sourced<T> => ({
  value,
  source: { kind: 'estimated', basis },
});

export const unsourced = (intendedSource: string): Unsourced => ({
  value: null,
  source: { kind: 'unsourced', intendedSource },
});

export const isSourced = <T>(field: Field<T>): field is Sourced<T> => field.value !== null;

/**
 * Whether a source answered on this request.
 *
 * `cached` is not a quiet success. The charter's bar is that a stale answer says so, so age
 * travels with the payload rather than being inferable only from a timestamp comparison.
 */
export type SourceHealth =
  | { readonly status: 'live'; readonly fetchedAt: Timestamp }
  | {
      readonly status: 'cached';
      readonly fetchedAt: Timestamp;
      readonly ageMinutes: number;
      /** Why we fell back — a timeout, a 5xx, or an offline device. */
      readonly reason: string;
    }
  | {
      readonly status: 'unavailable';
      readonly attemptedAt: Timestamp;
      readonly error: string;
    };

export const isUsable = (
  health: SourceHealth,
): health is Extract<SourceHealth, { status: 'live' | 'cached' }> =>
  health.status !== 'unavailable';
