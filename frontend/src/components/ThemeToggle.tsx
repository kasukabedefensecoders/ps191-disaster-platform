import { useTheme } from "../lib/ThemeContext";

/** Ported from PROTOTYPE/PS191 Platform.dc.html's theme-toggle chip: two
 * overlapping dots (accent = dark, sev3 = light) whose opacity swaps, plus
 * a mono label — not a generic switch component. */
export default function ThemeToggle({ compact }: { compact?: boolean }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      onClick={toggleTheme}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="ps-icon-btn"
      style={{
        flex: "none",
        display: "flex",
        alignItems: "center",
        gap: 7,
        padding: "6px 10px",
        borderRadius: 4,
        border: "1px solid var(--border2)",
        background: "var(--track)",
        cursor: "pointer",
        marginLeft: compact ? 0 : 12,
      }}
    >
      <span style={{ width: 11, height: 11, borderRadius: "50%", border: "1.5px solid var(--accent)", background: "var(--accent)", opacity: isDark ? 1 : 0 }} />
      <span style={{ width: 11, height: 11, borderRadius: "50%", border: "1.5px solid var(--sev3)", marginLeft: -18, opacity: isDark ? 0 : 1 }} />
      <span style={{ font: "500 10px/1 var(--font-data)", letterSpacing: "0.06em", color: "var(--ink2)" }}>{isDark ? "DARK" : "LIGHT"}</span>
    </button>
  );
}
