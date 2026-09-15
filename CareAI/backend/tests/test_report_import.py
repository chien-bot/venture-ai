from app.schemas import ReportImportPreviewRequest
from app.services.report_import import preview_report_import


def test_report_text_preview_extracts_draft_and_requires_confirmation() -> None:
    preview = preview_report_import(ReportImportPreviewRequest(
        source_filename="checkup.txt",
        text="报告日期：2026-08-20\n年龄：30\n性别：女\n身高：165 cm\n体重：62 kg\n血压：128/82\n空腹血糖：5.8 mmol/L",
    ))
    assert preview.extraction_status == "needs_confirmation"
    assert preview.recorded_at.isoformat() == "2026-08-20"
    assert preview.height_cm == 165
    assert preview.systolic_bp == 128
    assert "当前版本不执行 PDF／图片 OCR" in preview.notices[-1]


def test_report_text_preview_does_not_invent_missing_values() -> None:
    preview = preview_report_import(ReportImportPreviewRequest(text="这是没有数值的报告文字。"))
    assert preview.height_cm is None
    assert preview.extracted_fields == []
