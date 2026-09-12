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

export interface Zone {
  zone_id: string;
  display_code: string | null;
  district_id: string;
  name: string;
  geom: GeoJSONPolygon;
  hazard_types: string[];
  population: number;
  data_confidence: "baseline" | "field_verified" | "due_for_reverification";
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

export interface ZoneListResponse {
  items: Zone[];
  count: number;
  limit: number;
  offset: number;
  next_offset: number | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new ApiError(res.status, `login failed (${res.status})`);
  const data = await res.json();
  return data.access_token as string;
}

export async function fetchZones(token: string): Promise<ZoneListResponse> {
  const res = await fetch(`${API_BASE}/zones?limit=200`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new ApiError(res.status, `fetch zones failed (${res.status})`);
  return res.json();
}
