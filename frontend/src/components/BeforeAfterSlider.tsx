import { useState, type CSSProperties } from "react";

/** Ported from PROTOTYPE/PS191 Platform.dc.html's SAR change-detection
 * screen (lines ~1168-1189): a full "after" image with a "before" image
 * clipped to a draggable split, a range input driving the same split. */
export default function BeforeAfterSlider({ beforeSrc, afterSrc }: { beforeSrc: string; afterSrc: string }) {
  const [split, setSplit] = useState(50);

  return (
    <div>
      <div style={{ position: "relative", height: 340, overflow: "hidden", background: "#0a0f1c" }}>
        <img src={afterSrc} alt="After" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
        <div style={{ position: "absolute", inset: 0, width: `${split}%`, overflow: "hidden", borderRight: "2px solid var(--accent)" }}>
          <img
            src={beforeSrc}
            alt="Before"
            style={{ position: "absolute", inset: 0, width: "100vw", maxWidth: "none", height: "100%", objectFit: "cover" }}
          />
          <Corner label="BEFORE" style={{ left: 18 }} />
        </div>
        <Corner label="AFTER" style={{ right: 18 }} />
      </div>
      <div style={{ padding: "14px 16px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 12 }}>
        <span style={sideLabelStyle}>BEFORE</span>
        <input
          type="range"
          min={0}
          max={100}
          value={split}
          onChange={(e) => setSplit(Number(e.target.value))}
          style={{ flex: 1, accentColor: "var(--accent)", background: "transparent", cursor: "ew-resize" }}
        />
        <span style={sideLabelStyle}>AFTER</span>
      </div>
    </div>
  );
}

function Corner({ label, style }: { label: string; style: CSSProperties }) {
  return (
    <div
      style={{
        position: "absolute",
        top: 14,
        padding: "5px 8px",
        borderRadius: 3,
        background: "rgba(7,11,22,.85)",
        border: "1px solid var(--border2)",
        font: "500 10px/1 var(--font-data)",
        color: "var(--ink3)",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {label}
    </div>
  );
}

const sideLabelStyle = {
  font: "500 10px/1 var(--font-data)",
  letterSpacing: "0.06em",
  color: "var(--ink4)",
} as const;
