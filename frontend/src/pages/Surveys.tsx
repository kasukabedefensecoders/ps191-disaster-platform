import { useEffect, useState } from "react";

import { SampleDataBadge } from "../components/badges";
import { fetchSurveys, reviewSurvey, type Survey } from "../lib/api";
import { useAuth } from "../lib/AuthContext";

const REVIEW_COLOR: Record<Survey["review_status"], string> = {
  unreviewed: "var(--ink3)",
  approved: "var(--sev5)",
  flagged: "var(--sev1)",
};

export default function Surveys() {
  const { token, user } = useAuth();
  const [surveys, setSurveys] = useState<Survey[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    if (!token) return;
    fetchSurveys(token)
      .then((r) => setSurveys(r.items))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  };

  useEffect(load, [token]);

  const act = async (surveyId: string, status: "approved" | "flagged") => {
    if (!token) return;
    setBusyId(surveyId);
    try {
      await reviewSurvey(token, surveyId, status);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId(null);
    }
  };

  if (error) return <p style={{ padding: 16, color: "var(--sev1)" }}>Failed to load surveys: {error}</p>;
  if (!surveys) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading surveys…</p>;

  const canReview = user?.role === "sdma_official";

  return (
    <div style={{ padding: 16, maxWidth: 900 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ fontSize: 18 }}>{canReview ? "Survey review" : "Submission history"}</h2>
        <SampleDataBadge />
      </div>
      {surveys.length === 0 && <p style={{ fontSize: 12, color: "var(--ink3)" }}>No survey submissions yet.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {surveys.map((s) => (
          <div key={s.survey_id} className="ps-card-hover" style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 6, padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "var(--font-data)", fontWeight: 600, fontSize: 13 }}>{s.display_code}</span>
              <span
                style={{
                  fontFamily: "var(--font-data)",
                  fontSize: 11,
                  color: REVIEW_COLOR[s.review_status],
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {s.review_status}
                {s.synced_at === null && <span style={{ color: "var(--ink4)" }}> · captured offline</span>}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--ink3)" }}>Submitted {new Date(s.submitted_at).toLocaleString()}</div>
            <div style={{ fontSize: 12, color: "var(--ink2)", display: "flex", gap: 12, flexWrap: "wrap" }}>
              {Object.entries(s.payload)
                .filter(([k]) => k !== "notes")
                .map(([k, v]) => (
                  <span key={k} style={{ fontFamily: "var(--font-data)" }}>
                    {k.replace(/_/g, " ")}: {String(v)}
                  </span>
                ))}
            </div>
            {typeof s.payload.notes === "string" && s.payload.notes && (
              <p style={{ fontSize: 12, color: "var(--ink2)", margin: 0 }}>{s.payload.notes}</p>
            )}
            {canReview && s.review_status === "unreviewed" && (
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => act(s.survey_id, "approved")} disabled={busyId === s.survey_id} className="ps-btn-confirm" style={actionStyle("var(--sev5)")}>
                  Approve
                </button>
                <button onClick={() => act(s.survey_id, "flagged")} disabled={busyId === s.survey_id} className="ps-btn-confirm" style={actionStyle("var(--sev1)")}>
                  Flag
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function actionStyle(color: string) {
  return {
    background: "transparent",
    border: `1px solid ${color}`,
    borderRadius: 4,
    color,
    padding: "5px 12px",
    fontSize: 12,
    cursor: "pointer",
    fontFamily: "var(--font-interface)",
  } as const;
}
