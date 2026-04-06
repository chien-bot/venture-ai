"use client";

const RUBRIC_LABELS: Record<string, string> = {
  R1: "痛点", R2: "用户", R3: "可行性",
  R4: "商业", R5: "竞争", R6: "财务",
  R7: "创新", R8: "团队", R9: "表达",
  R10: "合规", R11: "增长",
};

type RubricData = Record<string, { score: number; evidence?: string; suggestion?: string }>;

export default function RubricRadar({ data, maxScore = 5 }: { data: RubricData; maxScore?: number }) {
  const keys = Object.keys(data).filter(k => k.startsWith("R")).sort((a, b) => {
    const na = parseInt(a.slice(1)), nb = parseInt(b.slice(1));
    return na - nb;
  });

  if (keys.length < 3) return null;

  const size = 220;
  const center = size / 2;
  const radius = 80;
  const n = keys.length;
  const angleStep = (2 * Math.PI) / n;

  const getPoint = (index: number, value: number) => {
    const angle = angleStep * index - Math.PI / 2;
    const r = (value / maxScore) * radius;
    return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) };
  };

  const polygonPoints = keys
    .map((key, i) => {
      const p = getPoint(i, data[key]?.score || 0);
      return `${p.x},${p.y}`;
    })
    .join(" ");

  const total = keys.reduce((s, k) => s + (data[k]?.score || 0), 0);
  const avg = (total / keys.length).toFixed(1);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`-18 -18 ${size + 36} ${size + 36}`}>
        <defs>
          <radialGradient id="rubricFill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.08" />
          </radialGradient>
          <filter id="rubricGlow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Grid rings */}
        {Array.from({ length: maxScore }, (_, l) => l + 1).map((level) => (
          <polygon
            key={level}
            points={keys.map((_, i) => {
              const p = getPoint(i, level);
              return `${p.x},${p.y}`;
            }).join(" ")}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="0.8"
          />
        ))}

        {/* Axes */}
        {keys.map((_, i) => {
          const p = getPoint(i, maxScore);
          return <line key={i} x1={center} y1={center} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.05)" strokeWidth="0.8" />;
        })}

        {/* Data fill */}
        <polygon points={polygonPoints} fill="url(#rubricFill)" stroke="none" />

        {/* Data border */}
        <polygon
          points={polygonPoints}
          fill="none"
          stroke="#fbbf24"
          strokeWidth="1.5"
          filter="url(#rubricGlow)"
        />

        {/* Data dots */}
        {keys.map((key, i) => {
          const score = data[key]?.score || 0;
          const p = getPoint(i, score);
          const dotColor = score >= 4 ? "#34d399" : score >= 3 ? "#fbbf24" : "#f87171";
          return (
            <g key={key}>
              <circle cx={p.x} cy={p.y} r="4" fill={dotColor} opacity="0.3" />
              <circle cx={p.x} cy={p.y} r="2.5" fill={dotColor} />
            </g>
          );
        })}

        {/* Labels */}
        {keys.map((key, i) => {
          const p = getPoint(i, maxScore + 2.2);
          const score = data[key]?.score || 0;
          const color = score >= 4 ? "#6ee7b7" : score >= 3 ? "#fcd34d" : "#fca5a5";
          return (
            <text
              key={key}
              x={p.x}
              y={p.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="8"
              fill={color}
              fontWeight="600"
            >
              {RUBRIC_LABELS[key] || key}
            </text>
          );
        })}

        {/* Center average */}
        <text x={center} y={center - 5} textAnchor="middle" fontSize="14" fill="#fbbf24" fontWeight="bold">
          {avg}
        </text>
        <text x={center} y={center + 8} textAnchor="middle" fontSize="7" fill="rgba(255,255,255,0.4)">
          均分
        </text>
      </svg>
    </div>
  );
}
