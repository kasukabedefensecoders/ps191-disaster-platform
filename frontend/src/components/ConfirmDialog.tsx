import { useEffect, useState, type CSSProperties } from "react";

/** A styled stand-in for window.confirm() — same overlay/card treatment and
 * enter/exit animation as SignInModal (data-modal-overlay/data-modal-card
 * in tokens.css), so a destructive-action confirmation doesn't jump out of
 * the app's own visual language into an unstyled native browser dialog.
 * Only ever mounted while open (parent conditionally renders it), so
 * "closing" here always means an animated exit, unlike SignInModal's
 * success path which can skip it. */
export default function ConfirmDialog({
  title,
  body,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [closing, setClosing] = useState(false);

  const requestClose = (action: () => void) => {
    setClosing(true);
    setTimeout(action, 150);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") requestClose(onCancel);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label={title}
      onClick={() => requestClose(onCancel)}
      data-modal-overlay=""
      data-closing={closing}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1100,
        background: "rgba(4, 8, 18, 0.6)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        data-modal-card=""
        data-closing={closing}
        style={{
          width: "100%",
          maxWidth: 380,
          background: "var(--bg2)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          boxShadow: "var(--shadow)",
          padding: 24,
        }}
      >
        <div style={{ font: "600 16px/1.3 var(--font-interface)", color: "var(--ink)", marginBottom: 10 }}>{title}</div>
        <div style={{ font: "400 12.5px/1.6 var(--font-interface)", color: "var(--ink3)", marginBottom: 20 }}>{body}</div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button type="button" onClick={() => requestClose(onCancel)} className="ps-btn-outline" style={cancelButtonStyle}>
            Cancel
          </button>
          <button type="button" onClick={() => requestClose(onConfirm)} className="ps-btn-primary" style={confirmButtonStyle}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

const cancelButtonStyle: CSSProperties = {
  padding: "9px 15px",
  borderRadius: 5,
  border: "1px solid var(--border2)",
  background: "transparent",
  color: "var(--ink2)",
  font: "600 12.5px/1 var(--font-interface)",
  cursor: "pointer",
};

const confirmButtonStyle: CSSProperties = {
  padding: "9px 15px",
  borderRadius: 5,
  border: "1px solid var(--accent)",
  background: "var(--accent)",
  color: "var(--on-accent)",
  font: "600 12.5px/1 var(--font-interface)",
  cursor: "pointer",
};
