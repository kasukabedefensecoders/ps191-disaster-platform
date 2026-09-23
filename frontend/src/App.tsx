import type { ReactElement } from "react";
import { Navigate, Route, HashRouter as Router, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import { AuthProvider, useAuth } from "./lib/AuthContext";
import { ShelterAuthProvider, useShelterAuth } from "./lib/ShelterAuthContext";
import { ThemeProvider } from "./lib/ThemeContext";
import ChangeDetection from "./pages/ChangeDetection";
import Dashboard from "./pages/Dashboard";
import FieldLogistics from "./pages/FieldLogistics";
import Forecast from "./pages/Forecast";
import Handoffs from "./pages/Handoffs";
import HouseholdAssessment from "./pages/HouseholdAssessment";
import IncidentOutcomes from "./pages/IncidentOutcomes";
import Landing from "./pages/Landing";
import PriorityRanking from "./pages/PriorityRanking";
import Relocations from "./pages/Relocations";
import RoutesPage from "./pages/Routes";
import ShelterOfficerDashboard from "./pages/ShelterOfficerDashboard";
import Shelters from "./pages/Shelters";
import Surveys from "./pages/Surveys";
import ZoneDetail from "./pages/ZoneDetail";
import Zones from "./pages/Zones";

// The "/" route tree is declared once (its nested <Route>s are matched
// regardless of what this component renders); an unauthenticated visitor
// sees the public Landing page in its place instead of being redirected
// straight to /login, and the nested routes simply don't render (Landing
// has no <Outlet/>) until they sign in.
function RootGate({ children }: { children: ReactElement }) {
  const { token, loading } = useAuth();
  if (loading) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading…</p>;
  if (!token) return <Landing />;
  return children;
}

// Shelter officer sessions are a wholly separate credential from the main
// AuthProvider (docs/TRD.md §10) — its own gate, keyed off useShelterAuth()
// instead. There's no separate /shelter-login page to redirect to anymore
// (sign-in is ShelterSignInModal, opened from Landing) — an unauthenticated
// visit to /shelter-dashboard/:code goes back to "/", the same as RootGate
// does for the main dashboard routes.
function ShelterRootGate({ children }: { children: ReactElement }) {
  const { token, loading } = useShelterAuth();
  if (loading) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading…</p>;
  if (!token) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ShelterAuthProvider>
          <Router>
            <Routes>
              {/* Sign-in is a modal over the landing page now (SignInModal,
                  opened from Landing) rather than its own page — this route
                  only exists so an old bookmark/link to /login still lands
                  the visitor on the landing page instead of a dead route. */}
              <Route path="/login" element={<Navigate to="/" replace />} />
              {/* Shelter sign-in is also a modal on the landing page now
                  (ShelterSignInModal) rather than its own page — same
                  reasoning as /login above. */}
              <Route path="/shelter-login" element={<Navigate to="/" replace />} />
              {/* A bare /shelter-dashboard (no :code) predates that param —
                  keep it as a graceful redirect for any old bookmark rather
                  than an unmatched, blank route. */}
              <Route path="/shelter-dashboard" element={<Navigate to="/" replace />} />
              <Route
                path="/shelter-dashboard/:code"
                element={
                  <ShelterRootGate>
                    <ShelterOfficerDashboard />
                  </ShelterRootGate>
                }
              />
              <Route
                path="/"
                element={
                  <RootGate>
                    <Layout />
                  </RootGate>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="zones" element={<Zones />} />
                <Route path="zones/:zoneId" element={<ZoneDetail />} />
                <Route path="forecast" element={<Forecast />} />
                <Route path="change-detection" element={<ChangeDetection />} />
                <Route path="households" element={<HouseholdAssessment />} />
                <Route path="priority" element={<PriorityRanking />} />
                <Route path="shelters" element={<Shelters />} />
                <Route path="relocations" element={<Relocations />} />
                <Route path="field-logistics" element={<FieldLogistics />} />
                <Route path="routes" element={<RoutesPage />} />
                <Route path="surveys" element={<Surveys />} />
                <Route path="handoffs" element={<Handoffs />} />
                <Route path="incident-outcomes" element={<IncidentOutcomes />} />
              </Route>
            </Routes>
          </Router>
        </ShelterAuthProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
