import type { Lift, LiftStatus, MountainConditions, PodConditions } from '../conditions.js';
import type { PodAccess, LiftId } from '../access.js';
import { liftId } from '../access.js';
import { ACCESS_EDGES, KNOWN_ACCESS_GAPS } from '../catalog.js';
import { estimated, timestamp, unsourced } from '../provenance.js';
import type { SourceHealth, Timestamp } from '../provenance.js';
import { parseGroomingFeed } from './grooming.js';
import type { GroomingFeedPayload, ParsedGrooming } from './grooming.js';
import { POD_IDS } from '../pod.js';
import type { PodId } from '../pod.js';

export interface LiftFeedPayload {
  liftStatuses: readonly {
    liftName: string;
    status: string;
    area: string;
    elevationGainFeet: string;
    time: string;
    hoursOfOperation: string;
  }[];
}

export interface ParsedLifts {
  readonly lifts: readonly Lift[];
  readonly access: ReadonlyMap<PodId, PodAccess>;
  readonly diagnostics: readonly string[];
  readonly health: SourceHealth;
}

const URL = 'https://www.aspensnowmass.com/AspenSnowmass/LiftStatus/Feed?mountain=Snowmass&areas=&isSummer=False';

const normalizeStatus = (raw: string): LiftStatus | null => {
  switch (raw.trim().toLowerCase()) {
    case 'open': case 'opened': return 'open';
    case 'closed': case 'close': return 'closed';
    case 'on hold': case 'on-hold': case 'hold': return 'on-hold';
    default: return null;
  }
};

const number = (value: string): number | null => {
  const parsed = Number(value.replace(/,/g, '').trim());
  return Number.isFinite(parsed) ? parsed : null;
};

export const parseLiftFeed = (
  payload: LiftFeedPayload,
  podIds: readonly PodId[] = POD_IDS,
  fetchedAt: Timestamp = timestamp(new Date().toISOString()),
): ParsedLifts => {
  const diagnostics: string[] = [];
  const lifts = payload.liftStatuses.map((raw): Lift => {
    const status = normalizeStatus(raw.status);
    if (status === null) diagnostics.push(`Unrecognized lift status "${raw.status}" for "${raw.liftName}"`);
    const verticalFt = number(raw.elevationGainFeet);
    const rideMinutes = number(raw.time);
    if (verticalFt === null) diagnostics.push(`Unrecognized elevation "${raw.elevationGainFeet}" for "${raw.liftName}"`);
    if (rideMinutes === null) diagnostics.push(`Unrecognized ride time "${raw.time}" for "${raw.liftName}"`);
    return {
      id: liftId(raw.liftName),
      // `on-hold` is the only non-running status that does not claim Aspen explicitly said
      // "closed"; the raw value and diagnostic preserve the distinction for callers.
      status: status ?? 'on-hold',
      statusRaw: raw.status,
      verticalFt: verticalFt ?? 0,
      rideMinutes: rideMinutes ?? 0,
      hoursOfOperation: raw.hoursOfOperation,
    };
  });
  const byLift = new Map<LiftId, Lift>(lifts.map((lift) => [lift.id, lift]));
  const access = new Map<PodId, PodAccess>();
  for (const pod of podIds) {
    const edges = ACCESS_EDGES.filter((edge) => edge.pod === pod);
    if (edges.length === 0) {
      access.set(pod, KNOWN_ACCESS_GAPS[pod]
        ? { kind: 'unknown', reason: KNOWN_ACCESS_GAPS[pod] }
        : { kind: 'no-access', reason: 'No access edge is declared for this pod.' });
      continue;
    }
    const running = edges.filter((edge) => byLift.get(edge.lift)?.status === 'open');
    const primary = running.filter((edge) => edge.kind === 'primary').map((edge) => edge.lift);
    const connecting = running.filter((edge) => edge.kind === 'connecting').map((edge) => edge.lift);
    access.set(pod, primary.length > 0 ? { kind: 'lift-served', via: primary }
      : connecting.length > 0 ? { kind: 'traverse-only', from: connecting }
      : { kind: 'no-access', reason: 'All declared access lifts are closed or unavailable.' });
  }
  return { lifts, access, diagnostics, health: { status: 'live', fetchedAt } };
};

/** Assemble the feed-backed portion of MountainConditions; non-feed snow sources stay unsourced. */
export const buildMountainConditions = (
  groomingPayload: GroomingFeedPayload,
  liftPayload: LiftFeedPayload,
  fetchedAt: Timestamp = timestamp(new Date().toISOString()),
): MountainConditions => {
  const grooming: ParsedGrooming = parseGroomingFeed(groomingPayload, fetchedAt);
  const parsed = parseLiftFeed(liftPayload, [...grooming.pods.keys()], fetchedAt);
  const pods = new Map<PodId, PodConditions>();
  for (const [podId, runs] of grooming.pods) {
    pods.set(podId, {
      podId, runs, access: parsed.access.get(podId)!,
      maxDifficulty: { value: grooming.maxDifficulty.get(podId) ?? null, source: estimated(null, 'Derived from areas[].trails[].difficulty on this fetch.').source },
      openRunCount: runs.filter((run) => run.open).length,
      groomedRunCount: runs.filter((run) => run.groomed).length,
      gated: grooming.gated.has(podId),
    });
  }
  const unavailable = { status: 'unavailable' as const, attemptedAt: fetchedAt, error: 'No source configured.' };
  return {
    fetchedAt, pods, lifts: parsed.lifts,
    snow: { baseDepthIn: unsourced('SNOTEL'), newSnow24hIn: unsourced('Aspen station'), newSnow72hIn: unsourced('Aspen station'), sweIn: unsourced('SNOTEL'), thinCoverRisk: unsourced('Terrain survey') },
    health: { grooming: grooming.health, lifts: parsed.health, station: unavailable, snotel: unavailable, forecast: unavailable },
    diagnostics: [...grooming.diagnostics, ...parsed.diagnostics],
  };
};

export { URL as LIFT_FEED_URL };
