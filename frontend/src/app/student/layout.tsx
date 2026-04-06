"use client";
import { useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    const stored = sessionStorage.getItem("user");
    if (!stored) { router.replace("/"); return; }
    const user = JSON.parse(stored);
    if (user.role !== "student") router.replace("/teacher/dashboard");
  }, [router]);

  return (
    <div className="flex h-screen">
      <Suspense fallback={<div className="w-60 h-screen" style={{ background: "rgba(8,13,26,0.95)" }} />}>
        <Sidebar />
      </Suspense>
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
