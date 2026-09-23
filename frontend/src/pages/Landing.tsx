import { useEffect, useRef, useState } from "react";

import ParticleField from "../components/ParticleField";
import SignInModal, { type RoleKey } from "../components/SignInModal";
import ThemeToggle from "../components/ThemeToggle";
import ZoneMap from "../components/ZoneMap";
import { useTheme } from "../lib/ThemeContext";

const ROLE_ACCENTS = {
  sdma_official: "var(--accent)",
  field_officer: "var(--sev4)",
  shelter_officer: "var(--sev5)",
  control_room: "var(--blue-ink)",
} as const;

/** Public landing — PROTOTYPE/PS191 Platform.dc.html's isLanding view.
 * The hero map renders the real basemap/tile-fallback chain with no zone
 * overlays (rather than the prototype's iframed static demo file) — real
 * zone/hazard data stays behind auth, consistent with this being an
 * authority-only decision layer, not something to preview publicly. An
 * ambient particle-field backdrop sits behind everything, purely
 * decorative and theme-aware. Sign-in is always the one modal (SignInModal)
 * over this page, never a separate page — all four roles, including the
 * shelter officer's separate code-only credential, live in it. Clicking a
 * role card opens the modal pre-selected to that role so a judge can test
 * all four with one click each. */
export default function Landing() {
  const { theme } = useTheme();
  const [signInOpen, setSignInOpen] = useState(false);
  const [initialRole, setInitialRole] = useState<RoleKey | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const [rolesVisible, setRolesVisible] = useState(false);
  const rolesRef = useRef<HTMLDivElement>(null);

  const openSignIn = (role: RoleKey | null = null) => {
    setInitialRole(role);
    setSignInOpen(true);
  };

  // The header goes from transparent to a frosted panel once the hero has
  // scrolled past — this is a normal document-flow page (the window itself
  // scrolls), not a boxed scroll container.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // One scroll-triggered reveal, for the role cards only — not a per-card
  // effect (that reads as scattered/generic), a single moment when the
  // section as a whole enters view.
  useEffect(() => {
    const el = rolesRef.current;
    if (!el) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setRolesVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRolesVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div style={{ position: "relative", minHeight: "100vh", overflowX: "hidden", background: "var(--bg)", color: "var(--ink)", display: "flex", flexDirection: "column" }}>
      <div style={{ position: "fixed", inset: 0, zIndex: 0 }}>
        <ParticleField theme={theme} />
      </div>
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 2,
          flex: "none",
          display: "flex",
          alignItems: "center",
          gap: 11,
          padding: "18px 40px",
          borderBottom: `1px solid ${scrolled ? "var(--border)" : "transparent"}`,
          background: scrolled ? "color-mix(in srgb, var(--bg) 78%, transparent)" : "transparent",
          backdropFilter: scrolled ? "blur(10px)" : "none",
          WebkitBackdropFilter: scrolled ? "blur(10px)" : "none",
          transition: "background 0.25s ease, border-color 0.25s ease",
        }}
      >
        <div
          style={{
            width: 26,
            height: 26,
            flex: "none",
            borderRadius: 4,
            background: "var(--brand-deep)",
            border: "1px solid var(--blue)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            font: "600 11px/1 var(--font-data)",
            color: "var(--on-brand)",
          }}
        >
          RZ
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ font: "600 13px/1.15 var(--font-interface)", color: "var(--ink)" }}>Red Zone &amp; Relocation</div>
          <div style={{ font: "400 10px/1.4 var(--font-data)", color: "var(--ink4)", letterSpacing: "0.06em" }}>SIH26191 · NDRF / MHA</div>
        </div>
        <ThemeToggle />
        <button onClick={() => openSignIn()} className="ps-btn-outline" style={signInOutlineStyle}>
          Sign in
        </button>
      </header>

      <main
        data-reveal=""
        style={{
          position: "relative",
          zIndex: 1,
          flex: 1,
          display: "flex",
          flexDirection: "column",
          padding: "56px 40px 60px",
          gap: 56,
          maxWidth: 1180,
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div className="ps-hero-grid" style={{ position: "relative", display: "grid", gap: 40, alignItems: "center" }}>
          {/* One soft, brand-toned wash behind the headline — the hero's one
              bit of visual boldness, not a decoration repeated per-section. */}
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              top: "-15%",
              left: "-10%",
              width: 560,
              height: 560,
              background: "radial-gradient(circle, color-mix(in srgb, var(--accent) 16%, transparent), transparent 65%)",
              pointerEvents: "none",
              zIndex: 0,
            }}
          />
          <div style={{ position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 18 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--sev5)", flex: "none", animation: "pulseDot 2s ease-in-out infinite" }} />
              <span style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink4)" }}>
                District disaster management · pilot deployment
              </span>
            </div>
            <div
              style={{
                font: "700 clamp(34px, 4.6vw, 58px)/1.06 var(--font-interface)",
                letterSpacing: "-0.02em",
                color: "var(--ink)",
                marginBottom: 22,
              }}
            >
              Hazard red zones, carrying capacity and relocation priority — for one district.
            </div>
            <div style={{ font: "400 15px/1.7 var(--font-interface)", color: "var(--ink3)", maxWidth: 500, marginBottom: 32 }}>
              A single decision layer over IMD, CWC, GSI, INCOIS and Bhuvan data — mapping which zones are at risk, who
              lives there, and where they go next.
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
              <button onClick={() => openSignIn()} className="ps-btn-primary" style={heroButtonStyle}>
                Sign in to your dashboard →
              </button>
              <span style={{ font: "400 11px/1.5 var(--font-data)", color: "var(--ink4)" }}>
                Four roles · one district · Dima Hasao, Assam
              </span>
            </div>
          </div>

          {/* The hero's other bit of boldness: a "hazard monitoring" frame
              around the map preview — corner brackets and a slow scanning
              sweep, both drawn from the subject matter (a live-monitoring
              console) rather than generic decoration. Quiet everywhere else
              on the page, deliberate here. */}
          <div style={{ position: "relative", height: 420 }}>
            <div aria-hidden="true" style={cornerBracketStyle("top", "left")} />
            <div aria-hidden="true" style={cornerBracketStyle("top", "right")} />
            <div aria-hidden="true" style={cornerBracketStyle("bottom", "left")} />
            <div aria-hidden="true" style={cornerBracketStyle("bottom", "right")} />
            <div
              style={{
                position: "relative",
                height: "100%",
                borderRadius: 8,
                overflow: "hidden",
                border: "1px solid var(--border)",
                background: "var(--bg2)",
                boxShadow: "var(--shadow)",
              }}
            >
              <ZoneMap zones={[]} theme={theme} emptyFallbackNote="Sign in to see live zone data for Dima Hasao district." />
              <div aria-hidden="true" className="ps-scan-sweep" />
            </div>
          </div>
        </div>

        <div ref={rolesRef}>
          <div style={{ font: "500 11px/1 var(--font-data)", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--ink4)", marginBottom: 16 }}>
            Four roles, four dashboards
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
            <RoleCard
              title="SDMA official"
              desc="Full district view — risk forecasting, household assessment, shelter allocation, logistics and interagency handoff."
              accent={ROLE_ACCENTS.sdma_official}
              visible={rolesVisible}
              delayMs={0}
              onClick={() => openSignIn("sdma_official")}
            />
            <RoleCard
              title="Field officer"
              desc="A focused survey app — log household assessments in assigned zones, offline-first, and track submission history."
              accent={ROLE_ACCENTS.field_officer}
              visible={rolesVisible}
              delayMs={60}
              onClick={() => openSignIn("field_officer")}
            />
            <RoleCard
              title="Shelter officer"
              desc="No account needed — sign in with your shelter's code to update occupancy, supplies and urgent needs from that shelter alone."
              accent={ROLE_ACCENTS.shelter_officer}
              visible={rolesVisible}
              delayMs={120}
              onClick={() => openSignIn("shelter_officer")}
            />
            <RoleCard
              title="Control room"
              desc="Read-only situational awareness — live alerts, red zone status and relocation progress across the district."
              accent={ROLE_ACCENTS.control_room}
              visible={rolesVisible}
              delayMs={180}
              onClick={() => openSignIn("control_room")}
            />
          </div>
        </div>
      </main>

      <footer
        style={{
          position: "relative",
          zIndex: 1,
          flex: "none",
          padding: "16px 40px",
          borderTop: "1px solid var(--border)",
          font: "400 10.5px/1.4 var(--font-data)",
          color: "var(--ink4)",
          textAlign: "center",
        }}
      >
        Prototype · sample data · SIH26191
      </footer>

      {signInOpen && <SignInModal onClose={() => setSignInOpen(false)} initialRole={initialRole} />}
    </div>
  );
}

function RoleCard({
  title,
  desc,
  accent,
  visible,
  delayMs,
  onClick,
}: {
  title: string;
  desc: string;
  accent: string;
  visible: boolean;
  delayMs: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="ps-card-hover ps-role-card"
      style={{
        position: "relative",
        textAlign: "left",
        cursor: "pointer",
        border: "1px solid var(--border)",
        borderRadius: 8,
        background: "var(--panel)",
        padding: "22px 20px 20px",
        font: "inherit",
        color: "inherit",
        overflow: "hidden",
        opacity: visible ? 1 : 0,
        transform: visible ? "none" : "translateY(14px)",
        transition: `opacity 0.5s cubic-bezier(0.2, 0.7, 0.2, 1) ${delayMs}ms, transform 0.5s cubic-bezier(0.2, 0.7, 0.2, 1) ${delayMs}ms, border-color 0.18s, box-shadow 0.18s`,
      }}
    >
      <span style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: accent, opacity: 0.85 }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 8 }}>
        <span style={{ font: "600 15px/1.3 var(--font-interface)", color: "var(--ink)" }}>{title}</span>
        <span className="ps-role-card-arrow" style={{ font: "600 13px/1 var(--font-data)", color: accent }}>
          →
        </span>
      </div>
      <div style={{ font: "400 12.5px/1.6 var(--font-data)", color: "var(--ink3)" }}>{desc}</div>
    </button>
  );
}

function cornerBracketStyle(v: "top" | "bottom", h: "left" | "right") {
  const size = 22;
  return {
    position: "absolute" as const,
    [v]: -8,
    [h]: -8,
    width: size,
    height: size,
    borderTop: v === "top" ? "2px solid var(--accent)" : undefined,
    borderBottom: v === "bottom" ? "2px solid var(--accent)" : undefined,
    borderLeft: h === "left" ? "2px solid var(--accent)" : undefined,
    borderRight: h === "right" ? "2px solid var(--accent)" : undefined,
    opacity: 0.55,
    pointerEvents: "none" as const,
    zIndex: 2,
  };
}

const signInOutlineStyle = {
  padding: "10px 16px",
  borderRadius: 5,
  border: "1px solid var(--accent)",
  background: "transparent",
  color: "var(--accent)",
  font: "600 12px/1 var(--font-interface)",
  cursor: "pointer",
} as const;

const heroButtonStyle = {
  padding: "15px 26px",
  borderRadius: 6,
  border: "1px solid var(--accent)",
  background: "var(--accent)",
  color: "var(--on-accent)",
  font: "600 14px/1 var(--font-interface)",
  cursor: "pointer",
} as const;
