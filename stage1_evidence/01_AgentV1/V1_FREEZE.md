# VentureAI V1 冻结说明（CareAI 第一阶段）

## 冻结身份

- 冻结标签：`ventureai-v1-stage1-2026-09-05`
- Git 提交：`c456aefa5d2029b39c9a772b1ebe9a3d3a5275d0`
- 分支：`main`（与 `origin/main` 同步）
- 冻结时间：2026-09-05（Asia/Kuala_Lumpur）
- 冻结目的：作为 CareAI 第一阶段的唯一 V1 基线；本阶段不得修改、替换或覆盖 V1 功能。

## 工作区边界

冻结时不存在已跟踪文件改动。工作区中已有未追踪的文档、上传目录与测试辅助文件；它们不属于此 V1 标签，且不作为本次 Agent 能力的证据。

## 模型与工具配置

- `USE_MOCK_API=False`
- API 路径：OpenRouter（已配置，优先于未配置的 Anthropic 路径）
- 主模型：`qwen/qwen-2.5-72b-instruct`
- 轻量模型：`qwen/qwen-2.5-7b-instruct`
- 后端：Python 3.10.11、FastAPI 0.115.0、Uvicorn 0.30.0
- 前端：Next.js 16.1.6、React 18.3.0
- 数据与工具：SQLite 会话/项目存储；可选 Neo4j 图谱同步；本地 TF-IDF 超图检索；上传文件解析；OpenRouter/Anthropic LLM 客户端。

## 三个基线流程与实现入口

1. 理论学习：`agent_type=tutor`，主要提示词 `backend/prompts/tutor.py`。
2. 项目指导：`agent_type=coach`，主要提示词 `backend/prompts/coach.py`。
3. 项目评审：`agent_type=grader`，主要提示词 `backend/agents/nodes/grader.py`。

统一编排入口为 `backend/agents/router.py`，HTTP 入口为 `POST /api/chat/start` 与 `POST /api/chat/message`。

## 知识与规则版本

下列 SHA-256 用于检测本阶段内是否发生 V1 变更：

| 文件 | SHA-256 |
| --- | --- |
| `backend/config.py` | `C33F04516469C8A1208581C8BFE059867D619F8F567914D25AF83A14CF4837DC` |
| `backend/main.py` | `E3570257F67A309E7E1428157CEFDFCCFDA5D8367AFE80FD1B5D09AA7F2E25E0` |
| `backend/agents/router.py` | `E91D56DB435D8C5E4609EA0CCF805CC8F0A84DD66FFFB14084F32A3E50C76409` |
| `backend/prompts/coach.py` | `3D32B5994AE0F5A279C29211BB1EE79626B87E4CEC18E3B832745015E16856DF` |
| `backend/prompts/tutor.py` | `720C3088E9FF384D10FA792148AEFFB2C97D0CC55590DD544D2C0D511B5A1CF1` |
| `backend/prompts/competition.py` | `20C1E591822861461D28402844C30241AD59FB956F442A3514204D1FE099427B` |
| `backend/agents/nodes/grader.py` | `7BF697F61B307DB9E665BCB1238F07910C6169BE736DF0E741C241F9897446AC` |
| `backend/data/hypergraph_data.json` | `875419A773AA8D40E0AD859D0F7E3A5C5BBF97CE2B781FC0B83B3030096D93BF` |
| `backend/data/knowledge_cards.json` | `BDEC099E165E4E6DACDFF720BEF6666CE9C672EBBA81DB937C1E37A03A6FE133` |
| `backend/data/playbooks.json` | `7773C3B120D3949A5288739E678668F9EB9A3C64653E16222BD574CD14F710D4` |
| `backend/data/rubric/rubric_items.json` | `4A5BDCE199CDD01B5DF29BFBB94505CA5F270ED662B5B1335D615CC610105A68` |
| `backend/data/rubric/constraint_rules.json` | `8F25A37C63950F73B8CB877EB6C9A19A34CAD46416BB97D626EF30B78822A840` |
| `backend/data/rubric/competition_templates.json` | `A4EF4E05333BCB34590E381C0A15CBAA8055DA6596F5618FF8FE01C9B4727417` |

