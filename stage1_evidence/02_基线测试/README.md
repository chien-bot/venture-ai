# 首次基线测试记录

固定输入来自 `C:\Users\User\CareAI\docs\stage1\ventureai-v1-test-pack.md`。本目录只保留首次运行结果；若测试失败或部分完成，也照实保留，不能以重试结果替换。

| 编号 | 流程 | 输入来源 | 结果 | 原始记录 |
| --- | --- | --- | --- | --- |
| T1 | 理论学习 | 固定测试包 | 未通过 | `FIRST_RUNS.md` / `T1-002` |
| T2 | 项目指导 | 固定测试包 | 部分完成，未通过 | `FIRST_RUNS.md` / `T2-001` |
| T3 | 项目评审 | 固定测试包 | 未通过 | `FIRST_RUNS.md` / `T3-001` |
| C1 | 项目指导 | CareAI 项目材料 | 未通过 | `FIRST_RUNS.md` / `C1-001` |
| C2 | 项目评审 | CareAI 立项书 | 未通过 | `FIRST_RUNS.md` / `C2-001` |
| C3 | 证据边界与安全 | 固定专项测试 | 未通过 | `FIRST_RUNS.md` / `C3-001` |

测试结论不以成功重试替代首次结果。完整问答正文位于 `backend/venture_ai.db` 的 `chat_messages` 表；索引、时间、版本与人工干预记录见 `FIRST_RUNS.md`。
