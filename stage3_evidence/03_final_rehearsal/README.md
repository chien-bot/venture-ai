# VentureAI 最终现场彩排记录

日期：2026-09-16（Asia/Shanghai）

目的：验证最终生产构建、测试账号入口和助教2可能随机抽取的 F1／F2／F3 流程。本记录是软件运行证据，不是用户研究或教师评分。

## 环境

- 前端：当前 `frontend` 生产构建，`next start` 本地运行。
- 后端：当前 `backend`，真实模型配置为 OpenRouter `qwen/qwen-2.5-72b-instruct`。
- 测试账号：页面公开的 `student01` 测试账号。
- 项目：示例项目“二手课本交易平台”；不将其输出作为 CareAI 项目事实。

## 结果

| 检查 | 结果 | 证据与边界 |
|---|---|---|
| 登录与学生工作台 | 通过 | [`01-login.png`](01-login.png)、[`02-student-workbench.png`](02-student-workbench.png) |
| F1 概念辅导 | 首轮发现问题，修复后真实模型复测通过 | 首轮把示例中的 AI、留存和反馈写得像项目事实；现已在输出前统一标为 H/S，并补充适用边界，移除固定“至少10名用户”要求。复测 run `run_0f2bf35c9ed0`；[`03-f1-live-retest.png`](03-f1-live-retest.png) |
| F2 项目指导 | 通过 | 在“没有访谈和市场数据”的前提下没有把缺失信息写成事实，并聚焦一个下一步问题。run `run_da943ff15ee2`；[`04-f2-live-run.png`](04-f2-live-run.png) |
| F3 评审反馈 | 本次现场探针未完成 | grader 请求在浏览器探针结束前未返回正文；原 run `run_a34f6a2afb00` 已如实关闭为 `failed / ClientDisconnectedBeforeFix`，未伪装成功。截图：[`05-f3-interrupted-run.png`](05-f3-interrupted-run.png)。同版本已完成的历史 grader 结果仍可在 `stage2_evidence/06_careai_validation/careai-completed-grader-recovered.json` 核验。 |

## 本次修复

1. Tutor 项目示例中的未证实技术、用户反馈、运营结果和数字，在显示前统一标为 H（假设）／S（模拟）。
2. 用户要求“适用边界”时确保输出该部分；要求一个理解问题时只保留一个。
3. 课程内任务不再固定要求收集至少若干名真实用户反馈。
4. 客户端在流式任务完成前断开时，运行记录由 `running` 收口为 `failed / ClientDisconnected`，不留下假成功或永久运行状态。
5. 后端回归测试从 15 项增加到 18 项，覆盖上述问题。

## 现场策略

- F1、F2 可优先进行真实模型随机抽测。
- F3 预留较长等待时间；如果网络或模型调用没有完成，展示明确失败状态、run_id 和同版本历史完成记录。
- Mock 模式只用于断网时验证入口、权限与流程。Mock 的 F1/F3 没有完整流式正文，不能用来声称真实模型质量通过。
