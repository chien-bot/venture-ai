# CareAI × VentureAI：第一阶段材料索引

## 两个项目的关系

- **CareAI**：本组的创新创业项目与产品原型，提供健康数据记录、非诊断性风险提示、解释性建议、7 天行动计划和历史趋势。
- **VentureAI**：上学期完成的创新创业教学智能体。本阶段先冻结为 V1，再用它指导与评审 CareAI；后续依据真实使用问题优化为 V2。

## 本目录内容

| 文件 | 用途 | 当前状态 |
| --- | --- | --- |
| `careai-project-positioning.md` | 选题矩阵、定位、边界和 MVP 功能事实 | 已完成初稿 |
| `careai-project-proposal.md` | 一页项目立项书 | 已完成初稿 |
| `evidence-assumption-ledger.md` | 公开证据、F/I/H/S 标注与后续验证计划 | 已完成初稿 |
| `ventureai-v1-test-pack.md` | 交给 VentureAI V1 的统一测试与 CareAI 专项测试 | 已完成首次运行；详见 VentureAI 原始日志索引 |
| `agent-problem-log.md` | VentureAI 真实问题案例记录模板 | 已记录 5 个真实、可复现案例；跨组测试待完成 |
| `stage1-precheck.md` | 第一阶段门槛预审与补件清单 | 已完成预审 |
| `cross-group-test.html` | 两名外部测试者使用的独立测试台 | 已就绪，待真实使用 |
| `cross-group-test-guide.md` | 跨组测试启动、分工和记录说明 | 已就绪 |
| `cross-group-results/` | 外部测试者下载的原始 JSON 结果 | 待真实使用 |

## 使用顺序

1. 以本目录中的 CareAI 立项书和证据台账作为项目材料 `v0.1`。
2. 进入 VentureAI 仓库，冻结当前版本为 `V1`；记录提交号、模型、提示词、知识库、工具和启动方式。
3. 使用 `ventureai-v1-test-pack.md` 中的测试输入运行 V1，保存第一次原始对话、日志和人工干预。
4. 仅把**真实发生且可复现**的问题填入 `agent-problem-log.md`；不得事后想象或补写问题。
5. 根据问题影响选择少量高优先级项开发 VentureAI V2；CareAI 项目材料的人工改写与 VentureAI 能力改进必须分别记录。

## 诚信与安全底线

- 当前材料没有声称已开展真实问卷、访谈、订单、合作或运营验证。
- 所有公开资料、推断、待验证假设和模拟内容，分别标记为 F、I、H、S。
- CareAI 仅面向成年人的健康教育与风险提示；不输出疾病诊断、处方或剂量建议，也不替代专业人员。
- 健康信息属于敏感个人信息。任何后续真实试用都需要先补充授权、告知、最小化采集、存储和删除机制。
