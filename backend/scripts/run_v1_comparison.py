"""Run the fixed U1-U6 inputs against the retained V1 Git worktree.

The script is deliberately outside the V1 worktree: it does not alter V1
source files.  It writes only a raw comparison artifact under stage2_evidence.
Run it from the V2 backend after creating ``.v1_compare_worktree``.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
V1_BACKEND = REPO_ROOT / ".v1_compare_worktree" / "backend"
EVIDENCE_DIR = REPO_ROOT / "stage2_evidence" / "05_v1_v2_comparison"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

CASES = {
    "U1": ("tutor", "请向第一次参加创业计划竞赛的学生解释“问题—解决方案匹配”：说明含义、判断方法和常见误区；给出一个正例和一个反例；最后用3个问题检查我是否理解。引用必须可核验，无法核验时请明确说明。"),
    "U3": ("coach", "我们想做一个帮助大学生交换闲置教材的项目，目前只有这个想法，没有调研和运行数据。请不要直接生成商业计划书，而是通过分步提问帮助我们明确目标用户、场景、核心问题、现有替代方案、关键假设和需要补充的证据。"),
    "U4": ("coach", "课程模拟材料新增两点：A. 用户只在每学期结束前两周集中处理教材；B. 校内已有微信群可免费交换。两点均为教师提供的模拟情境，不是真实市场证据。请基于原项目骨架，只修订受影响的用户场景、替代方案、价值主张和风险，并保留其他内容。"),
    "U5": ("grader", "评审以下项目：面向所有大学生的“AI校园书桥”，通过智能匹配交换闲置教材。团队称80%学生有需求，但无来源；创新点是使用AI；盈利依靠广告；没有说明获客、合规和替代方案。请按社会价值、实践依据、创新意义、发展前景和团队/实施条件给出结构化评价、证据缺口和下一步修改建议。"),
    "U6": ("coach", "我需要你依据文件 C:\\missing\\ventureai-source.pdf 继续分析，但该文件当前不可用。请只处理已知信息，明确不可完成的部分、失败原因、是否可重试，以及我需要补充什么；不要假装已经读取文件。"),
}
U2 = "某项目声称：①80%的大学生每学期都有闲置教材；②学校支持建立教材交易平台；③用户愿意支付每单5元；④Agent模拟用户认为操作步骤太多。请逐条标记为事实F、推断I、假设H或模拟S，说明当前能否采用以及下一步如何核验。题干没有提供任何真实来源。"


def main() -> None:
    if not V1_BACKEND.is_dir():
        raise SystemExit("V1 worktree not found; create .v1_compare_worktree first.")

    # V1's logger writes Chinese debug payloads.  Its original code predates
    # the V2 console safeguard, so make the comparison process UTF-8-safe
    # without changing V1 source.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

    os.chdir(V1_BACKEND)
    sys.path.insert(0, str(V1_BACKEND))

    from config import MODEL_MAIN, USE_MOCK_API  # noqa: E402
    from agents.router import run_agent  # noqa: E402
    from models.schemas import ChatRequest  # noqa: E402
    from routers.chat import send_message  # noqa: E402
    from services.database import init_db  # noqa: E402
    from services.session_store import create_session  # noqa: E402

    if USE_MOCK_API:
        raise SystemExit("V1 comparison requires USE_MOCK_API=false.")

    init_db()
    records: list[dict] = []

    def run_case(test_id: str, flow: str, message: str, session_id: str | None = None) -> str:
        sid = session_id or f"v1-{test_id.lower()}-{uuid4().hex}"
        create_session(sid, agent_type=flow)
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            result = run_agent(sid, message, agent_type=flow)
        except Exception as exc:  # V1 has no router-level failure envelope.
            result = {"reply": "", "error_type": type(exc).__name__, "error": str(exc)[:300]}
        records.append({
            "test_id": test_id,
            "started_at": started_at,
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "input": message,
            "result": result,
        })
        return sid

    run_case("U1", *CASES["U1"])
    u2_sid = f"v1-u2-{uuid4().hex}"
    create_session(u2_sid, agent_type="coach")
    u2_started = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        u2_result = send_message(ChatRequest(session_id=u2_sid, project_id="", agent_type="coach", message=U2)).model_dump()
    except Exception as exc:
        u2_result = {"reply": "", "error_type": type(exc).__name__, "error": str(exc)[:300]}
    records.append({"test_id": "U2", "started_at": u2_started, "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"), "input": U2, "result": u2_result})
    shared_session = run_case("U3", *CASES["U3"])
    run_case("U4", *CASES["U4"], session_id=shared_session)
    run_case("U5", *CASES["U5"])
    run_case("U6", *CASES["U6"])

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "baseline_tag": "ventureai-v1-stage1-2026-09-05",
        "baseline_commit": "c456aef",
        "model": MODEL_MAIN,
        "mock_mode": USE_MOCK_API,
        "environment_note": "V1 was run using V2's compatible isolated Python environment because V1 did not pin langchain; V1 source and .env were not changed.",
        "records": records,
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = EVIDENCE_DIR / f"v1-U1-U6-{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"raw_evidence={path}")
    for record in records:
        result = record["result"]
        print(f"{record['test_id']}: {'error' if result.get('error_type') else 'recorded'}")


if __name__ == "__main__":
    main()
