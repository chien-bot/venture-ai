"""Regression checks for project evidence and student data isolation."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from starlette.requests import Request


def request_with_token(token: str | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return Request({"type": "http", "headers": headers})


class CareAIRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="ventureai-careai-tests-")
        os.environ["VENTUREAI_DB_PATH"] = str(Path(cls.temp.name) / "test.db")
        os.environ["USE_MOCK_API"] = "true"
        import services.database as database
        cls.old_db_path = database.DB_PATH
        database.DB_PATH = Path(cls.temp.name) / "test.db"
        from services.database import init_db
        init_db()

    @classmethod
    def tearDownClass(cls):
        import services.database as database
        database.DB_PATH = cls.old_db_path
        cls.temp.cleanup()

    def test_uploaded_document_reaches_model_and_overrides_old_ai_claims(self):
        from agents.router import _grounded_messages
        from services.database import save_project, save_uploaded_file

        project_id = f"proj_{uuid4().hex[:8]}"
        save_project({
            "project_id": project_id, "owner_id": "student_001", "name": "CareAI",
            "industry": "健康教育", "description": "非诊断性健康习惯管理", "stage": "discovery",
            "scores": {}, "diagnosis": [], "created_at": "2026-09-14",
        })
        source = "CareAI 以本地规则解释 BMI，生成 7 天行动计划。尚未进行真实用户访谈。" + "项目证据末尾。" * 300
        save_uploaded_file(f"file_{uuid4().hex[:8]}", project_id, "", "CareAI项目书.md", "text", source, len(source))
        history = [
            {"role": "user", "content": "请分析 CareAI"},
            {"role": "assistant", "content": "CareAI 已训练心理疾病筛查 NLP 模型并完成访谈。"},
            {"role": "user", "content": "请复述已完成的工作"},
        ]
        messages, current = _grounded_messages(history, "请复述已完成的工作", project_id)
        self.assertIn("项目证据末尾", current)
        self.assertIn("尚未进行真实用户访谈", messages[-1]["content"])
        self.assertNotIn("心理疾病筛查", str(messages))
        self.assertEqual(messages[-1]["role"], "user")

    def test_anonymous_and_other_student_cannot_read_project_or_session(self):
        from services.access_control import require_project, require_session
        from services.database import create_session, save_project, save_token

        project_id = f"proj_{uuid4().hex[:8]}"
        session_id = f"session_{uuid4().hex[:8]}"
        save_project({
            "project_id": project_id, "owner_id": "student_001", "name": "Private CareAI",
            "industry": "健康教育", "description": "test", "stage": "discovery",
            "scores": {}, "diagnosis": [], "created_at": "2026-09-14",
        })
        create_session(session_id, project_id, "coach", "student_001")
        owner_token, outsider_token = uuid4().hex, uuid4().hex
        save_token(owner_token, "student_001")
        save_token(outsider_token, "student_002")

        self.assertEqual(require_project(request_with_token(owner_token), project_id)["owner_id"], "student_001")
        self.assertEqual(require_session(request_with_token(owner_token), session_id)["session_id"], session_id)
        for checker, identifier in ((require_project, project_id), (require_session, session_id)):
            with self.assertRaises(HTTPException) as anonymous:
                checker(request_with_token(), identifier)
            self.assertEqual(anonymous.exception.status_code, 401)
            with self.assertRaises(HTTPException) as outsider:
                checker(request_with_token(outsider_token), identifier)
            self.assertEqual(outsider.exception.status_code, 403)

    def test_single_question_request_does_not_turn_into_task_checklist(self):
        from agents.router import _focus_one_question

        raw = "### 项目定位\n非诊断性健康教育\n\n### 下一步任务\n访谈十人并提交记录。\n---\n风险清单"
        focused = _focus_one_question(raw, "请先复述，再只问我一个下一步问题")
        self.assertIn("非诊断性健康教育", focused)
        self.assertNotIn("访谈十人", focused)
        self.assertEqual(focused.count("？"), 1)

    def test_consent_and_missing_retention_are_not_ip_or_ltv_violations(self):
        from hypergraph.consistency_check import check_conversation

        message = "健康数据测试尚未进行；以后如招募参与者，先获取知情同意与授权。留存率尚无数据。"
        triggered = check_conversation(
            [{"role": "user", "content": message}], message, session_id=f"test-{uuid4().hex}"
        )
        ids = {item.rule_id for item in triggered}
        self.assertNotIn("H19", ids)
        self.assertNotIn("H17", ids)

    def test_competitor_plan_uses_both_products_and_simulated_data(self):
        from services.competitor_review import ensure_comparison_protocol

        prompt = "补充：蚂蚁阿福已经有健康档案。请设计不采集真实健康数据的课堂对照测试。"
        old = (
            "### 证据缺口\n偏好未验证。\n"
            "### 项目对比\n蚂蚁阿福没有七天计划。\n"
            "### 下一步问题\n**下一步任务：** 找十个人只测试 CareAI。"
        )
        result = ensure_comparison_protocol(old, prompt)
        self.assertIn("与蚂蚁阿福的同条件课堂对照", result)
        self.assertIn("S（模拟）", result)
        self.assertNotIn("找十个人", result)
        self.assertNotIn("蚂蚁阿福没有", result)
        self.assertIn("结果未产生前", result)
        alternate = ensure_comparison_protocol(
            "### 项目诊断\n尚未验证。\n### 设计对照测试\n提交20名用户结果。",
            prompt,
        )
        self.assertNotIn("提交20名用户", alternate)

    def test_source_free_medical_claim_keeps_non_diagnostic_boundary(self):
        from routers.chat import _generic_evidence_boundary_review

        reply = _generic_evidence_boundary_review(
            "按 F/I/H/S 判断：CareAI 能提前发现慢性病。题干没有提供任何真实来源。"
        )
        self.assertIn("当前不应作为产品主张", reply)
        self.assertIn("不能将健康教育提示写成医疗结论", reply)


if __name__ == "__main__":
    unittest.main()
