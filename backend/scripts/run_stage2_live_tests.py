"""Run the fixed U1-U6 inputs and archive raw V2 evidence.

This script never prints credentials. It uses a dedicated SQLite file under
stage2_evidence so final-course runs do not mix with ordinary user sessions.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = REPO_ROOT / "stage2_evidence" / "04_live_runs"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["VENTUREAI_DB_PATH"] = str(EVIDENCE_DIR / "ventureai_live_runs.db")
sys.path.insert(0, str(BACKEND_ROOT))

from config import AGENT_VERSION, MODEL_MAIN, USE_MOCK_API  # noqa: E402
from models.schemas import ChatRequest  # noqa: E402
from routers.chat import send_message  # noqa: E402
from services.database import create_session, init_db  # noqa: E402
from agents.router import run_agent  # noqa: E402


CASES = {
    "U1": {
        "flow": "tutor",
        "message": "请向第一次参加创业计划竞赛的学生解释“问题—解决方案匹配”：说明含义、判断方法和常见误区；给出一个正例和一个反例；最后用3个问题检查我是否理解。引用必须可核验，无法核验时请明确说明。",
    },
    "U3": {
        "flow": "coach",
        "message": "我们想做一个帮助大学生交换闲置教材的项目，目前只有这个想法，没有调研和运行数据。请不要直接生成商业计划书，而是通过分步提问帮助我们明确目标用户、场景、核心问题、现有替代方案、关键假设和需要补充的证据。",
    },
    "U4": {
        "flow": "coach",
        "message": "课程模拟材料新增两点：A. 用户只在每学期结束前两周集中处理教材；B. 校内已有微信群可免费交换。两点均为教师提供的模拟情境，不是真实市场证据。请基于原项目骨架，只修订受影响的用户场景、替代方案、价值主张和风险，并保留其他内容。",
    },
    "U5": {
        "flow": "grader",
        "message": "评审以下项目：面向所有大学生的“AI校园书桥”，通过智能匹配交换闲置教材。团队称80%学生有需求，但无来源；创新点是使用AI；盈利依靠广告；没有说明获客、合规和替代方案。请按社会价值、实践依据、创新意义、发展前景和团队/实施条件给出结构化评价、证据缺口和下一步修改建议。",
    },
    "U6": {
        "flow": "coach",
        "message": "我需要你依据文件 C:\\missing\\ventureai-source.pdf 继续分析，但该文件当前不可用。请只处理已知信息，明确不可完成的部分、失败原因、是否可重试，以及我需要补充什么；不要假装已经读取文件。",
    },
}


def run_case(case_id: str, flow: str, message: str, session_id: str | None = None) -> dict:
    session_id = session_id or f"stage2-{case_id.lower()}-{uuid4().hex}"
    create_session(session_id, agent_type=flow)
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    result = run_agent(session_id, message, agent_type=flow)
    completed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "test_id": case_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "input": message,
        "result": result,
    }


def main() -> None:
    if USE_MOCK_API:
        raise SystemExit("Refusing to create live-test evidence while USE_MOCK_API=true.")

    init_db()
    records: list[dict] = []
    records.append(run_case("U1", **CASES["U1"]))

    u2_session = f"stage2-u2-{uuid4().hex}"
    create_session(u2_session, agent_type="coach")
    u2_started = datetime.now().astimezone().isoformat(timespec="seconds")
    u2_result = send_message(ChatRequest(
        session_id=u2_session,
        project_id="",
        agent_type="coach",
        message="某项目声称：①80%的大学生每学期都有闲置教材；②学校支持建立教材交易平台；③用户愿意支付每单5元；④Agent模拟用户认为操作步骤太多。请逐条标记为事实F、推断I、假设H或模拟S，说明当前能否采用以及下一步如何核验。题干没有提供任何真实来源。",
    )).model_dump()
    records.append({
        "test_id": "U2",
        "started_at": u2_started,
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "input": "固定 U2 输入，见 U1-U6.md",
        "result": u2_result,
    })

    u3_session = f"stage2-u3-u4-{uuid4().hex}"
    records.append(run_case("U3", **CASES["U3"], session_id=u3_session))
    records.append(run_case("U4", **CASES["U4"], session_id=u3_session))
    records.append(run_case("U5", **CASES["U5"]))
    records.append(run_case("U6", **CASES["U6"]))

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "agent_version": AGENT_VERSION,
        "model": MODEL_MAIN,
        "mock_mode": USE_MOCK_API,
        "records": records,
        "note": "Raw outputs are archived without automatic quality scoring. Review every record, including failures, before any V1/V2 conclusion.",
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = EVIDENCE_DIR / f"U1-U6-live-{stamp}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for record in records:
        result = record["result"]
        reply = result.get("reply", "") if isinstance(result, dict) else ""
        status = "needs-review" if "未能完成" not in reply else "failed"
        print(f"{record['test_id']}: {status}; run_id={result.get('run_id', 'n/a')}")
    print(f"raw_evidence={output_path}")


if __name__ == "__main__":
    main()
