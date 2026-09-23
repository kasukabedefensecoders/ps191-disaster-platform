import { useEffect, useRef } from "react";

import type { Theme } from "../lib/ThemeContext";

/** Ambient hero visual for the public landing page — a drifting particle
 * field with a mouse-driven parallax tilt (a cheap stand-in for a full 3D
 * scene; no WebGL/three.js dependency for what's a decorative background,
 * not a data view). Deliberately not tied to real zone coordinates: this
 * renders before login, and real hazard geometry stays behind auth like
 * everywhere else in this app — the points here are ambient decoration,
 * not a claim about actual Dima Hasao zones. */

interface Particle {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
}

const PARTICLE_COUNT = 90;
const LINK_DISTANCE = 130;

function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

const THEME_COLOR = {
  dark: { particle: "6, 190, 225", link: "38, 60, 100", glow: "6, 190, 225" },
  light: { particle: "47, 111, 224", link: "180, 195, 220", glow: "47, 111, 224" },
};

export default function ParticleField({ theme = "dark" }: { theme?: Theme }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const themeRef = useRef(theme);
  themeRef.current = theme;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const rand = seededRandom(42);
    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let mouseX = 0.5;
    let mouseY = 0.5;
    let raf = 0;
    let alive = true;

    const particles: Particle[] = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: rand(),
      y: rand(),
      z: rand(), // depth: 0 (far) .. 1 (near) — drives parallax strength and size
      vx: (rand() - 0.5) * 0.00025,
      vy: (rand() - 0.5) * 0.00025,
    }));

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = (e.clientX - rect.left) / rect.width;
      mouseY = (e.clientY - rect.top) / rect.height;
    };
    canvas.addEventListener("mousemove", onMouseMove);

    const draw = () => {
      if (!alive) return;
      const colors = THEME_COLOR[themeRef.current];
      ctx.clearRect(0, 0, width, height);

      const parallaxX = (mouseX - 0.5) * 26;
      const parallaxY = (mouseY - 0.5) * 18;

      const projected = particles.map((p) => {
        if (!reduceMotion) {
          p.x += p.vx;
          p.y += p.vy;
          if (p.x < 0 || p.x > 1) p.vx *= -1;
          if (p.y < 0 || p.y > 1) p.vy *= -1;
        }
        const depth = 0.4 + p.z * 0.6;
        return {
          sx: p.x * width + parallaxX * depth,
          sy: p.y * height + parallaxY * depth,
          z: p.z,
        };
      });

      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const a = projected[i];
          const b = projected[j];
          const dx = a.sx - b.sx;
          const dy = a.sy - b.sy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < LINK_DISTANCE) {
            const alpha = (1 - dist / LINK_DISTANCE) * 0.35 * ((a.z + b.z) / 2);
            ctx.strokeStyle = `rgba(${colors.link}, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.sx, a.sy);
            ctx.lineTo(b.sx, b.sy);
            ctx.stroke();
          }
        }
      }

      for (const p of projected) {
        const radius = 1 + p.z * 2.2;
        ctx.beginPath();
        ctx.fillStyle = `rgba(${colors.particle}, ${0.35 + p.z * 0.5})`;
        ctx.arc(p.sx, p.sy, radius, 0, Math.PI * 2);
        ctx.fill();
      }

      if (!reduceMotion) raf = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      alive = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      canvas.removeEventListener("mousemove", onMouseMove);
    };
  }, []);

  return <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />;
}
