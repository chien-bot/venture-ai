import { ArrowRight, BrainCircuit, ClipboardCheck, ShieldCheck, Sparkles } from "lucide-react";

export function HomePage({ onStart }: { onStart: () => void }) {
  return (
    <main>
      <section className="mx-auto grid max-w-6xl gap-12 px-5 pb-18 pt-16 lg:grid-cols-[1.15fr_.85fr] lg:items-center lg:pt-24">
        <div>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1.5 text-sm font-medium text-teal-700"><Sparkles size={16} />终生健康 Memory · 主动管理</div>
          <h1 className="max-w-3xl text-4xl font-bold leading-tight tracking-tight text-slate-950 sm:text-5xl">记住每一次变化，<br /><span className="text-teal-600">更早开始健康管理。</span></h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">CareAI 把每次健康记录放进个人健康 Memory，分析长期趋势、提示值得关注的变化，并追踪行动计划是否真正完成。</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button onClick={onStart} className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 font-semibold text-white shadow-lg shadow-teal-600/20 transition hover:bg-teal-700">开始健康分析 <ArrowRight size={18} /></button>
            <span className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">约 2 分钟完成</span>
          </div>
        </div>
        <div className="rounded-3xl border border-teal-100 bg-gradient-to-br from-teal-50 via-white to-sky-50 p-6 shadow-xl shadow-slate-200/50">
          <div className="rounded-2xl bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between"><div><p className="text-sm text-slate-500">健康风险概览</p><p className="mt-1 text-xl font-bold text-slate-900">从数据到行动</p></div><span className="grid size-11 place-items-center rounded-xl bg-teal-100 text-teal-700"><BrainCircuit /></span></div>
            <div className="mt-6 space-y-4">
              {["记录并进入健康时间轴", "规则分析长期变化", "执行、追踪与每周复盘"].map((item, index) => <div key={item} className="flex items-center gap-3"><span className="grid size-7 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white">{index + 1}</span><span className="font-medium text-slate-700">{item}</span></div>)}
            </div>
          </div>
        </div>
      </section>
      <section className="border-y border-slate-200 bg-white"><div className="mx-auto grid max-w-6xl gap-6 px-5 py-10 md:grid-cols-3">
        {[
          [ClipboardCheck, "健康 Memory", "将带日期的指标、报告和计划完成情况放入个人时间轴。"],
          [BrainCircuit, "主动趋势提示", "基于多次记录发现连续变化；资料不足时不会制造预警。"],
          [ShieldCheck, "非诊断定位", "不诊断疾病，不替代医生；异常情况建议线下咨询专业人员。"]
        ].map(([Icon, title, text]) => <article key={String(title)} className="rounded-2xl border border-slate-100 p-5"><span className="mb-4 grid size-10 place-items-center rounded-xl bg-teal-50 text-teal-700"><Icon size={21} /></span><h2 className="font-bold text-slate-900">{String(title)}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{String(text)}</p></article>)}
      </div></section>
    </main>
  );
}
