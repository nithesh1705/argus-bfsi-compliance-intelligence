// frontend/src/pages/Login/components/FindingConnectors.tsx
import React, { useEffect, useRef, useCallback, useState } from "react";

interface ConnectorPoint {
  x: number;
  y: number;
}

interface PathState {
  origin: ConnectorPoint;
  targets: ConnectorPoint[];
}

interface FindingConnectorsProps {
  stageRef: React.RefObject<HTMLDivElement | null>;
  cardRef: React.RefObject<HTMLDivElement | null>;
  findingRefs: Array<React.RefObject<HTMLDivElement | null>>;
  isDark: boolean;
  submitPulse?: boolean;
  prefersReducedMotion?: boolean;
}

// 70% opacity theme tokens per card (red, violet, green)
const LINE_COLORS = [
  "rgba(239, 68, 68, 0.70)",   // Card 0: red
  "rgba(168, 85, 247, 0.70)",  // Card 1: violet
  "rgba(16, 185, 129, 0.70)",  // Card 2: emerald
];

const SOLID_COLORS = [
  "rgb(239, 68, 68)",
  "rgb(168, 85, 247)",
  "rgb(16, 185, 129)",
];

export const FindingConnectors: React.FC<FindingConnectorsProps> = ({
  stageRef,
  cardRef,
  findingRefs,
  isDark,
  submitPulse = false,
  prefersReducedMotion = false,
}) => {
  const [paths, setPaths] = useState<PathState | null>(null);
  const [stageDims, setStageDims] = useState<{ w: number; h: number }>({ w: 0, h: 0 });

  const measure = useCallback(() => {
    const stage = stageRef.current;
    const card = cardRef.current;
    if (!stage || !card) return;

    const stageRect = stage.getBoundingClientRect();
    const cardRect = card.getBoundingClientRect();

    if (stageRect.width === 0 || stageRect.height === 0) return;

    // Output node at the vertical middle of login card's right edge
    const origin: ConnectorPoint = {
      x: cardRect.right - stageRect.left,
      y: cardRect.top + cardRect.height / 2 - stageRect.top,
    };

    // Target nodes at the left-edge middle of each finding card
    const targets: ConnectorPoint[] = [];
    for (let i = 0; i < findingRefs.length; i++) {
      const el = findingRefs[i]?.current;
      if (!el) continue;
      const r = el.getBoundingClientRect();
      targets.push({
        x: r.left - stageRect.left,
        y: r.top + r.height / 2 - stageRect.top,
      });
    }

    // In development, log a warning if fewer than 3 paths render or any anchor is 0 or NaN
    if (process.env.NODE_ENV !== "production" || import.meta.env.DEV) {
      if (targets.length < 3) {
        console.warn(`[FindingConnectors] Expected 3 paths, got ${targets.length}`);
      }
      if (
        isNaN(origin.x) ||
        isNaN(origin.y) ||
        origin.x === 0 ||
        origin.y === 0 ||
        targets.some((t) => isNaN(t.x) || isNaN(t.y) || t.x === 0 || t.y === 0)
      ) {
        console.warn("[FindingConnectors] Anchor point is 0 or NaN:", { origin, targets });
      }
    }

    if (targets.length === findingRefs.length) {
      setPaths({ origin, targets });
      setStageDims({ w: stageRect.width, h: stageRect.height });
    }
  }, [stageRef, cardRef, findingRefs]);

  useEffect(() => {
    // Measure immediately on mount
    measure();

    // Re-measure after animation frame & timeout to catch layout shifts & card animation settle
    const rafId = requestAnimationFrame(measure);
    const t1 = setTimeout(measure, 60);
    const t2 = setTimeout(measure, 350);

    // Re-measure after fonts load
    if (document.fonts?.ready) {
      document.fonts.ready.then(() => measure());
    }

    // Re-measure on window resize
    window.addEventListener("resize", measure);

    // Sized to the stage with a ResizeObserver
    const ro = new ResizeObserver(() => {
      measure();
    });

    if (stageRef.current) ro.observe(stageRef.current);
    if (cardRef.current) ro.observe(cardRef.current);
    findingRefs.forEach((r) => {
      if (r.current) ro.observe(r.current);
    });

    return () => {
      cancelAnimationFrame(rafId);
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener("resize", measure);
      ro.disconnect();
    };
  }, [measure, stageRef, cardRef, findingRefs, isDark]);

  if (!paths || stageDims.w === 0 || stageDims.h === 0) {
    return null;
  }

  const { origin, targets } = paths;

  // Build smooth cubic Bezier path with horizontal tangents
  const buildPath = (o: ConnectorPoint, t: ConnectorPoint) => {
    const dx = t.x - o.x;
    const cp1x = o.x + dx * 0.5;
    const cp1y = o.y;
    const cp2x = t.x - dx * 0.5;
    const cp2y = t.y;
    return `M ${o.x} ${o.y} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${t.x} ${t.y}`;
  };

  const originRingColor = isDark ? "rgba(148, 163, 184, 0.7)" : "rgba(100, 116, 139, 0.7)";
  const originDotColor = isDark ? "#f1f5f9" : "#0f172a";

  return (
    <svg
      aria-hidden="true"
      className="absolute inset-0 w-full h-full pointer-events-none overflow-visible"
      style={{ zIndex: 12 }}
      viewBox={`0 0 ${stageDims.w} ${stageDims.h}`}
      preserveAspectRatio="none"
    >
      <defs>
        {/* Glow filters for pulse dots */}
        {SOLID_COLORS.map((col, i) => (
          <filter key={`glow-${i}`} id={`connector-glow-${i}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        ))}
      </defs>

      {/* ─── Base cubic Bezier connector lines (1.75px) ───────────────────────── */}
      {targets.map((t, i) => {
        const pathD = buildPath(origin, t);
        return (
          <g key={`path-group-${i}`}>
            {/* Background subtle guide line */}
            <path
              d={pathD}
              fill="none"
              stroke={LINE_COLORS[i]}
              strokeWidth={1.75}
              strokeLinecap="round"
              className="pointer-events-none"
            />

            {/* Animated travelling pulse along path using stroke-dashoffset */}
            {!prefersReducedMotion && (
              <path
                d={pathD}
                fill="none"
                stroke={SOLID_COLORS[i]}
                strokeWidth={2.5}
                strokeDasharray="24 140"
                strokeLinecap="round"
                className="pointer-events-none connector-pulse-line"
                style={{
                  animation: `connectorPulseDash ${submitPulse ? "1.2s" : "2.6s"} linear infinite`,
                  animationDelay: `${-i * 0.75}s`,
                  opacity: 0.9,
                }}
              />
            )}

            {/* Animated travelling pulse dot along the path */}
            {!prefersReducedMotion && (
              <circle
                r={submitPulse ? 4.5 : 3.5}
                fill={SOLID_COLORS[i]}
                filter={`url(#connector-glow-${i})`}
                className="pointer-events-none"
              >
                <animateMotion
                  path={pathD}
                  dur={submitPulse ? "1.2s" : "2.6s"}
                  repeatCount="indefinite"
                  begin={`${-i * 0.75}s`}
                  calcMode="spline"
                  keyTimes="0;1"
                  keySplines="0.45 0 0.55 1"
                />
              </circle>
            )}
          </g>
        );
      })}

      {/* ─── Output Node at vertical middle of login card right edge ─────────── */}
      {/* Outer ring */}
      <circle
        cx={origin.x}
        cy={origin.y}
        r={7}
        fill={isDark ? "#0f172a" : "#ffffff"}
        stroke={originRingColor}
        strokeWidth={1.5}
        className="pointer-events-none"
      />
      {/* Center dot (radius ~4) */}
      <circle
        cx={origin.x}
        cy={origin.y}
        r={4}
        fill={originDotColor}
        className="pointer-events-none"
      />

      {/* ─── Input Nodes at left-edge middle of each finding card ────────────── */}
      {targets.map((t, i) => (
        <g key={`target-node-${i}`}>
          {/* Outer ring */}
          <circle
            cx={t.x}
            cy={t.y}
            r={7}
            fill={isDark ? "#0f172a" : "#ffffff"}
            stroke={LINE_COLORS[i]}
            strokeWidth={1.5}
            className="pointer-events-none"
          />
          {/* Center node dot (radius ~4) */}
          <circle
            cx={t.x}
            cy={t.y}
            r={4}
            fill={SOLID_COLORS[i]}
            className="pointer-events-none"
          />
        </g>
      ))}

      {/* CSS Keyframe for travelling pulse */}
      <style>{`
        @keyframes connectorPulseDash {
          from {
            stroke-dashoffset: 164;
          }
          to {
            stroke-dashoffset: 0;
          }
        }
      `}</style>
    </svg>
  );
};
