import { useEffect, useRef, useState } from "react";

const DURATION_MS = 800;
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

/** Animates a number counting up (or down) to `value` on mount and whenever
 * it changes thereafter, rendered through `format` each frame — the one
 * deliberately bold motion moment on the dashboard's KPI numbers, not
 * applied everywhere else. This dashboard doesn't poll, so every mount is a
 * deliberate page visit (a real "reveal" moment worth counting up to), and
 * every later change is a real state change (a status advanced, data
 * reset) worth the same brief motion rather than a silent jump. Skips the
 * animation entirely under prefers-reduced-motion.
 *
 * Reads its animation's starting point from the currently *displayed*
 * value (via displayRef, a live mirror of `display`) rather than a separate
 * "last seen value" ref mutated inside the effect. That distinction matters
 * under React 18 StrictMode's dev-only double-invoke-on-mount: cancelling
 * the first invocation's rAF before it ever paints a frame leaves `display`
 * untouched, so the second invocation still sees the true starting point
 * (0) and animates normally. A "last seen value" ref mutated unconditionally
 * at the top of the effect gets updated by the first (cancelled) invocation
 * regardless, so the second invocation sees from === value and silently
 * skips animating — the number would just sit at 0 forever despite the
 * prop being correct from the very first render. Caught by actually loading
 * the dashboard and checking the numbers against the API, not by the
 * type-checker or a static review of the animation logic. */
export default function CountUp({ value, format }: { value: number; format?: (n: number) => string }) {
  const fmt = format ?? ((n: number) => n.toLocaleString("en-IN"));
  const [display, setDisplay] = useState(0);
  const displayRef = useRef(0);
  displayRef.current = display;
  const rafRef = useRef(0);

  useEffect(() => {
    const from = displayRef.current;
    if (from === value) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setDisplay(value);
      return;
    }

    const start = performance.now();
    cancelAnimationFrame(rafRef.current);
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DURATION_MS);
      setDisplay(from + (value - from) * easeOutCubic(t));
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value]);

  return <>{fmt(Math.round(display))}</>;
}
