"""Conservative extraction of common fields from user-provided report text.

This intentionally does not claim to read images or PDFs. Every extracted value is
returned as a draft and requires explicit confirmation in the client before use.
"""

import re
from datetime import date

from app.schemas import Gender, ReportImportPreview, ReportImportPreviewRequest


def _number_after(labels: list[str], text: str, unit: str = "") -> float | None:
    joined = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{joined})\s*[:：]?\s*(\d+(?:\.\d+)?)\s*{unit}", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def preview_report_import(payload: ReportImportPreviewRequest) -> ReportImportPreview:
    text = payload.text.replace("\u3000", " ")
    fields: list[str] = []
    notices = ["系统只从你提供的文字中提取常见数值；所有结果必须由你核对后才会写入健康 Memory。"]

    height = _number_after(["身高", "height"], text, "(?:cm|厘米)?")
    weight = _number_after(["体重", "weight"], text, "(?:kg|公斤)?")
    glucose = _number_after(["空腹血糖", "fasting glucose", "FPG"], text, "(?:mmol/L)?")
    sleep = _number_after(["睡眠", "sleep"], text, "(?:小时|h|hours)?")
    exercise = _number_after(["每周运动", "运动天数", "exercise days"], text, "(?:天|days)?")
    bp_match = re.search(r"(?:血压|blood pressure|BP)\s*[:：]?\s*(\d{2,3})\s*/\s*(\d{2,3})", text, re.IGNORECASE)
    date_match = re.search(r"(?:检查日期|报告日期|日期|date)\s*[:：]?\s*(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text, re.IGNORECASE)
    age_match = re.search(r"(?:年龄|age)\s*[:：]?\s*(\d{1,3})", text, re.IGNORECASE)
    gender_match = re.search(r"(?:性别|gender)\s*[:：]?\s*(男|女|male|female|其他|other)", text, re.IGNORECASE)

    for value, label in ((height, "身高"), (weight, "体重"), (glucose, "空腹血糖"), (sleep, "睡眠"), (exercise, "每周运动天数")):
        if value is not None:
            fields.append(label)
    if bp_match:
        fields.append("血压")

    recorded_at = None
    if date_match:
        try:
            recorded_at = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            fields.append("报告日期")
        except ValueError:
            notices.append("检测到的报告日期格式无效，未自动填入。")

    gender = None
    if gender_match:
        value = gender_match.group(1).lower()
        gender = Gender.MALE if value in {"男", "male"} else Gender.FEMALE if value in {"女", "female"} else Gender.OTHER
        fields.append("性别")
    age = int(age_match.group(1)) if age_match and 18 <= int(age_match.group(1)) <= 120 else None
    if age is not None:
        fields.append("年龄")
    if not fields:
        notices.append("未识别到可直接使用的指标。请检查文字格式，或手动填写健康记录。")
    notices.append("当前版本不执行 PDF／图片 OCR；请复制电子报告文字、上传 TXT，或使用课堂样例。")

    return ReportImportPreview(
        source_filename=payload.source_filename, recorded_at=recorded_at, age=age, gender=gender,
        height_cm=height, weight_kg=weight, systolic_bp=int(bp_match.group(1)) if bp_match else None,
        diastolic_bp=int(bp_match.group(2)) if bp_match else None, fasting_blood_glucose_mmol_l=glucose,
        sleep_hours=sleep, exercise_days_per_week=int(exercise) if exercise is not None and exercise.is_integer() else None,
        extracted_fields=fields, notices=notices,
    )
