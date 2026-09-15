# 两名外部测试者使用指南

## 组织者准备（不计入测试者表现）

1. 在 VentureAI 仓库的 `backend` 目录启动已冻结 V1：

   ```powershell
   .\.venv-stage1-system\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```

2. 确认浏览器能访问 `http://127.0.0.1:8000/health`。
3. 让测试者在浏览器打开本目录的 `cross-group-test.html`。页面不会修改 VentureAI，也不会替测试者作答。

## 分工与顺序

| 测试者 | 固定任务 | 需要选择的材料 | 观察重点 |
| --- | --- | --- | --- |
| A（未参与开发） | T1、C1 | C1 选择 `careai-project-proposal.md` 和 `evidence-assumption-ledger.md` | 是否进入 tutor；是否单步指导；是否保持 F/I/H/S 与健康边界 |
| B（未参与开发） | T3、C3 | 无 | 是否进入 grader；五维评审是否完整；证据分类是否被误拦截 |

每位测试者至少运行一项；建议按表完成两项，以增加覆盖面。每项仅点击一次“开始首次运行并保存记录”。

## 测试纪律

- 测试者不得修改只读测试输入，不得让开发者解释、代答或调参。
- 如服务报错、路由错误、被拦截或输出不完整，照实下载并保留该结果；不要用重试覆盖。
- 每项完成后填写“开发组提供的帮助”和实际观察，再下载 JSON。
- 将下载的 JSON 放入 `docs/stage1/cross-group-results/`，文件名保持页面自动生成的名称。

## 完成条件

每份 JSON 都含测试者、开始时间、V1 标签、请求流程、会话 ID、完整输入、完整输出/错误、人工帮助与观察。组织者随后将其中真实发现补入 `agent-problem-log.md`；没有发现问题也应保留 JSON，不得为凑数量编造问题。
