"""Exercise VentureAI's public API with the CareAI project, preserving raw replies."""

from __future__ import annotations

import json
import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
API = "http://127.0.0.1:8001"
PROJECT_BOOK = ROOT / "CareAI项目书.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="live")
    parser.add_argument("--case", action="append", choices=(
        "coach_initial", "coach_competitor_followup", "evidence_boundary",
        "tutor_psf", "grader_uploaded_only", "grader_full_document",
    ))
    args = parser.parse_args()
    if args.case and "coach_competitor_followup" in args.case and "coach_initial" not in args.case:
        args.case.insert(0, "coach_initial")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = OUTPUT_DIR / f"careai-{args.label}-{stamp}.json"
    record: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api": API,
        "input_file": str(PROJECT_BOOK.relative_to(ROOT)),
        "note": "Real-model responses; no simulated-user or market-validation evidence.",
        "setup": {},
        "cases": [],
    }

    def save() -> None:
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    def post_json(client: httpx.Client, path: str, body: dict) -> tuple[int, dict]:
        response = client.post(path, json=body)
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw_text": response.text[:2000]}
        return response.status_code, payload

    with httpx.Client(base_url=API, timeout=360.0) as client:
        health = client.get("/health")
        record["setup"]["health"] = {"status": health.status_code, "body": health.json()}

        username = f"careai_eval_{uuid4().hex[:8]}"
        status, registration = post_json(client, "/api/auth/register", {
            "username": username,
            "password": uuid4().hex,
            "role": "student",
            "display_name": "CareAI 功能测试",
        })
        if status != 200:
            raise RuntimeError(f"registration failed: {status} {registration}")
        token = registration.pop("token")
        client.headers["Authorization"] = f"Bearer {token}"
        record["setup"]["registration"] = {"status": status, "body": registration}
        save()

        status, project = post_json(client, "/api/projects/", {
            "name": "CareAI 成人健康习惯管理原型",
            "industry": "健康教育",
            "description": "面向成年人；本地规则确定关注项，AI 只解释并生成7天行动计划；已有MVP，尚无真实用户访谈、临床验证、收入或付费数据。",
            "project_type": "创新项目",
        })
        if status != 200:
            raise RuntimeError(f"project creation failed: {status} {project}")
        project_id = project["project_id"]
        record["setup"]["project"] = {"status": status, "body": project}
        save()

        with PROJECT_BOOK.open("rb") as source:
            upload = client.post(
                "/api/upload/file",
                files={"file": (PROJECT_BOOK.name, source, "text/markdown")},
                data={"project_id": project_id},
            )
        record["setup"]["upload"] = {"status": upload.status_code, "body": upload.json()}
        save()

        sessions: dict[str, str] = {}

        def run(case_id: str, flow: str, message: str, reuse: str | None = None) -> None:
            if args.case and case_id not in args.case:
                return
            if reuse:
                session_id = sessions[reuse]
            else:
                status, started = post_json(
                    client, f"/api/chat/start?agent_type={flow}&project_id={project_id}", {}
                )
                if status != 200:
                    raise RuntimeError(f"chat start failed: {status} {started}")
                session_id = started["session_id"]
                sessions[case_id] = session_id

            started_at = datetime.now(timezone.utc).isoformat()
            before = time.monotonic()
            try:
                status, payload = post_json(client, "/api/chat/message", {
                    "session_id": session_id,
                    "project_id": project_id,
                    "agent_type": flow,
                    "message": message,
                })
                result = {"status": status, "body": payload}
            except Exception as exc:
                result = {"exception": f"{type(exc).__name__}: {exc}"}
            item = {
                "case_id": case_id,
                "flow": flow,
                "session_id": session_id,
                "started_at": started_at,
                "elapsed_seconds": round(time.monotonic() - before, 2),
                "input": message,
                "result": result,
            }
            record["cases"].append(item)
            save()
            body = result.get("body") or {}
            print(f"{case_id}: HTTP {result.get('status', 'exception')}; "
                  f"intent={body.get('intent')}; run_id={body.get('run_id')}; "
                  f"reply_chars={len(body.get('reply') or '')}; {item['elapsed_seconds']}s", flush=True)

        run(
            "coach_initial",
            "coach",
            "我上传了 CareAI 项目书。请先准确复述项目定位、目前真实完成的工作和没有完成的验证；"
            "指出最重要的一个证据缺口，再只问我一个下一步问题。不要把设想当成用户反馈或临床证据。",
        )
        run(
            "coach_competitor_followup",
            "coach",
            "补充：蚂蚁阿福已经有健康档案和健康小目标，CareAI 目前没有真实用户访谈、留存或付费证据。"
            "如果我想发布 CareAI，为什么用户会选它？请根据我们刚才讨论的项目，指出尚未验证的差异化假设，"
            "设计一个不采集真实健康数据的课堂对照测试。不要说阿福没有习惯计划。",
            reuse="coach_initial",
        )
        run(
            "evidence_boundary",
            "coach",
            "请按 F/I/H/S 逐项判断以下 CareAI 说法，题干没有提供任何真实来源："
            "①八成大学生睡眠不足；②用户愿意每月付费10元；③CareAI能提前发现慢性病；"
            "④Agent模拟用户说7天计划很方便。指出哪些不能写成事实、医疗边界和下一步验证方法。",
        )
        run(
            "tutor_psf",
            "tutor",
            "请结合 CareAI 向第一次创业的学生解释‘问题—解决方案匹配’，区别已完成的功能和已验证的用户需求；"
            "给一个具体正例、一个反例，最后用两个问题检查我是否理解。",
        )
        run(
            "grader_uploaded_only",
            "grader",
            "请评审我上传的 CareAI 项目书，按 R1-R11 逐项给出依据、缺失证据和一条下一步建议。"
            "尤其核对未做真实用户测试、临床验证和医疗健康数据隐私治理；无法从文件读到的内容请明确说不知道。",
        )
        run(
            "grader_full_document",
            "grader",
            "请对以下完整 CareAI 项目书做形成性评审，按 R1-R11 逐项给出依据、缺失证据和下一步建议。"
            "严格区分功能已实现与需求已验证；不能把模拟结果当真实用户反馈；不能作诊断性产品主张。\n\n"
            + PROJECT_BOOK.read_text(encoding="utf-8"),
        )

        if "coach_initial" in sessions:
            history = client.get(f"/api/chat/history/{sessions['coach_initial']}")
            record["setup"]["coach_history"] = {"status": history.status_code, "body": history.json()}
            save()

    print(f"raw_evidence={output}", flush=True)


if __name__ == "__main__":
    main()
