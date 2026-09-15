"""Regression checks for the Stage 2 V2 run-evidence contract.

These tests intentionally use an isolated SQLite file and mock mode.  They
verify application behaviour and traceability without representing mock
output as a live-model evaluation.
"""

from __future__ import annotations

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4


class V2TraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_dir = tempfile.TemporaryDirectory(prefix="ventureai-v2-tests-")
        os.environ["VENTUREAI_DB_PATH"] = str(Path(cls._temp_dir.name) / "ventureai-test.db")
        os.environ["USE_MOCK_API"] = "true"

        import services.database as database
        cls.old_db_path = database.DB_PATH
        database.DB_PATH = Path(cls._temp_dir.name) / "ventureai-test.db"
        from services.database import create_session, get_chat_history, init_db, save_token
        from agents.router import run_agent, run_agent_stream
        from models.schemas import ChatRequest
        from routers.chat import send_message

        init_db()
        cls.test_token = f"test-token-{uuid4().hex}"
        save_token(cls.test_token, "student_001")
        cls.create_session = staticmethod(create_session)
        cls.get_chat_history = staticmethod(get_chat_history)
        cls.run_agent = staticmethod(run_agent)
        cls.run_agent_stream = staticmethod(run_agent_stream)
        cls.ChatRequest = ChatRequest
        cls.send_message = staticmethod(send_message)

    @classmethod
    def tearDownClass(cls) -> None:
        import services.database as database
        database.DB_PATH = cls.old_db_path
        cls._temp_dir.cleanup()

    def _run(self, flow: str, message: str) -> tuple[str, dict]:
        session_id = f"test-{uuid4().hex}"
        self.create_session(session_id, agent_type=flow)
        return session_id, self.run_agent(session_id, message, agent_type=flow)

    def test_all_three_flows_have_a_traceable_run(self) -> None:
        cases = (
            ("tutor", "请解释 PMF 的含义，并给我一个反例。"),
            ("coach", "我只有一个帮助大学生交换闲置教材的想法，没有调研数据。"),
            ("grader", "请按 Rubric 评审这个项目：用户是大学生，尚未提供市场数据。"),
        )

        for flow, message in cases:
            with self.subTest(flow=flow):
                session_id, result = self._run(flow, message)
                self.assertTrue(result["run_id"].startswith("run_"))
                self.assertTrue(result["agent_version"])
                self.assertTrue(result["reply"].strip())
                self.assertNotIn("未能完成", result["reply"])
                if flow == "grader":
                    self.assertNotIn("至少10份真实用户访谈记录", result["reply"])

                history = self.get_chat_history(session_id)
                self.assertEqual(history[-1]["role"], "assistant")
                logs = history[-1]["debug_logs"]
                self.assertTrue(logs)
                self.assertTrue(any(entry["tag"] == "RUN_COMPLETED" for entry in logs))
                self.assertFalse(any(entry["tag"] == "RUN_FAILED" for entry in logs))
                for entry in logs:
                    self.assertEqual(entry["run_id"], result["run_id"])
                    self.assertEqual(entry["agent_version"], result["agent_version"])
                    self.assertEqual(entry["flow"], flow)

    def test_failure_is_recorded_without_losing_the_run_identity(self) -> None:
        session_id = f"test-{uuid4().hex}"
        self.create_session(session_id, agent_type="coach", owner_id="student_001")

        with patch("agents.router.get_graph", side_effect=RuntimeError("simulated unavailable service")):
            result = self.run_agent(session_id, "测试服务不可用时的降级。", agent_type="coach")

        self.assertIn("未能完成", result["reply"])
        self.assertTrue(result["run_id"].startswith("run_"))
        self.assertTrue(any(log["tag"] == "RUN_FAILED" for log in result["debug_logs"]))

    def test_streaming_flow_emits_the_same_run_identity(self) -> None:
        session_id = f"test-{uuid4().hex}"
        self.create_session(session_id, agent_type="tutor")

        events = list(self.run_agent_stream(
            session_id,
            "请解释 PMF 的含义。",
            agent_type="tutor",
        ))
        payloads = [json.loads(event.removeprefix("data: ").strip()) for event in events]
        done = next(payload for payload in payloads if payload["type"] == "done")

        self.assertTrue(done["run_id"].startswith("run_"))
        self.assertTrue(done["agent_version"])
        self.assertTrue(done["debug_logs"])
        self.assertTrue(any(log["tag"] == "RUN_COMPLETED" for log in done["debug_logs"]))

    def test_source_free_claims_are_not_presented_as_facts(self) -> None:
        session_id = f"test-{uuid4().hex}"
        self.create_session(session_id, agent_type="coach", owner_id="student_001")
        request = self.ChatRequest(
            session_id=session_id,
            project_id="",
            agent_type="coach",
            message=(
                "请按 F/I/H/S 标记：80%的大学生有闲置教材，学校支持平台，"
                "用户愿意每单支付5元，Agent模拟用户认为步骤太多。"
                "题干没有提供任何真实来源。"
            ),
        )

        from starlette.requests import Request
        http_request = Request({
            "type": "http",
            "headers": [(b"authorization", f"Bearer {self.test_token}".encode())],
        })
        result = self.send_message(request, http_request)

        self.assertEqual(result.intent, "evidence_review")
        self.assertTrue(result.run_id.startswith("run_"))
        self.assertTrue(result.agent_version)
        self.assertIn("H（假设）", result.reply)
        self.assertIn("S（模拟）", result.reply)
        self.assertIn("不能写成已证实", result.reply)


    def test_course_boundary_removes_fixed_real_research_requirements(self) -> None:
        from services.course_boundary import enforce_course_boundary

        reply = enforce_course_boundary(
            "请用具体的用户访谈或问卷数据来验证。提交至少5位目标用户的访谈记录或问卷结果。"
            "建议通过问卷调查、访谈等方式获取真实用户反馈。",
            "课程模拟材料：这些内容不是市场证据。",
        )

        self.assertNotIn("至少5位目标用户", reply)
        self.assertNotIn("具体的用户访谈或问卷数据", reply)
        self.assertNotIn("通过问卷调查、访谈等方式获取真实用户反馈", reply)
        self.assertIn("课程内证据/假设表", reply)


if __name__ == "__main__":
    unittest.main()
