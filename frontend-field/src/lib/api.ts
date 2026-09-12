const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

export interface CurrentUser {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  district_id: string | null;
}

export interface Zone {
  zone_id: string;
  display_code: string | null;
  name: string;
}

export interface HouseholdSummary {
  household_id: string;
  display_code: string | null;
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

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const body = new URLSearchParams({ username: email, password });
  return request("/auth/login", null, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
}

export const getMe = (token: string) => request<CurrentUser>("/auth/me", token);

export const fetchZones = (token: string) => request<{ items: Zone[] }>("/zones?limit=200", token);
export const fetchZoneHouseholds = (token: string, zoneId: string) =>
  request<{ items: HouseholdSummary[] }>(`/zones/${zoneId}/households?limit=200`, token);

export interface SyncResult {
  synced: { survey_id: string; survey_display_code: string; household_id: string }[];
  errors: { survey_id: string; error: string }[];
}

export const syncSurveys = (token: string, surveys: unknown[]) =>
  request<SyncResult>("/surveys/sync", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ surveys }),
  });
