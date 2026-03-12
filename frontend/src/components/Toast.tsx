"use client";
import { useEffect, useState } from "react";

export type ToastType = "success" | "error" | "info";

interface ToastProps {
  message: string;
  type?: ToastType;
  duration?: number;
  onClose: () => void;
}

const STYLES: Record<ToastType, { bg: string; border: string; icon: string; color: string }> = {
  success: { bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", icon: "✓", color: "#6ee7b7" },
  error:   { bg: "rgba(239,68,68,0.12)",  border: "rgba(239,68,68,0.3)",  icon: "✕", color: "#fca5a5" },
  info:    { bg: "rgba(99,102,241,0.12)", border: "rgba(99,102,241,0.3)", icon: "ℹ", color: "#a5b4fc" },
};

export function Toast({ message, type = "info", duration = 3000, onClose }: ToastProps) {
  const [visible, setVisible] = useState(true);
  const s = STYLES[type];

  useEffect(() => {
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, duration);
    return () => clearTimeout(t);
  }, [duration, onClose]);

  return (
    <div
      className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium backdrop-blur-md"
      style={{
        background: s.bg,
        border: `1px solid ${s.border}`,
        color: s.color,
        boxShadow: `0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px ${s.border}`,
        transition: "all 0.3s ease",
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(8px)",
      }}
    >
      <span style={{ fontSize: "1rem" }}>{s.icon}</span>
      <span style={{ color: "var(--text-primary)" }}>{message}</span>
      <button
        onClick={() => { setVisible(false); setTimeout(onClose, 300); }}
        className="ml-1 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--text-secondary)" }}
      >
        ✕
      </button>
    </div>
  );
}

export function useToast() {
  const [toasts, setToasts] = useState<{ id: number; message: string; type: ToastType }[]>([]);
  let counter = 0;

  const show = (message: string, type: ToastType = "info") => {
    const id = ++counter;
    setToasts((prev) => [...prev, { id, message, type }]);
  };

  const remove = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const ToastContainer = () => (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 no-print">
      {toasts.map((t) => (
        <Toast key={t.id} message={t.message} type={t.type} onClose={() => remove(t.id)} />
      ))}
    </div>
  );

  return { show, ToastContainer };
}
