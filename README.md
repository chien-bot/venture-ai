# VentureAI V2

VentureAI is an entrepreneurship-teaching Agent with three independent flows:

- `tutor`: concept learning with examples and understanding checks;
- `coach`: step-by-step project guidance that keeps evidence gaps visible;
- `grader`: rubric-based formative review with actionable feedback.

The system is the final submission. CareAI may be used only as an input case for
demonstrations or tests; it is not the submitted system.

## Quick start (Windows / PowerShell)

1. Copy `.env.example` to `backend/.env`, then set `USE_MOCK_API=true` for an
   offline demo or configure one live-model API key for a real-model run.
2. Create and install the isolated backend environment:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Start the backend in one terminal:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
   ```

4. Start the frontend in another terminal:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

Open `http://localhost:3000`. The backend health check is
`http://localhost:8000/health`.

## Evidence and testing

- V1 is retained by the tags `ventureai-v1-stage1-2026-09-05` and
  `ventureai-v1.1-stage1-2026-09-06`.
- Every non-streaming V2 run now returns a `run_id` and `agent_version`.
  Its saved debug log records lifecycle state, flow, model setting and whether
  mock mode was used.
- Run the offline regression checks with:

  ```powershell
  cd backend
  .\.venv\Scripts\python.exe -m unittest discover -s tests -v
  ```

  These tests use mock mode and an isolated SQLite database. They establish
  routing, traceability and failure handling only; they do **not** prove live
  model quality.
- The fixed U1-U6 inputs and the required raw-result record are in
  `stage2_evidence/03_测试集/`. Run them with `USE_MOCK_API=false`, retain every
  original output (including failures), and do not treat simulated material as
  real market evidence.
- The current archived live-model record is
  `stage2_evidence/04_live_runs/U1-U6-live-20260911-193404.json`. It contains
  the six raw results and their trace metadata; earlier runs are retained as
  the repair history.
- The frozen final system version is tag
  `ventureai-v2-stage3-2026-09-15` at commit `7975302`. Presentation files
  created after the freeze do not change that system version.
- The final classroom handoff, including acceptance hardening and the three
  assistant-specific material sets, is tag
  `ventureai-v2-stage3-final-2026-09-16` on branch `HC`.

## Known limits before final submission

- Cross-group testing has been cancelled by the teacher and is not included.
- The same-condition V1/V2 comparison is archived in
  `stage2_evidence/05_v1_v2_comparison/`. The V2 baseline and final classroom
  handoff tags are listed above.
