import Dexie, { type Table } from "dexie";

/**
 * The offline queue itself (rule 5: offline-first is a data-model
 * property). A survey is written here the instant the officer submits the
 * form — before any network call — so capture works with zero
 * connectivity. `synced` flips true only after the backend's
 * insert-on-conflict sync endpoint confirms it; a queued row is never
 * deleted, only marked, so a device that goes offline again mid-sync still
 * has an accurate local record of what has and hasn't made it to the
 * server.
 */
export interface QueuedSurvey {
  survey_id: string; // client-generated (crypto.randomUUID()) — the idempotency key rule 5 depends on
  zone_id: string;
  household_id: string | null;
  submitted_at: string;
  payload: {
    population_count: number;
    children_count: number;
    elderly_count: number;
    assistance_needs_count: number;
    structural_condition: string;
    notes: string | null;
  };
  geotag: { type: "Point"; coordinates: [number, number] } | null;
  synced: boolean;
  sync_error: string | null;
  synced_household_id: string | null;
}

export interface CachedZone {
  zone_id: string;
  display_code: string | null;
  name: string;
}
export interface CachedHousehold {
  household_id: string;
  zone_id: string;
  display_code: string | null;
}

class FieldDB extends Dexie {
  surveys!: Table<QueuedSurvey, string>;
  zonesCache!: Table<CachedZone, string>;
  householdsCache!: Table<CachedHousehold, string>;

  constructor() {
    super("ps191_field");
    this.version(1).stores({
      // survey_id as the primary key means Dexie itself also naturally
      // de-dupes a resubmission with the same client-generated id.
      surveys: "survey_id, synced",
      // Cached the last time the zone/household picker had connectivity,
      // so the capture form still works with zero network — not just the
      // submit queue, the reference data it needs has to be offline-first
      // too, or "simulated offline" would only cover half the flow.
      zonesCache: "zone_id",
      householdsCache: "household_id, zone_id",
    });
  }
}

export const db = new FieldDB();
