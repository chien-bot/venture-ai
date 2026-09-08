# VentureAI V1 运行说明

## 启动

在仓库根目录执行：

```powershell
Set-Location backend
.\.venv-stage1-system\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/health`。

> 这是用于复现 V1 首次基线的隔离环境。直接使用全局 `python` 的启动方式会触发已记录的 FastAPI/Starlette 与 LangChain 依赖冲突（见 `../02_基线测试/FIRST_RUNS.md`），不得把该失败记录删除或改写为成功。

前端（可选）：

```powershell
Set-Location frontend
npm run dev
```

## 基线测试调用

1. `POST /api/chat/start?agent_type=tutor` 后调用 `POST /api/chat/message`：T1。
2. `POST /api/chat/start?agent_type=coach` 后调用 `POST /api/chat/message`：T2、C1、C3。
3. `POST /api/chat/start?agent_type=grader` 后调用 `POST /api/chat/message`：T3、C2。

输入、输出、时间、会话 ID、模型、人工干预及可复现状态全部保存到 `../02_基线测试/`。CareAI 材料版本是 `C:\Users\User\CareAI` 的提交 `3a144465a8a5d5c9ed76ee43a3a0faa72e4e64e6`。
