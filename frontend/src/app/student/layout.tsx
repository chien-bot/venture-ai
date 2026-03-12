"use client";
import { useEffect } from "react";
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
      <Sidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
