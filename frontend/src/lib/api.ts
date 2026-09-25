const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

export interface Factor {
  name: string;
  weight: number;
  input_value: unknown;
  contribution: number;
}

export interface GeoJSONPolygon {
  type: "Polygon";
  coordinates: number[][][];
}
export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number];
}
export interface GeoJSONLineString {
  type: "LineString";
  coordinates: [number, number][];
}

export type DataConfidence = "baseline" | "field_verified" | "due_for_reverification";
export type PriorityTier = "immediate" | "short_term" | "medium_term";

export interface Zone {
  zone_id: string;
  display_code: string | null;
  district_id: string;
  name: string;
  geom: GeoJSONPolygon;
  hazard_types: string[];
  population: number;
  data_confidence: DataConfidence;
  last_verified_at: string | null;
  last_verified_by: string | null;
  susceptibility_score: number | null;
  susceptibility_factors: Factor[] | null;
  gsi_classification: string | null;
  gsi_score: number | null;
  risk_score_72h: number | null;
  risk_score_factors: Factor[] | null;
  risk_score_updated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ZoneDetail extends Zone {
  incident_history: Record<string, unknown>[];
  ml_vs_gsi_divergence_note: string | null;
}

export interface RiskForecast {
  forecast_id: string;
  zone_id: string;
  horizon_hours: number;
  score: number;
  factors: Factor[];
  model_version: string;
  generated_at: string;
}

export interface ChangeDetection {
  detection_id: string;
  zone_id: string;
  before_image_ref: string;
  after_image_ref: string;
  affected_area_geom: Record<string, unknown> | null;
  confidence: number | null;
  cross_referenced_household_ids: string[];
  cross_referenced_survey_ids: string[];
  detected_at: string;
  created_at: string;
}

export type ReviewStatus = "unreviewed" | "approved" | "flagged";

export interface Survey {
  survey_id: string;
  display_code: string | null;
  zone_id: string;
  household_id: string | null;
  officer_id: string;
  submitted_at: string;
  synced_at: string | null;
  payload: Record<string, unknown>;
  photo_url: string | null;
  review_status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface HouseholdRanked {
  household_id: string;
  display_code: string | null;
  zone_id: string;
  geom: GeoJSONPoint;
  population_count: number;
  children_count: number;
  elderly_count: number;
  assistance_needs_count: number;
  structural_condition: string;
  data_confidence: DataConfidence;
  last_surveyed_at: string | null;
  vulnerability_score: number;
  vulnerability_factors: Factor[];
  priority_score: number;
  priority_tier: PriorityTier;
  priority_factors: Factor[];
}

export type ShelterStatus = "active" | "standby" | "full" | "closed" | "damaged";

export interface Shelter {
  shelter_id: string;
  display_code: string | null;
  district_id: string;
  name: string;
  geom: GeoJSONPoint;
  max_capacity: number;
  current_occupancy: number;
  facilities: Record<string, unknown>;
  status: ShelterStatus;
  contact_name: string | null;
  contact_phone: string | null;
  needs: string[];
  last_updated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShelterMatch extends Shelter {
  distance_km: number;
  duration_minutes: number;
  route_access: string;
  match_score: number;
  match_factors: Factor[];
}

export interface RouteRecord {
  route_id: string;
  display_code: string | null;
  zone_id: string;
  shelter_id: string;
  origin_geom: GeoJSONPoint;
  dest_geom: GeoJSONPoint;
  path: GeoJSONLineString;
  blocked_segments: Record<string, unknown>[];
  distance_km: number | null;
  estimated_duration_minutes: number | null;
  created_at: string;
  updated_at: string;
}

export interface RelocationRecord {
  record_id: string;
  display_code: string | null;
  household_id: string;
  shelter_id: string;
  route_id: string | null;
  vehicle_id: string | null;
  escort_id: string | null;
  priority_tier: PriorityTier;
  priority_factors: Factor[] | null;
  allocation_factors: Factor[] | null;
  status: "assigned" | "in_transit" | "arrived";
  decided_by: string;
  assigned_at: string;
  in_transit_at: string | null;
  arrived_at: string | null;
  created_at: string;
  updated_at: string;
}

export type HandoffStatus = "open" | "acknowledged" | "in_progress" | "resolved";

export interface HandoffLog {
  log_id: string;
  display_code: string | null;
  need_type: string;
  agency: string;
  status: HandoffStatus;
  linked_record_id: string | null;
  zone_id: string | null;
  household_id: string | null;
  description: string | null;
  raised_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface IncidentOutcome {
  outcome_id: string;
  zone_id: string;
  relocation_record_id: string | null;
  forecast_id: string | null;
  detection_id: string | null;
  occurred_at: string;
  shelter_adequate: boolean | null;
  route_held_up: boolean | null;
  actual_impact: Record<string, unknown> | null;
  notes: string | null;
  recorded_by: string;
  recorded_at: string;
  created_at: string;
  predicted_score: number | null;
  predicted_horizon_hours: number | null;
}

export interface Paged<T> {
  items: T[];
  count: number;
  limit: number;
  offset: number;
  next_offset?: number | null;
}

export interface DashboardSummary {
  since: string | null;
  generated_at: string;
  zones: Paged<Zone>;
  shelters: Paged<Shelter>;
  routes: Paged<RouteRecord>;
  relocations: Paged<RelocationRecord>;
  handoffs: Paged<HandoffLog>;
  top_priority_households: HouseholdRanked[];
}

export interface CurrentUser {
  user_id: string;
  full_name: string;
  email: string;
  role: "sdma_official" | "field_officer" | "control_room";
  district_id: string | null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, `${init.method ?? "GET"} ${path} failed (${res.status}): ${body}`);
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
  const body = new URLSearchParams({ username: email, password });
  return request("/auth/login", null, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
}

export const getMe = (token: string) => request<CurrentUser>("/auth/me", token);

export const fetchZones = (token: string) => request<Paged<Zone>>("/zones?limit=200", token);
export const fetchZone = (token: string, zoneId: string) => request<ZoneDetail>(`/zones/${zoneId}`, token);
export const fetchZoneHouseholds = (token: string, zoneId: string) =>
  request<Paged<HouseholdRanked>>(`/zones/${zoneId}/households?limit=200`, token);

export const fetchZoneForecasts = (token: string, zoneId: string) =>
  request<{ items: RiskForecast[]; count: number }>(`/zones/${zoneId}/forecasts?limit=50`, token);
export const generateForecasts = (token: string, zoneId: string) =>
  request<{ zone_id: string; generated_at: string; forecasts: RiskForecast[] }>(`/zones/${zoneId}/forecasts/generate`, token, {
    method: "POST",
  });

export const fetchZoneChangeDetections = (token: string, zoneId: string) =>
  request<{ items: ChangeDetection[]; count: number }>(`/zones/${zoneId}/change-detections?limit=50`, token);
export const runChangeDetection = (token: string, zoneId: string) =>
  request<ChangeDetection>(`/zones/${zoneId}/change-detections/run`, token, { method: "POST" });

// Images need the Authorization header, so a plain <img src> won't work —
// fetch the bytes and hand back a blob: URL the caller revokes when done.
export async function fetchZoneChangeDetectionImage(token: string, zoneId: string, which: "before" | "after"): Promise<string> {
  const res = await fetch(`${API_BASE}/zones/${zoneId}/change-detections/image/${which}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new ApiError(res.status, `GET change-detections/image/${which} failed (${res.status})`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export const fetchSurveys = (token: string) => request<{ items: Survey[]; count: number; limit: number; offset: number }>("/surveys?limit=200", token);
export const reviewSurvey = (token: string, surveyId: string, review_status: "approved" | "flagged") =>
  request<Survey>(`/surveys/${surveyId}/review`, token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ review_status }),
  });

export const addBlockedSegment = (token: string, routeId: string, payload: { reason: string; osm_way_id?: string | null }) =>
  request<RouteRecord>(`/routes/${routeId}/blocked-segments`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: "field_report", ...payload }),
  });
export const clearBlockedSegments = (token: string, routeId: string) =>
  request<RouteRecord>(`/routes/${routeId}/blocked-segments`, token, { method: "DELETE" });

export const fetchShelters = (token: string) => request<Paged<Shelter>>("/shelters?limit=200", token);
export const createShelter = (
  token: string,
  payload: {
    display_code: string;
    district_id: string;
    name: string;
    geom: GeoJSONPoint;
    max_capacity: number;
    current_occupancy?: number;
    facilities?: Record<string, unknown>;
    status?: ShelterStatus;
    contact_name?: string | null;
    contact_phone?: string | null;
    needs?: string[];
  },
) =>
  request<Shelter>("/shelters", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
export type ShelterUpdatePayload = Partial<{
  name: string;
  geom: GeoJSONPoint;
  max_capacity: number;
  current_occupancy: number;
  facilities: Record<string, unknown>;
  status: ShelterStatus;
  contact_name: string | null;
  contact_phone: string | null;
  needs: string[];
}>;
export const updateShelter = (token: string, shelterId: string, payload: ShelterUpdatePayload) =>
  request<Shelter>(`/shelters/${shelterId}`, token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

// Shelter officer dashboard's own code-based session (POST /auth/shelter-login,
// not the sdma_official/field_officer/control_room JWT flow) — see
// docs/TRD.md §10. The resulting token only ever unlocks these two calls.
export interface ShelterSession {
  access_token: string;
  token_type: string;
  shelter_id: string;
  display_code: string | null;
  name: string;
}
export const shelterLogin = (shelterCode: string) =>
  request<ShelterSession>("/auth/shelter-login", null, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shelter_code: shelterCode }),
  });
export const fetchMyShelter = (token: string) => request<Shelter>("/shelters/me", token);
export const updateMyShelter = (token: string, payload: ShelterUpdatePayload) =>
  request<Shelter>("/shelters/me", token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
export const fetchShelterMatches = (token: string, householdId: string) =>
  request<{ items: ShelterMatch[]; count: number; need: number; note: string }>(
    `/households/${householdId}/shelter-matches`,
    token,
  );

export type VehicleStatus = "available" | "assigned" | "in_transit" | "unavailable";
export interface Vehicle {
  vehicle_id: string;
  district_id: string;
  display_code: string | null;
  route_label: string | null;
  vehicle_type: string;
  capacity: number;
  status: VehicleStatus;
  created_at: string;
  updated_at: string;
}
export const fetchVehicles = (token: string) => request<Vehicle[]>("/vehicles", token);

export const fetchRoutes = (token: string) => request<Paged<RouteRecord>>("/routes?limit=200", token);

export interface DemoSeedResult {
  created: boolean;
  items: RelocationRecord[];
  counts_by_status: Record<string, number>;
  surveys_created: boolean;
  surveys: Survey[];
}
// Always resets relocation_records/surveys (plus the vehicle/shelter fields
// their lifecycle mutates) to a fresh copy of the demo scenario before
// re-seeding — see services/demo_seed.py. Safe to call repeatedly.
export const resetDemoRelocations = (token: string) =>
  request<DemoSeedResult>("/demo/seed-relocations", token, { method: "POST" });

export const fetchRelocations = (token: string) => request<Paged<RelocationRecord>>("/relocations?limit=200", token);

export interface VehicleGroupHousehold {
  record_id: string;
  display_code: string | null;
  household_id: string;
  household_display_code: string | null;
  shelter_id: string;
  shelter_display_code: string | null;
  shelter_name: string;
  population_count: number;
  children_count: number;
  elderly_count: number;
  assistance_needs_count: number;
  priority_tier: PriorityTier;
  status: RelocationRecord["status"];
  boarded_at: string | null;
  arrived_at: string | null;
}
export interface VehicleGroup {
  vehicle_id: string | null;
  vehicle_display_code: string | null;
  vehicle_type: string | null;
  route_label: string | null;
  capacity: number | null;
  current_occupancy: number;
  status: RelocationRecord["status"];
  departed_at: string | null;
  estimated_arrival: string | null;
  households: VehicleGroupHousehold[];
}
export const fetchRelocationsByVehicle = (token: string) =>
  request<{ items: VehicleGroup[]; note: string }>("/relocations/by-vehicle", token);

export const createRelocation = (
  token: string,
  payload: { household_id: string; shelter_id: string; vehicle_id?: string | null; escort_id?: string | null },
) =>
  request<RelocationRecord>("/relocations", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
export const updateRelocationStatus = (token: string, recordId: string, status: string) =>
  request<RelocationRecord>(`/relocations/${recordId}/status`, token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });

export const fetchDashboardSummary = (token: string) => request<DashboardSummary>("/dashboard/summary", token);

export const fetchHandoffs = (token: string) => request<Paged<HandoffLog>>("/handoffs?limit=200", token);
export const createHandoff = (
  token: string,
  payload: { need_type: string; agency: string; description?: string | null; zone_id?: string | null; household_id?: string | null },
) =>
  request<HandoffLog>("/handoffs", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
export const updateHandoffStatus = (token: string, logId: string, status: HandoffStatus) =>
  request<HandoffLog>(`/handoffs/${logId}/status`, token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });

export const fetchIncidentOutcomes = (token: string, zoneId: string) =>
  request<{ items: IncidentOutcome[]; count: number }>(`/zones/${zoneId}/incident-outcomes?limit=100`, token);
export const createIncidentOutcome = (
  token: string,
  zoneId: string,
  payload: {
    occurred_at: string;
    shelter_adequate?: boolean | null;
    route_held_up?: boolean | null;
    notes?: string | null;
  },
) =>
  request<IncidentOutcome>(`/zones/${zoneId}/incident-outcomes`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
