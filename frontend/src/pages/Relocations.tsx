import { useEffect, useState } from "react";

import { SampleDataBadge, TierBadge } from "../components/badges";
import { fetchRelocations, updateRelocationStatus, type RelocationRecord } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const NEXT_STATUS: Record<RelocationRecord["status"], string | null> = {
  assigned: "in_transit",
  in_transit: "arrived",
  arrived: null,
};

export default function Relocations() {
  const { token, user } = useAuth();
  const [records, setRecords] = useState<RelocationRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    if (!token) return;
    fetchRelocations(token)
      .then((r) => setRecords(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);

  const advance = async (record: RelocationRecord) => {
    const next = NEXT_STATUS[record.status];
    if (!token || !next) return;
    setBusyId(record.record_id);
    try {
      await updateRelocationStatus(token, record.record_id, next);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>{error}</p>;
  if (!records) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading relocations…</p>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ fontSize: 14, margin: 0 }}>Relocations</h2>
        <SampleDataBadge />
      </div>
      {records.length === 0 && <p style={{ color: "var(--ink3)", fontSize: 13 }}>No relocation decisions yet.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {records.map((r) => {
          const next = NEXT_STATUS[r.status];
          return (
            <div
              key={r.record_id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: 10,
                fontSize: 13,
              }}
            >
              <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
                <span style={{ fontFamily: "var(--font-data)", fontWeight: 600 }}>{r.display_code}</span>
                <TierBadge tier={r.priority_tier} />
                <span style={{ color: "var(--ink3)", fontFamily: "var(--font-data)" }}>{r.status}</span>
              </div>
              {next && user?.role === "sdma_official" && (
                <button
                  onClick={() => advance(r)}
                  disabled={busyId === r.record_id}
                  style={{
                    background: "transparent",
                    border: "1px solid var(--border2)",
                    color: "var(--ink2)",
                    borderRadius: 4,
                    padding: "5px 10px",
                    fontSize: 12,
                    cursor: busyId === r.record_id ? "default" : "pointer",
                  }}
                >
                  Mark {next.replace("_", " ")}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
