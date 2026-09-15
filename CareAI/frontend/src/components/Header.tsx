import { Activity, FileClock, Home, Stethoscope, UserRound } from "lucide-react";
import type { UserProfile } from "../types";

export type Page = "home" | "form" | "report" | "history" | "profile";

const links: { id: Page; label: string; icon: typeof Home }[] = [
  { id: "home", label: "首页", icon: Home },
  { id: "form", label: "健康分析", icon: Stethoscope },
  { id: "report", label: "我的报告", icon: Activity },
  { id: "history", label: "历史记录", icon: FileClock },
  { id: "profile", label: "健康档案", icon: UserRound },
];

export function Header({ activePage, onNavigate, profiles, activeUserId, onUserChange }: { activePage: Page; onNavigate: (page: Page) => void; profiles: UserProfile[]; activeUserId: string; onUserChange: (userId: string) => void }) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <button className="flex items-center gap-2 text-left" onClick={() => onNavigate("home")}>
          <span className="grid size-9 place-items-center rounded-xl bg-teal-600 text-white shadow-sm"><Activity size={21} /></span>
          <span><span className="block text-lg font-bold text-slate-900">CareAI</span><span className="block text-xs text-slate-500">健康风险管理助手</span></span>
        </button>
        <nav className="flex items-center gap-1" aria-label="主导航">
          {links.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => onNavigate(id)} className={`rounded-lg px-3 py-2 text-sm font-medium transition sm:px-4 ${activePage === id ? "bg-teal-50 text-teal-700" : "text-slate-600 hover:bg-slate-100"}`}>
              <Icon size={16} className="mr-1 inline sm:hidden" /><span className="hidden sm:inline">{label}</span><span className="sm:hidden">{label.slice(0, 2)}</span>
            </button>
          ))}
          <select aria-label="切换健康档案" value={activeUserId} onChange={(event) => onUserChange(event.target.value)} className="ml-1 max-w-28 rounded-lg border border-slate-200 bg-white px-2 py-2 text-xs text-slate-600 outline-none focus:border-teal-500 sm:max-w-36">
            {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.display_name}</option>)}
          </select>
        </nav>
      </div>
    </header>
  );
}
