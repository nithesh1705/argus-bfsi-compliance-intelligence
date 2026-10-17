import React, { useEffect, useRef } from "react";
import { Mic, Radio, Volume2 } from "lucide-react";

interface AudioWaveVisualizerProps {
  isDark: boolean;
}

export const AudioWaveVisualizer: React.FC<AudioWaveVisualizerProps> = ({ isDark }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let phase = 0;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      const midY = height / 2;

      ctx.clearRect(0, 0, width, height);

      // Subtle center guide line
      ctx.beginPath();
      ctx.strokeStyle = isDark ? "rgba(148, 163, 184, 0.12)" : "rgba(100, 116, 139, 0.15)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();
      ctx.setLineDash([]);

      // Primary Speech Wave (RM Channel)
      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = isDark ? "rgba(148, 163, 184, 0.75)" : "rgba(71, 85, 105, 0.8)";
      for (let x = 0; x < width; x += 2) {
        // Multi-frequency harmonic envelope simulating human voice modulation
        const envelope = Math.sin((x / width) * Math.PI); // tapered at ends
        const voiceMod = Math.sin(x * 0.04 + phase * 2.5) * 0.5 + Math.cos(x * 0.02 - phase) * 0.5;
        const y = midY + Math.sin(x * 0.05 + phase) * 22 * envelope * voiceMod;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Secondary Speech Wave (Customer Channel - Subtle Intertwined)
      ctx.beginPath();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = isDark ? "rgba(203, 213, 225, 0.45)" : "rgba(148, 163, 184, 0.6)";
      for (let x = 0; x < width; x += 2) {
        const envelope = Math.sin((x / width) * Math.PI);
        const y = midY + Math.cos(x * 0.035 - phase * 1.8) * 15 * envelope;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Continuous Speech Waveform Oscillogram Bars (Vertical lines matching hand-drawn sketch)
      const numBars = 36;
      const spacing = width / numBars;
      for (let i = 0; i < numBars; i++) {
        const barX = i * spacing + spacing / 2;
        const normPos = i / numBars;
        const envelope = Math.sin(normPos * Math.PI); // bell curve envelope
        // Dynamic organic voice height
        const barHeight =
          (Math.abs(Math.sin(i * 0.8 + phase * 3.5)) * 26 +
            Math.abs(Math.cos(i * 1.3 - phase * 2.0)) * 18) *
          envelope +
          3;

        ctx.beginPath();
        ctx.strokeStyle = isDark
          ? i % 4 === 0
            ? "rgba(226, 232, 240, 0.65)"
            : "rgba(148, 163, 184, 0.4)"
          : i % 4 === 0
          ? "rgba(51, 65, 85, 0.7)"
          : "rgba(100, 116, 139, 0.45)";
        ctx.lineWidth = 2.5;
        ctx.lineCap = "round";
        ctx.moveTo(barX, midY - barHeight);
        ctx.lineTo(barX, midY + barHeight);
        ctx.stroke();
      }

      phase += 0.035;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [isDark]);

  return (
    <div className="flex flex-col items-center justify-center w-full max-w-[340px] px-2 select-none">
      {/* Top Badge: Live Voice Channel */}
      <div className="flex items-center justify-between w-full mb-3 px-3 py-1.5 rounded-full bg-white/70 dark:bg-slate-900/70 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-md shadow-sm">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
          <span className="text-[11px] font-mono font-semibold text-slate-700 dark:text-slate-300">
            RM ⟷ Customer Call
          </span>
        </div>
        <div className="flex items-center gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-400">
          <Radio className="w-3 h-3 text-blue-500 animate-pulse" />
          <span>16 kHz PCM</span>
        </div>
      </div>

      {/* The Continuous Oscilloscope Audio Wave (Canvas) */}
      <div className="relative w-full h-28 rounded-2xl bg-white/50 dark:bg-slate-900/50 border border-slate-200/70 dark:border-slate-800/70 backdrop-blur-md shadow-inner flex items-center justify-center p-2 overflow-hidden group">
        <canvas
          ref={canvasRef}
          width={320}
          height={100}
          className="w-full h-full object-contain"
        />

        {/* Ambient subtle vignette */}
        <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-slate-50/80 dark:from-slate-950/80 to-transparent pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-slate-50/80 dark:from-slate-950/80 to-transparent pointer-events-none" />
      </div>

      {/* Acoustic Diarization Metadata */}
      <div className="mt-3 w-full flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 px-2">
        <span className="flex items-center gap-1.5">
          <Volume2 className="w-3.5 h-3.5 text-slate-400" />
          Continuous Acoustic Wave
        </span>
        <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          Streaming
        </span>
      </div>

      {/* Subtle speech citation quote */}
      <div className="mt-2.5 w-full p-2.5 rounded-xl bg-slate-100/70 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60 text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed italic text-center">
        &ldquo;...guaranteed 18% return with zero capital risk...&rdquo;
      </div>
    </div>
  );
};
