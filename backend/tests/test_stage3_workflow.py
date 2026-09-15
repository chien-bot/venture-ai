"""Acceptance tests derived from the third-stage final report gates."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from starlette.requests import Request


def request(token: str | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return Request({"type": "http", "headers": headers})


class StageThreeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="ventureai-stage3-")
        os.environ["VENTUREAI_DB_PATH"] = str(Path(cls.temp.name) / "stage3.db")
        import services.database as database
        cls.old_db_path = database.DB_PATH
        database.DB_PATH = Path(cls.temp.name) / "stage3.db"
        database.init_db()
        cls.db = database
        cls.student_id = f"student-{uuid4().hex[:8]}"
        cls.teacher_id = f"teacher-{uuid4().hex[:8]}"
        database.save_user(cls.student_id, f"student_{uuid4().hex[:8]}", "hash", "student", "Student", "class-a")
        database.save_user(cls.teacher_id, f"teacher_{uuid4().hex[:8]}", "hash", "teacher", "Teacher", "class-a")
        cls.student_token, cls.teacher_token = uuid4().hex, uuid4().hex
        database.save_token(cls.student_token, cls.student_id)
        database.save_token(cls.teacher_token, cls.teacher_id)
        database.set_teacher_class_ids(cls.teacher_id, ["class-a"])

    @classmethod
    def tearDownClass(cls):
        import services.database as database
        database.DB_PATH = cls.old_db_path
        cls.temp.cleanup()

    def setUp(self):
        self.project_id = f"proj_{uuid4().hex[:8]}"
        self.db.save_project({
            "project_id": self.project_id, "owner_id": self.student_id,
            "name": "CareAI", "industry": "健康教育", "description": "非诊断健康教育",
            "stage": "discovery", "scores": {}, "diagnosis": [], "created_at": "2026-09-15",
        })

    def _run(self, flow: str) -> str:
        run_id = f"run_{uuid4().hex[:12]}"
        with self.db.get_conn() as conn:
            conn.execute(
                """INSERT INTO agent_runs
                   (run_id,session_id,project_id,flow,agent_version,git_commit,model,source_hash,prompt_hash,status,finished_at)
                   VALUES (?,?,?,?,?,?,?,?,?,'completed',datetime('now'))""",
                (run_id, f"session-{run_id}", self.project_id, flow, "v2-test", "commit", "mock", "source", "prompt"),
            )
        return run_id

    def _doc(self, kind: str, content: str, **extra):
        from routers.stage3 import DocumentInput, save_document
        return save_document(self.project_id, DocumentInput(kind=kind, content=content, source="student", **extra), request(self.student_token))

    def _approve(self):
        from routers.stage3 import GateReviewInput, gate_review
        return gate_review(self.project_id, GateReviewInput(
            proposal_version=1, criteria={f"G{i}": True for i in range(1, 7)},
            decision="approved", feedback="材料边界清楚，可以进入计划书阶段。",
        ), request(self.teacher_token))

    def test_public_registration_cannot_create_privileged_account(self):
        from routers.auth import RegisterRequest, register
        with self.assertRaises(HTTPException) as caught:
            register(RegisterRequest(username="fake_teacher", password="pass", role="teacher"))
        self.assertEqual(caught.exception.status_code, 403)

    def test_sensitive_route_groups_reject_anonymous_requests(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        checks = [
            ("GET", "/api/teacher/projects", None),
            ("GET", "/api/admin/users", None),
            ("GET", "/api/graph/status", None),
            ("GET", f"/api/tools/timeline/{self.project_id}", None),
            ("GET", "/api/peer-review/available", None),
            ("GET", "/api/knowledge/cards", None),
            ("GET", "/api/playbooks/", None),
            ("POST", "/api/chat/defense/start", {"project_id": self.project_id}),
        ]
        for method, path, payload in checks:
            with self.subTest(path=path):
                response = client.request(method, path, json=payload)
                self.assertEqual(response.status_code, 401)

    def test_proposal_gate_blocks_formal_material_and_incomplete_approval(self):
        from routers.stage3 import DocumentInput, GateReviewInput, gate_review, save_document
        self._doc("proposal", "CareAI 立项书：项目定位、用户、问题、方案、边界与 Agent 使用计划。")
        with self.assertRaises(HTTPException) as blocked:
            save_document(self.project_id, DocumentInput(
                kind="plan", content="尚未过闯关的计划书不能进入正式材料阶段。",
                source="student", basis_version=1,
            ), request(self.student_token))
        self.assertEqual(blocked.exception.status_code, 409)
        criteria = {f"G{i}": True for i in range(1, 7)}
        criteria["G3"] = False
        with self.assertRaises(HTTPException) as incomplete:
            gate_review(self.project_id, GateReviewInput(
                proposal_version=1, criteria=criteria, decision="approved", feedback="G3 证据边界仍需补充并重新提交。",
            ), request(self.teacher_token))
        self.assertEqual(incomplete.exception.status_code, 422)

    def test_complete_dual_gate_workflow_is_traceable(self):
        from routers.stage3 import (
            DailyProgressInput, EvidenceInput, FinalReviewInput, ScoreInput, UseRecordInput,
            add_evidence, add_score, add_use_record, final_review, save_daily_progress,
        )
        self._doc("proposal", "CareAI 学生立项书，包含具体用户场景、证据边界、解决方案和三流程使用计划。")
        self._approve()
        plan1 = self._doc("plan", "CareAI 商业计划书学生初版，所有结论均按 F/I/H/S 标记并说明缺口。", basis_version=1)
        plan2 = self._doc("plan", "CareAI 商业计划书学生修改版，已根据评审纠正证据跳跃并保留修改说明。", basis_version=1, note="根据F3评审修改")
        self._doc("slides", "CareAI 十六页路演PPT文字稿：问题、证据、方案、模式、风险和请求。", basis_version=1, plan_version=plan2["version"])
        self._doc("script", "CareAI 十分钟路演讲稿，说明问题、依据、边界、方案、实施和社会价值。", basis_version=1, plan_version=plan2["version"], timed_seconds=586)
        questions = "\n".join(f"{i}. 高风险问题{i}？结论—依据—边界—下一步验证。" for i in range(1, 11))
        self._doc("qa", questions, basis_version=1, plan_version=plan2["version"])
        self._doc("stage_summary", "第三阶段总结：项目结果、Agent贡献、人工采纳与拒绝、局限和后续计划。", basis_version=1)
        add_evidence(self.project_id, EvidenceInput(
            label="F", claim="CareAI 已实现可演示 MVP", source_ref="CareAI项目书.md 第四章及代码仓库",
        ), request(self.student_token))

        tutor, coach, grader_before, grader_after = (self._run(x) for x in ("tutor", "coach", "grader", "grader"))
        add_use_record(self.project_id, UseRecordInput(
            run_id=tutor, flow="F1", task="理解证据边界并完成概念纠错",
            material_kind="proposal", material_version=1, action="adopted",
            reason="概念解释与课程要求一致，因此在立项证据表中采用。",
            learning_check="学生将无来源的支付意愿误判为事实，复核后改为H。",
            evidence_ref="F1 对话记录 run_id 对应原始输出",
            effect_judgment="纠正了事实与假设混淆，降低证据越界风险。",
        ), request(self.student_token))
        add_use_record(self.project_id, UseRecordInput(
            run_id=coach, flow="F2", task="根据立项材料梳理计划书结构",
            material_kind="proposal", material_version=1, action="rewritten",
            reason="采用章节顺序，但人工删除未经证实的市场判断并重写。",
            result_kind="plan", result_version=plan1["version"],
            evidence_ref="F2 对话记录与计划书 v1 修改痕迹",
            effect_judgment="缩短结构整理时间，市场结论仍由学生核验。",
        ), request(self.student_token))
        add_use_record(self.project_id, UseRecordInput(
            run_id=grader_before, flow="F3", task="定位计划书中的证据跳跃并复验",
            material_kind="plan", material_version=plan1["version"], action="rewritten",
            reason="按评审意见修正用户偏好与健康效果表述，再用评分流程复验。",
            issue_location="计划书 v1 的市场与产品效果章节", verification_run_id=grader_after,
            result_kind="plan", result_version=plan2["version"],
            evidence_ref="F3 修改前后评分运行与计划书版本差异",
            effect_judgment="修正两处证据跳跃，复验结果用于确认改动。",
        ), request(self.student_token))
        for day in range(1, 10):
            save_daily_progress(self.project_id, DailyProgressInput(
                day=day, goal=f"完成 D{day} 课程任务", artifact=f"D{day} 对应材料版本",
                agent_evidence=f"D{day} run_id 或不使用说明", risk_next=f"D{day} 风险和次日行动",
            ), request(self.student_token))

        project_scores = {"social_value": 12, "evidence_process": 13, "innovation": 12, "feasibility": 15, "team_consistency": 10}
        agent_scores = {"three_flows": 13, "traceability": 14, "effectiveness": 16, "correctness": 13, "human_boundary": 10}
        self.assertTrue(add_score(self.project_id, ScoreInput(category="project", scores=project_scores, feedback="材料版本完整且证据依据可定位。"), request(self.teacher_token))["pass"])
        self.assertTrue(add_score(self.project_id, ScoreInput(category="agent", scores=agent_scores, feedback="三流程运行与人工处理均可追溯。"), request(self.teacher_token))["pass"])
        result = final_review(self.project_id, FinalReviewInput(
            decision="pass", redline=False, feedback="双门槛通过，材料完整且无红线。",
        ), request(self.teacher_token))
        self.assertTrue(result["ready_for_acceptance"])
        self.assertEqual(result["final_review"]["decision"], "pass")
        self.assertTrue(result["final_review"]["current"])
        self.assertEqual(len(result["daily_progress"]), 9)
        self.assertEqual(set(result["flow_coverage"]), {"F1", "F2", "F3"})

        self._doc(
            "plan",
            "CareAI 商业计划书学生 v3，进一步改写实施路径；正式评分和终局结论应自动失效。",
            basis_version=1,
            note="根据终局反馈更新实施路径并等待重新评分验证。",
        )
        from routers.stage3 import _overview
        refreshed = _overview(self.project_id)
        self.assertFalse(refreshed["ready_for_acceptance"])
        self.assertFalse(refreshed["final_review"]["current"])
        self.assertTrue(any("评分未绑定当前" in item for item in refreshed["missing"]))


if __name__ == "__main__":
    unittest.main()
