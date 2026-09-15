import type { RiskLevel } from "../types";

const levelMap: Record<RiskLevel, { label: string; className: string }> = {
  normal: { label: "一般关注", className: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  attention: { label: "建议关注", className: "bg-amber-50 text-amber-700 ring-amber-200" },
  high_attention: { label: "重点关注", className: "bg-rose-50 text-rose-700 ring-rose-200" },
};

export function LevelBadge({ level }: { level: RiskLevel }) {
  const style = levelMap[level];
  return <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ring-1 ring-inset ${style.className}`}>{style.label}</span>;
}
