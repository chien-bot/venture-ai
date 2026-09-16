# CareAI 可解释健康行动助手

CareAI 是用于创新创业课程验证的非诊断健康管理原型。它把基础健康数据转成可解释的关注项、7 天行动实验和连续复盘，同时让用户看到依据、确认自己是否理解，并控制数据是否交给 AI 或保存。

## 本轮创新功能

1. **理解确认**：报告后用 3 个问题进行 teach-back 检查，答错可重试，结果会随报告保存。
2. **单变量行动实验**：每轮只改变提醒时间、行动时长、行动频率或任务难度中的一个变量，并保留版本链。
3. **证据卡片**：显示输入字段、规则版本、AI 与规则各自负责的内容、参考来源和不确定性。
4. **隐私中心**：用户可以关闭 AI、停止保存、设置保留期限、导出或删除全部健康记录。
5. **便携摘要**：支持 JSON、打印／保存 PDF，以及带 Provenance 的 FHIR R5 结构演示文件。
6. **安全实验室**：以 12 个中英文固定用例回归检查疾病判断、处方、具体药名、剂量和服用频次等越界输出。

## 安全边界

CareAI 只提供健康教育与习惯管理建议，不诊断疾病，也不提供处方或药物剂量。风险等级由可检查的本地规则决定；受限 AI 只负责解释和行动建议。FHIR 文件用于结构验证，不是经认证的临床交换记录。

## 本地运行

后端：

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

前端（另开终端）：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。没有配置模型密钥时，可在“隐私中心”关闭 AI，完整体验本地规则模式。

## 验证

```bash
cd backend && .venv/bin/python -m pytest -q
cd ../frontend && npm run build
```

桌面与手机端的真实浏览器验证截图见 [`docs/innovation-evidence`](docs/innovation-evidence)。
