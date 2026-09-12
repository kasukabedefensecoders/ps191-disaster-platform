import type { ReactElement } from "react";
import { Navigate, Route, HashRouter as Router, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import { AuthProvider, useAuth } from "./lib/AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Relocations from "./pages/Relocations";
import Shelters from "./pages/Shelters";

function RequireAuth({ children }: { children: ReactElement }) {
  const { token, loading } = useAuth();
  if (loading) return <p style={{ padding: 16, color: "var(--ink3)" }}>Loading…</p>;
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

// Without this, a successful login leaves the user stranded on /login —
// AuthContext updates `token`, but nothing was navigating away from the
// login route itself. Caught by actually logging in through the browser,
// not by the type-checker or the earlier build check.
function RedirectIfAuthed({ children }: { children: ReactElement }) {
  const { token, loading } = useAuth();
  if (loading) return null;
  if (token) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route
            path="/login"
            element={
              <RedirectIfAuthed>
                <Login />
              </RedirectIfAuthed>
            }
          />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="shelters" element={<Shelters />} />
            <Route path="relocations" element={<Relocations />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}
