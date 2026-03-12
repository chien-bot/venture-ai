"use client";
import { Suspense } from "react";
import StudentChatPageContent from "./content";

export default function StudentChatPage() {
  return (
    <Suspense fallback={<div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>加载中...</div>}>
      <StudentChatPageContent />
    </Suspense>
  );
}
