import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "VentureAI - 创新创业教学智能体",
  description: "基于知识图谱与超图的双创教育AI系统",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className={`${inter.className} antialiased`}>{children}</body>
    </html>
  );
}
