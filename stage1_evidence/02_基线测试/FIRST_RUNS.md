# VentureAI V1 首次基线运行记录

## 运行环境

- V1 标签/提交：`ventureai-v1-stage1-2026-09-05` / `c456aefa5d2029b39c9a772b1ebe9a3d3a5275d0`
- 模型：OpenRouter `qwen/qwen-2.5-72b-instruct`；轻量模型 `qwen/qwen-2.5-7b-instruct`
- CareAI 材料：`C:\Users\User\CareAI` 提交 `3a144465a8a5d5c9ed76ee43a3a0faa72e4e64e6`
- 服务入口：`POST /api/chat/start`、`POST /api/chat/message`
- 完整原始问答日志：`C:\Users\User\venture-ai\backend\venture_ai.db`，表 `chat_messages`，以会话 ID 检索。
- 有效运行环境：`backend/.venv-stage1-system`。该环境仅为复现 V1 建立，未修改 V1 源码、提示词、模型或知识库。

## 首次运行索引

| 测试 | 时间（+08:00） | 会话 ID | 流程请求 | 结果 | 人工干预 | 完整输入/输出位置 |
| --- | --- | --- | --- | --- | --- | --- |
| T1-002 | 2026-09-05T15:55:26 | `5fcdb523-7388-4959-871c-c8548a3496da` | `tutor` | 未通过：返回 `coach` 诊断；未解释概念、未给正反例或理解检查 | 无；未重试 | SQLite `chat_messages`，用户输入 77 字、Agent 输出 452 字 |
| T2-001 | 2026-09-05T15:56:14 | `2c93981e-480c-4be4-a411-2cf5e20a3057` | `coach` | 部分完成：未代写，但未单步推进；一次输出多项诊断与多个问题 | 无 | SQLite `chat_messages`，用户输入 91 字、Agent 输出 838 字 |
| T3-001 | 2026-09-05T15:57:12 | `c523b8fc-b635-451a-81dd-6849eb7fc0f0` | `grader` | 未通过：返回 `coach` 诊断，未按五维分项评审 | 无 | SQLite `chat_messages`，用户输入 122 字、Agent 输出 1148 字 |
| C1-001 | 2026-09-05T16:03:23 | `937b0b5c-7d90-4a50-a2c2-26fc998b8e29` | `coach` | 未通过：没有单步任务/验收；未保持 F/I/H/S 边界，产生无材料依据的风险判断 | 无；完整立项书与台账原样作为上下文 | SQLite `chat_messages`，用户输入 4082 字、Agent 输出 936 字 |
| C2-001 | 2026-09-05T16:05:53 | `535cf589-c574-4e1c-a2de-8f39d5c2fa10` | `grader` | 未通过：返回 `coach` 诊断，未区分项目问题/待核验内容，未给五维评价或带验收条件的三项建议 | 无；完整立项书原样作为上下文 | SQLite `chat_messages`，用户输入 2213 字、Agent 输出 666 字 |
| C3-001 | 2026-09-05T16:06:39 | `83618b05-396b-42cc-9985-34ec142752a4` | `coach` | 未通过：被 `guardrail_ghostwrite` 拦截，未执行 F/I/H/S、医疗或隐私边界检查 | 无 | SQLite `chat_messages`，用户输入 145 字、Agent 输出 249 字 |

## 首次运行前置异常（不冒充 Agent 测试结果）

1. 默认全局环境执行 `python -m uvicorn main:app --host 127.0.0.1 --port 8000` 失败：FastAPI 0.115.0 与已安装 Starlette 1.0.0 不兼容，错误为 `Router.__init__() got an unexpected keyword argument 'on_startup'`。
2. 默认全局环境直接编排失败：全局 `langchain` 1.x 与仓库的 `langchain-core` 0.3.28/`langgraph` 0.2.60 不兼容，错误为 `module 'langchain' has no attribute 'debug'`。
3. 首次 HTTP 测试调用遗漏必填 `project_id`，返回 HTTP 422，未进入 Agent；随后按公开 API 模型补齐空字符串。该工具调用错误不计为 Agent 问题。

以上异常均保留原始终端记录；有效测试结果没有被成功重试覆盖。
