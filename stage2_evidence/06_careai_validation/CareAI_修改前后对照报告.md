# VentureAI × CareAI 修改前后对照

测试日期：2026-09-14。基线代码为 `d3c6e03`，修改后为当前工作区代码。两轮使用同一份 [`CareAI项目书.md`](../../CareAI项目书.md)、同一组核心提问和本机 VentureAI 页面。模型调用是真实请求，不是模拟用户研究；课堂情境与产品偏好仍属待验证假设。

## 可直接查看的截图

| 场景 | 修改前 | 修改后 |
| --- | --- | --- |
| 教练首轮：复述项目事实 | [错误地写成心理健康筛查/NLP 训练/已访谈](before-careai-coach.png) | [正确描述非诊断性健康教育与 MVP](after-careai-coach.png)；[只保留一个下一步问题](after-careai-one-question.png) |
| 上传项目书评分 | [虚构“合作医院分成”与团队背景](before-careai-grader.png) | [按 R1–R11 显示依据与建议](after-careai-grader.png) |
| 与阿福的差异化测试 | [错用心理筛查任务并自行规定招募 30 人](before-careai-competitor.png) | [同一虚构资料、同一任务和指标的对照方案](after-careai-competitor.png) |

截图由 Playwright 打开 VentureAI 的真实学生聊天页面、登录隔离测试账号并加载对应会话后截取。截图显示的是服务器保存的原始会话内容；没有手工修改页面文字。

## 对照结果

| 检查项 | 修改前 | 修改后 |
| --- | --- | --- |
| 上传文件进入模型 | 文件只截取前 2,000 字放在图状态中，教练和评分节点实际读取的消息未包含文件正文 | 最新上传文件正文及关键证据索引进入模型消息；历史 AI 回复不再作为项目事实来源 |
| 项目定位与证据边界 | 把 CareAI 错说为心理健康筛查平台，虚构 NLP 训练和用户访谈 | 正确说出成年人的非诊断性健康教育、规则与 AI 分层、7 天计划；明确真实用户、临床和付费证据缺失 |
| “只问一个问题” | 继续生成访谈清单和多个任务 | 首轮仅保留一个下一步问题 |
| 竞品测试 | 把两款产品都当作心理筛查工具，自行规定招募 30 人，并用不存在的情绪分析准确性作指标 | 给出两边使用同一虚构样本、同一任务、同一观察指标的方案；不声称 CareAI 已获用户偏好 |
| 医疗能力证据边界 | 可能把“提前发现慢性病”当成普通待验证假设，缺少产品主张限制 | 在流式 F/I/H/S 审阅中明确写出临床与合规依据不足，当前不应作为产品主张 |
| R1–R11 评分 | 正文信息与结构化评分脱节，并出现虚构的收入/团队主张 | 显示 R1–R11 逐项依据、缺失与建议，同时返回 `rubric_full` 供前端使用 |
| 匿名读取 | 项目列表、项目详情、会话历史均为 HTTP 200 | 同样三个匿名请求均为 HTTP 401；项目/会话另有所属者检查 |
| 未评分界面 | 空评分对象显示成五维 0 分 | 未得到完整评分时不展示数值，避免把“未评分”当成“能力为零” |

## 原始记录

- 修改前六题原始请求与回复：[careai-live-20260914-135948.json](careai-live-20260914-135948.json)。关键错误在 `coach_initial` 与 `grader_uploaded_only`。
- 修改后三道同题请求与原始状态：[careai-completed-20260914-222527.json](careai-completed-20260914-222527.json)。教练首轮、竞品追问返回 HTTP 200；评分请求在客户端等待 180 秒后超时，但服务端随后完成并保存了结果。经已授权历史接口取回的评分原文与 11 项结构化评分见 [careai-completed-grader-recovered.json](careai-completed-grader-recovered.json)，取回接口返回 HTTP 200。
- 竞品对照复测：[careai-competitor-final-20260914-223241.json](careai-competitor-final-20260914-223241.json) 记录了模型曾作出未经核验的阿福功能断言；[careai-competitor-corrected.json](careai-competitor-corrected.json) 记录了中间版本重复给出测试任务的问题。修复后的同一句追问原始 API 回复见 [careai-competitor-verified.json](careai-competitor-verified.json)，HTTP 200、`run_id=run_07a98721bfe5`，对应修改后竞品截图。
- 匿名访问原始状态：[修改前](unauthenticated_access.json)、[修改后](unauthenticated_access_after.json)。
- 流式接口检查：[careai-stream-smoke.json](careai-stream-smoke.json)。该用例走 F/I/H/S 短路回复，验证 SSE 事件、会话、鉴权及医疗主张边界，未作为真实模型流式生成质量证据。
- 自动化回归：`backend/.venv/bin/python -m unittest discover -s tests -q`（11 项通过）；前端 `npx tsc --noEmit` 与 `git diff --check` 通过。单文件 ESLint 仍报 18 个既有 `no-explicit-any` 错误和 6 个警告，本次未清理全文件历史类型问题。

## 仍需谨慎的地方

这轮测试证明 VentureAI 的回复更贴近材料，并不证明 CareAI 已获用户偏好、健康效果或法律合规。评分仍由模型给出，个别关于团队能力、隐私合规或验证阶段的措辞可能过度推断，应让教师或项目负责人核对。一次评分调用超过了测试客户端的 180 秒等待时间，虽然服务端随后保存了结果，实际交互仍有延迟风险。超图风险提示仍可能偏宽，不能当作已查明违规。安全检查覆盖本次涉及的项目和聊天入口，并非全站权限审计。
