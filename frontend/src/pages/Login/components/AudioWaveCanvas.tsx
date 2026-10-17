// frontend/src/pages/Login/components/AudioWaveCanvas.tsx
import React, { useEffect, useRef, useCallback } from "react";

interface AudioWaveCanvasProps {
  isDark: boolean;
  amplitudeBoost?: number; // 0–1, raised when typing
  errorState?: boolean;    // tint red on error
  submitPulse?: boolean;   // bright travelling pulse on submit
  "aria-hidden"?: boolean;
}

const BAR_WIDTH = 3;
const BAR_GAP = 5;
const BAR_STEP = BAR_WIDTH + BAR_GAP; // 8px

export const AudioWaveCanvas: React.FC<AudioWaveCanvasProps> = ({
  isDark,
  amplitudeBoost = 0,
  errorState = false,
  submitPulse = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const phaseRef = useRef(0);
  const pulseOffsetRef = useRef(0);
  const sizeRef = useRef({ w: 0, h: 0 });

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { w: W, h: H } = sizeRef.current;
    if (W <= 0 || H <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.scale(dpr, dpr);

    const phase = phaseRef.current;
    const pulse = pulseOffsetRef.current;

    // Number of bars that fit horizontally
    const numBars = Math.max(2, Math.floor(W / BAR_STEP));

    // Maximum height: 50% of viewport height (capped at 420px)
    const maxBarH = Math.min(H * 0.5, 420);

    for (let i = 0; i < numBars; i++) {
      // t goes from 0.0 at far left to 1.0 at card edge
      const t = i / (numBars - 1);
      // Anchor bars so the rightmost bar aligns exactly with the right edge (x = W - BAR_WIDTH)
      const x = W - BAR_WIDTH - (numBars - 1 - i) * BAR_STEP;

      // Easing curve: height eases upward toward the card (small at far left, tallest at card edge)
      const ease = Math.pow(t, 1.4);
      const envelope = 0.06 + 0.94 * ease;

      // Voice multi-frequency shape
      const v1 = Math.sin(i * 0.42 + phase * 2.4);
      const v2 = Math.cos(i * 0.73 - phase * 1.5);
      const v3 = Math.sin(i * 1.15 + phase * 3.1);
      const voiceRaw = Math.abs(0.52 * v1 + 0.32 * v2 + 0.16 * v3);
      const voice = 0.22 + 0.78 * voiceRaw;

      const boost = 1 + amplitudeBoost * 0.5;
      const barH = Math.max(4, voice * envelope * maxBarH * boost);
      const y = (H - barH) / 2;

      // Smooth mask: bars fade in from far-left edge
      const edgeFade = t < 0.14 ? Math.pow(t / 0.14, 1.5) : 1;

      // Submit pulse: bright wave sweeping across
      let pulseGlow = 0;
      if (submitPulse) {
        const dist = Math.abs(t - (pulse % 1));
        pulseGlow = Math.max(0, 1 - dist / 0.18);
      }

      // Color scheme based on theme tokens
      // Light theme: brand blue-violet-red gradient
      // Dark theme: cool white-blue
      let barColor = "";
      if (errorState) {
        const alpha = (0.4 + 0.55 * t + pulseGlow * 0.3) * edgeFade;
        barColor = `rgba(239, 68, 68, ${alpha})`;
      } else if (isDark) {
        // Dark theme: cool cyan -> ice blue -> glowing white
        const alpha = Math.min(1, (0.28 + 0.68 * t + pulseGlow * 0.4) * edgeFade);
        if (pulseGlow > 0.4) {
          barColor = `rgba(255, 255, 255, ${alpha})`;
        } else if (t < 0.45) {
          // cool sky blue
          barColor = `rgba(56, 189, 248, ${alpha})`;
        } else if (t < 0.8) {
          // ice blue
          barColor = `rgba(186, 230, 253, ${alpha})`;
        } else {
          // glowing cool white
          barColor = `rgba(241, 245, 249, ${alpha})`;
        }
      } else {
        // Light theme: brand blue -> violet -> red
        const alpha = Math.min(1, (0.35 + 0.6 * t + pulseGlow * 0.35) * edgeFade);
        if (pulseGlow > 0.4) {
          barColor = `rgba(220, 38, 38, ${alpha})`;
        } else if (t < 0.4) {
          // brand blue (59, 130, 246)
          barColor = `rgba(59, 130, 246, ${alpha})`;
        } else if (t < 0.75) {
          // violet (139, 92, 246)
          barColor = `rgba(139, 92, 246, ${alpha})`;
        } else {
          // brand red (220, 38, 38)
          barColor = `rgba(220, 38, 38, ${alpha})`;
        }
      }

      ctx.fillStyle = barColor;
      ctx.beginPath();
      // Thin rounded bar (3px wide with pill ends)
      ctx.roundRect(x, y, BAR_WIDTH, barH, 1.5);
      ctx.fill();
    }

    // Soft glow where waveform meets the card (at x = W)
    const glowRadius = Math.min(100, W * 0.3);
    const glowGrad = ctx.createRadialGradient(W, H / 2, 0, W, H / 2, glowRadius);
    const glowColor = errorState
      ? "rgba(239, 68, 68,"
      : isDark
      ? "rgba(56, 189, 248,"
      : "rgba(220, 38, 38,";
    glowGrad.addColorStop(0, `${glowColor} 0.22)`);
    glowGrad.addColorStop(0.5, `${glowColor} 0.08)`);
    glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(W, H / 2, glowRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }, [isDark, amplitudeBoost, errorState, submitPulse]);

  // Handle canvas sizing with dpr
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const updateSize = () => {
      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const cssW = Math.round(rect.width);
      const cssH = Math.round(rect.height);

      if (cssW === 0 || cssH === 0) return;

      canvas.width = Math.round(cssW * dpr);
      canvas.height = Math.round(cssH * dpr);
      canvas.style.width = `${cssW}px`;
      canvas.style.height = `${cssH}px`;
      sizeRef.current = { w: cssW, h: cssH };
      draw();
    };

    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(container);

    let isHidden = false;
    const onVisibility = () => {
      isHidden = document.hidden;
    };
    document.addEventListener("visibilitychange", onVisibility);

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const animate = () => {
      if (!isHidden) {
        phaseRef.current += prefersReduced ? 0 : 0.024;
        if (submitPulse) pulseOffsetRef.current += 0.016;
        draw();
      }
      rafRef.current = requestAnimationFrame(animate);
    };
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [draw, submitPulse]);

  return (
    <div ref={containerRef} className="w-full h-full relative overflow-hidden pointer-events-none">
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  );
};
