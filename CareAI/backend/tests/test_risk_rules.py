from app.schemas import Gender, HealthDataInput, RiskLevel
from app.services.risk_rules import assess_health_risk
from app.services.risk_config import THRESHOLDS, get_rule_information


def test_rule_configuration_is_versioned_and_reviewable() -> None:
    info = get_rule_information()
    assert info["version"]
    assert info["thresholds"]["bmi_low"] == THRESHOLDS.bmi_low
    assert any(reference["dimension"] == "sleep" for reference in info["references"])


def test_low_risk_profile() -> None:
    data = HealthDataInput(
        age=20,
        gender=Gender.FEMALE,
        height_cm=165,
        weight_kg=55,
        sleep_hours=8,
        exercise_days_per_week=3,
    )
    result = assess_health_risk(data)
    assert result.bmi == 20.2
    assert result.overall_level == RiskLevel.NORMAL


def test_high_risk_profile() -> None:
    data = HealthDataInput(
        age=22,
        gender=Gender.MALE,
        height_cm=170,
        weight_kg=85,
        sleep_hours=5.5,
        exercise_days_per_week=0,
    )
    result = assess_health_risk(data)
    assert result.overall_level == RiskLevel.HIGH_ATTENTION
    assert any(item.category == "BMI" and item.level == RiskLevel.HIGH_ATTENTION for item in result.risks)


def test_client_field_names_are_normalized() -> None:
    data = HealthDataInput.model_validate(
        {
            "age": 22,
            "gender": "male",
            "height": 175,
            "weight": 80,
            "blood_pressure": "145/90",
            "sleep_hours": 5,
            "exercise_frequency": 1,
        }
    )
    result = assess_health_risk(data)
    assert data.systolic_bp == 145
    assert data.diastolic_bp == 90
    assert result.bmi == 26.1
    assert [risk.level for risk in result.risks] == [
        RiskLevel.ATTENTION,
        RiskLevel.HIGH_ATTENTION,
        RiskLevel.ATTENTION,
        RiskLevel.HIGH_ATTENTION,
    ]


def test_optional_fasting_glucose_is_assessed() -> None:
    data = HealthDataInput(
        age=22,
        gender=Gender.MALE,
        height_cm=175,
        weight_kg=70,
        sleep_hours=8,
        exercise_days_per_week=3,
        fasting_blood_glucose_mmol_l=6.5,
    )
    result = assess_health_risk(data)
    glucose_risk = next(item for item in result.risks if item.category == "fasting_blood_glucose")
    assert glucose_risk.level == RiskLevel.ATTENTION
    assert glucose_risk.source == "user_input.blood_glucose"
    assert result.overall_level == RiskLevel.ATTENTION


def test_missing_blood_glucose_does_not_create_glucose_risk() -> None:
    data = HealthDataInput.model_validate(
        {
            "age": 22,
            "gender": "male",
            "height": 175,
            "weight": 80,
            "blood_pressure": "145/90",
            "sleep_hours": 5,
            "exercise_frequency": 1,
        }
    )
    result = assess_health_risk(data)
    assert data.fasting_blood_glucose_mmol_l is None
    assert all(item.category != "fasting_blood_glucose" for item in result.risks)
