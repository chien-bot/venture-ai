"""Run the report's complete gate workflow as an explicitly simulated CareAI case."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8002")
    parser.add_argument("--db", type=Path, required=True,
                        help="Database used by the local API; needed to provision the simulated teacher safely.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import services.database as database
    database.DB_PATH = args.db.resolve()
    database.init_db()
    from services.database import save_token, save_user, set_teacher_class_ids

    suffix = uuid4().hex[:8]
    with httpx.Client(base_url=args.api, timeout=120) as client:
        student = client.post("/api/auth/register", json={
            "username": f"stage3_student_{suffix}", "password": uuid4().hex,
            "display_name": "CareAI 第三阶段学生测试", "class_id": "stage3-simulated",
            "role": "student",
        })
        student.raise_for_status()
        student_body = student.json()
        student_headers = {"Authorization": f"Bearer {student_body['token']}"}

        teacher_id = f"stage3-teacher-{suffix}"
        teacher_token = str(uuid4())
        save_user(teacher_id, f"stage3_teacher_{suffix}", "disabled-login", "teacher", "第三阶段模拟教师", "")
        save_token(teacher_token, teacher_id)
        set_teacher_class_ids(teacher_id, ["stage3-simulated"])
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

        project_response = client.post("/api/projects/", headers=student_headers, json={
            "name": "CareAI 第三阶段流程测试（S 模拟）", "industry": "健康教育",
            "description": "仅用于验证 VentureAI 第三阶段工作流；所有评分和教师结论均为 S（模拟），不是项目真实获奖或用户证据。",
            "project_type": "创新项目",
        })
        project_response.raise_for_status()
        project = project_response.json()
        project_id = project["project_id"]

        def post(path: str, headers: dict, payload: dict) -> dict:
            response = client.post(path, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

        proposal = post(f"/api/stage3/{project_id}/documents", student_headers, {
            "kind": "proposal", "source": "student",
            "content": "CareAI 学生核验立项书（S 流程测试）：面向成年人提供非诊断性健康教育和习惯管理；已有可演示 MVP，但无真实用户、留存、付费和临床证据。项目边界、替代方案、关键假设及 F1/F2/F3 使用计划均已列明。",
            "note": "v1：根据 CareAI 项目书整理，所有未验证主张标 H。",
        })
        gate = post(f"/api/stage3/{project_id}/gate-review", teacher_headers, {
            "proposal_version": proposal["version"],
            "criteria": {f"G{i}": True for i in range(1, 7)},
            "decision": "approved",
            "feedback": "S（模拟教师判断）：仅证明 G1–G6 接口和门槛可运行，不代表真实课程教师通过。",
        })

        def agent_run(flow: str, message: str) -> dict:
            started = client.post(
                f"/api/chat/start?agent_type={flow}&project_id={project_id}",
                headers=student_headers, json={},
            )
            started.raise_for_status()
            sent = client.post("/api/chat/message", headers=student_headers, json={
                "session_id": started.json()["session_id"], "project_id": project_id,
                "agent_type": flow, "message": message,
            })
            sent.raise_for_status()
            body = sent.json()
            return {"flow": flow, "session_id": body["session_id"], "run_id": body["run_id"],
                    "agent_version": body["agent_version"], "http_status": sent.status_code}

        tutor = agent_run("tutor", "请解释事实、推断、假设和模拟材料的区别，并用 CareAI 的支付意愿主张做一次理解检查。")
        coach = agent_run("coach", "请基于学生核验的 CareAI 立项书指出计划书结构缺口，只给建议，不把假设写成事实。")
        plan1 = post(f"/api/stage3/{project_id}/documents", student_headers, {
            "kind": "plan", "source": "student", "basis_version": proposal["version"],
            "content": "CareAI 商业计划书学生 v1（S 流程测试）。包括社会价值、用户场景、方案、替代方案、运营机制、实施路线、三情景公式、风险合规、团队和验证计划。无来源市场结论均标 H。",
            "note": "根据 F2 建议由学生整理的初版。",
        })
        grader_before = agent_run("grader", "请评审 CareAI 商业计划书 v1，定位证据跳跃和缺失项。")
        plan2 = post(f"/api/stage3/{project_id}/documents", student_headers, {
            "kind": "plan", "source": "student", "basis_version": proposal["version"],
            "content": "CareAI 商业计划书学生 v2（S 流程测试）。已删除用户偏好和健康效果的无证据断言；明确非诊断边界，补充来源占位、三情景计算式、负面影响、人工责任及未来真实验证路径。",
            "note": "根据 F3 评审定位人工改写，等待复验。",
        })
        grader_after = agent_run("grader", "请复验 CareAI 商业计划书 v2，确认无证据偏好和医疗效果主张是否已移除。")

        common = {"source": "student", "basis_version": proposal["version"], "plan_version": plan2["version"]}
        slides = post(f"/api/stage3/{project_id}/documents", student_headers, {
            **common, "kind": "slides", "content": "CareAI 路演 PPT 学生稿（S 流程测试）：16页，依次呈现问题、证据、方案、演示、替代方案、运营、实施、财务假设、风险、社会价值、团队与请求。",
            "note": "与计划书 v2 使用同一证据口径。",
        })
        script = post(f"/api/stage3/{project_id}/documents", student_headers, {
            **common, "kind": "script", "timed_seconds": 588,
            "content": "CareAI 十分钟讲稿学生稿（S 流程测试）：结论—依据—边界—下一步验证。讲稿覆盖问题、证据、方案、模式、实施、社会价值、团队和请求。",
            "note": "S 模拟计时 588 秒，仅验证计时门槛。",
        })
        qa_text = "\n".join(
            f"{i}. 高风险问题{i}？回答采用结论—依据—边界—下一步验证；该内容为 S 流程测试。"
            for i in range(1, 11)
        )
        qa = post(f"/api/stage3/{project_id}/documents", student_headers, {
            **common, "kind": "qa", "content": qa_text,
            "note": "10个 S 模拟高风险问题，待团队换成真实准备内容。",
        })
        summary = post(f"/api/stage3/{project_id}/documents", student_headers, {
            "kind": "stage_summary", "source": "student", "basis_version": proposal["version"],
            "content": "CareAI 第三阶段总结（S 流程测试）：记录项目结果、Agent 建议、学生采纳／拒绝、人工责任、系统局限和后续真实验证计划。",
            "note": "仅验证阶段总结版本和完整性门槛。",
        })
        evidence = post(f"/api/stage3/{project_id}/evidence", student_headers, {
            "label": "S", "claim": "本次双门槛评分与教师结论用于系统流程测试",
            "source_ref": "S（模拟）：run_stage3_acceptance.py 自动构造，不是现实教师评价",
            "formula": "无",
        })
        post(f"/api/stage3/{project_id}/evidence", student_headers, {
            "label": "F", "claim": "VentureAI 已保存 CareAI 项目材料版本哈希",
            "source_ref": "stage3 evidence-export 的 document_history.content_hash 字段",
            "formula": "SHA-256(content)",
        })

        use_records = [
            post(f"/api/stage3/{project_id}/use-records", student_headers, {
                "run_id": tutor["run_id"], "flow": "F1", "task": "理解 F/I/H/S 并纠正无来源主张",
                "material_kind": "proposal", "material_version": proposal["version"], "action": "adopted",
                "reason": "采用证据分类方法；学生仍负责核查每项来源。",
                "learning_check": "无来源的付费意愿最初不能标 F，理解检查后改为 H。",
                "evidence_ref": f"chat session {tutor['session_id']}",
                "effect_judgment": "纠正证据类型误判，并保留学生核查来源的责任边界。",
            }),
            post(f"/api/stage3/{project_id}/use-records", student_headers, {
                "run_id": coach["run_id"], "flow": "F2", "task": "从立项书推进计划书结构",
                "material_kind": "proposal", "material_version": proposal["version"], "action": "rewritten",
                "reason": "采用章节建议，人工删除自动生成的未经核验内容。",
                "result_kind": "plan", "result_version": plan1["version"],
                "evidence_ref": f"chat session {coach['session_id']}",
                "effect_judgment": "缩短结构整理时间，未经核验的内容由学生删除。",
            }),
            post(f"/api/stage3/{project_id}/use-records", student_headers, {
                "run_id": grader_before["run_id"], "flow": "F3", "task": "评审计划书并完成修改复验",
                "material_kind": "plan", "material_version": plan1["version"], "action": "rewritten",
                "reason": "根据评审移除无证据的用户偏好与健康效果主张。",
                "issue_location": "计划书 v1 的市场判断与健康效果表述",
                "verification_run_id": grader_after["run_id"], "result_kind": "plan", "result_version": plan2["version"],
                "evidence_ref": f"before={grader_before['session_id']}; after={grader_after['session_id']}",
                "effect_judgment": "修正两类证据跳跃，并用独立复验运行确认修改。",
            }),
        ]
        for day in range(1, 10):
            response = client.put(f"/api/stage3/{project_id}/daily-progress", headers=student_headers, json={
                "day": day, "goal": f"D{day} 系统流程测试目标（S）",
                "artifact": f"D{day} S 模拟产物，关联已保存材料版本",
                "agent_evidence": f"S 模拟记录；关键 run_id 见 evidence-export，D{day}",
                "risk_next": f"不把 D{day} 自动数据作为真实课程完成证明；下一步由师生填写",
            })
            response.raise_for_status()

        project_score = post(f"/api/stage3/{project_id}/scores", teacher_headers, {
            "category": "project", "scores": {"social_value": 14, "evidence_process": 14, "innovation": 13, "feasibility": 16, "team_consistency": 11},
            "feedback": "S（模拟评分）：仅验证项目成果100分表和独立60分门槛。",
        })
        agent_score = post(f"/api/stage3/{project_id}/scores", teacher_headers, {
            "category": "agent", "scores": {"three_flows": 14, "traceability": 15, "effectiveness": 17, "correctness": 14, "human_boundary": 11},
            "feedback": "S（模拟评分）：仅验证Agent效果100分表和独立60分门槛。",
        })
        final_review = post(f"/api/stage3/{project_id}/final-review", teacher_headers, {
            "decision": "pass", "redline": False,
            "feedback": "S（模拟终局结论）：系统门槛测试通过；真实课程必须由教师重新评分与签字。",
        })

        outsider = client.post("/api/auth/register", json={
            "username": f"stage3_outsider_{suffix}", "password": uuid4().hex,
            "display_name": "外班测试学生", "class_id": "other-class", "role": "student",
        })
        outsider.raise_for_status()
        outsider_headers = {"Authorization": f"Bearer {outsider.json()['token']}"}
        security = {
            "anonymous_stage3": client.get(f"/api/stage3/{project_id}/overview").status_code,
            "outsider_stage3": client.get(f"/api/stage3/{project_id}/overview", headers=outsider_headers).status_code,
            "student_teacher_page_api": client.get("/api/teacher/projects", headers=student_headers).status_code,
            "public_teacher_registration": client.post("/api/auth/register", json={
                "username": f"fake_teacher_{suffix}", "password": uuid4().hex, "role": "teacher",
            }).status_code,
            "anonymous_graph": client.get("/api/graph/status").status_code,
        }

        export = client.get(f"/api/stage3/{project_id}/evidence-export", headers=student_headers)
        export.raise_for_status()
        result = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": "S_simulated_stage3_workflow_functional_test",
            "warning": "All teacher scores, D1-D9 entries, timing and final decisions are S (simulated). They do not prove real course completion or CareAI user validation.",
            "api": args.api, "project": project,
            "gate": gate, "runs": [tutor, coach, grader_before, grader_after],
            "document_versions": [{"kind": x["kind"], "version": x["version"]} for x in (proposal, plan1, plan2, slides, script, qa, summary)],
            "evidence_id": evidence["id"], "use_record_ids": [x["id"] for x in use_records],
            "scores": {"project": project_score, "agent": agent_score},
            "final": {"ready_for_acceptance": final_review["ready_for_acceptance"], "decision": final_review["final_review"]["decision"]},
            "security": security, "export": export.json(),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({"project_id": project_id, "ready": result["final"]["ready_for_acceptance"], "security": security}, ensure_ascii=False))


if __name__ == "__main__":
    main()
