import { Save, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import type { UserProfile } from "../types";

type Props = {
  profile: UserProfile;
  onSave: (profile: UserProfile) => Promise<void>;
  onCreate: () => void;
  saving: boolean;
};

export function ProfilePage({ profile, onSave, onCreate, saving }: Props) {
  const [form, setForm] = useState<UserProfile>(profile);
  useEffect(() => setForm(profile), [profile]);
  const set = <K extends keyof UserProfile>(key: K, value: UserProfile[K]) => setForm((current) => ({ ...current, [key]: value }));
  return <main className="mx-auto max-w-3xl px-5 py-10"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-semibold text-teal-700">健康 Memory · 个人档案</p><h1 className="mt-2 text-3xl font-bold text-slate-950">{profile.display_name} 的健康档案</h1><p className="mt-3 text-slate-600">档案资料只用于让后续计划和健康摘要更贴近个人情况。此演示版本为本地资料隔离，不是正式医疗账号系统。</p></div><button onClick={onCreate} className="inline-flex items-center gap-2 rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-sm font-semibold text-teal-700 hover:bg-teal-50"><UserPlus size={16} />新建演示档案</button></div>
    <form onSubmit={(event) => { event.preventDefault(); void onSave(form); }} className="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><div className="grid gap-5 sm:grid-cols-2">
      <label className="text-sm font-medium text-slate-700">显示名称<input required value={form.display_name} onChange={(event) => set("display_name", event.target.value)} className={inputClass} /></label>
      <label className="text-sm font-medium text-slate-700">年龄<input type="number" min="18" max="120" value={form.age ?? ""} onChange={(event) => set("age", event.target.value ? Number(event.target.value) : null)} className={inputClass} /></label>
      <label className="text-sm font-medium text-slate-700">性别<select value={form.gender ?? ""} onChange={(event) => set("gender", (event.target.value || null) as UserProfile["gender"])} className={inputClass}><option value="">未填写</option><option value="male">男</option><option value="female">女</option><option value="other">其他</option></select></label>
      <label className="text-sm font-medium text-slate-700">主要健康目标<select value={form.health_goal ?? ""} onChange={(event) => set("health_goal", event.target.value || null)} className={inputClass}><option value="">未填写</option><option>改善睡眠</option><option>建立运动习惯</option><option>体重管理</option><option>规律记录血压</option></select></label>
    </div><div className="mt-6 grid gap-5"><label className="text-sm font-medium text-slate-700">既往健康情况（可选）<textarea value={form.medical_history ?? ""} onChange={(event) => set("medical_history", event.target.value || null)} className={inputClass} rows={3} placeholder="由用户自行填写；不作诊断" /></label><label className="text-sm font-medium text-slate-700">长期用药自述（可选）<textarea value={form.long_term_medication ?? ""} onChange={(event) => set("long_term_medication", event.target.value || null)} className={inputClass} rows={2} /></label><label className="text-sm font-medium text-slate-700">过敏信息（可选）<textarea value={form.allergies ?? ""} onChange={(event) => set("allergies", event.target.value || null)} className={inputClass} rows={2} /></label></div><div className="mt-7 flex justify-end border-t border-slate-100 pt-6"><button disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 font-semibold text-white disabled:opacity-60"><Save size={18} />{saving ? "正在保存" : "保存健康档案"}</button></div></form>
  </main>;
}

const inputClass = "mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-slate-900 outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10";
