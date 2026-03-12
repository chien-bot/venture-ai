"use client";
import { Scores } from "@/lib/types";

const LABELS: Record<string, string> = {
  empathy: "痛点",
  ideation: "方案",
  business: "商业",
  execution: "执行",
  pitching: "路演",
};

export default function ScoreRadar({ scores }: { scores: Scores | null }) {
  if (!scores) return null;

  const keys = Object.keys(LABELS);
  const maxScore = 10;
  const size = 180;
  const center = size / 2;
  const radius = 68;
  const angleStep = (2 * Math.PI) / keys.length;

  const getPoint = (index: number, value: number) => {
    const angle = angleStep * index - Math.PI / 2;
    const r = (value / maxScore) * radius;
    return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) };
  };

  const polygonPoints = keys
    .map((key, i) => {
      const p = getPoint(i, (scores as any)[key] || 0);
      return `${p.x},${p.y}`;
    })
    .join(" ");

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`-12 -12 ${size + 24} ${size + 24}`}>
        <defs>
          <radialGradient id="radarFill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.1" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Grid rings */}
        {[2, 4, 6, 8, 10].map((level) => (
          <polygon
            key={level}
            points={keys.map((_, i) => {
              const p = getPoint(i, level);
              return `${p.x},${p.y}`;
            }).join(" ")}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        ))}

        {/* Axes */}
        {keys.map((_, i) => {
          const p = getPoint(i, maxScore);
          return <line key={i} x1={center} y1={center} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />;
        })}

        {/* Data fill */}
        <polygon points={polygonPoints} fill="url(#radarFill)" stroke="none" />

        {/* Data border */}
        <polygon
          points={polygonPoints}
          fill="none"
          stroke="#818cf8"
          strokeWidth="1.5"
          filter="url(#glow)"
        />

        {/* Data dots */}
        {keys.map((key, i) => {
          const p = getPoint(i, (scores as any)[key] || 0);
          return (
            <g key={key}>
              <circle cx={p.x} cy={p.y} r="5" fill="#6366f1" opacity="0.3" />
              <circle cx={p.x} cy={p.y} r="3" fill="#818cf8" />
            </g>
          );
        })}

        {/* Labels */}
        {keys.map((key, i) => {
          const p = getPoint(i, maxScore + 3);
          const val = (scores as any)[key] || 0;
          return (
            <text
              key={key}
              x={p.x}
              y={p.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="10"
              fill={val >= 7 ? "#6ee7b7" : val >= 5 ? "#fcd34d" : "#94a3b8"}
              fontWeight="600"
            >
              {LABELS[key]}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
