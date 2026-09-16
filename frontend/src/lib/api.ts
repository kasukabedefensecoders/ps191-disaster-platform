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

export interface Shelter {
  shelter_id: string;
  display_code: string | null;
  district_id: string;
  name: string;
  geom: GeoJSONPoint;
  max_capacity: number;
  current_occupancy: number;
  facilities: Record<string, unknown>;
  status: string;
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
export const fetchZoneHouseholds = (token: string, zoneId: string) =>
  request<Paged<HouseholdRanked>>(`/zones/${zoneId}/households?limit=200`, token);

export const fetchShelters = (token: string) => request<Paged<Shelter>>("/shelters?limit=200", token);
export const fetchShelterMatches = (token: string, householdId: string) =>
  request<{ items: ShelterMatch[]; count: number; need: number; note: string }>(
    `/households/${householdId}/shelter-matches`,
    token,
  );

export const fetchRoutes = (token: string) => request<Paged<RouteRecord>>("/routes?limit=200", token);

export const fetchRelocations = (token: string) => request<Paged<RelocationRecord>>("/relocations?limit=200", token);
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
