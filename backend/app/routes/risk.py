from fastapi import APIRouter

from app.schemas.zone import RiskPredictionRequest, RiskPredictionResponse
from app.services.risk_service import calculate_risk
from ml.predict import get_feature_importance, predict_risk_ml

router = APIRouter(tags=["Risk"])


@router.post("/predict-risk", response_model=RiskPredictionResponse)
def predict_risk(payload: RiskPredictionRequest):
    features = payload.model_dump()

    # Always compute the rule-based result: it is the fallback AND it
    # supplies the local, per-prediction risk_factors explanation even
    # when the ML model is used.
    rule_result = calculate_risk(**features)

    ml_result = None
    try:
        ml_result = predict_risk_ml(features)
    except Exception:
        ml_result = None

    if ml_result is not None:
        return RiskPredictionResponse(
            risk_score=ml_result["risk_score"],
            risk_level=ml_result["predicted_risk_level"],
            prediction_source="machine_learning",
            model_available=True,
            risk_factors=rule_result["factors"],
            class_probabilities=ml_result["probabilities"],
            feature_importance=get_feature_importance(),
        )

    return RiskPredictionResponse(
        risk_score=rule_result["risk_score"],
        risk_level=rule_result["risk_level"],
        prediction_source="rule_based_fallback",
        model_available=False,
        risk_factors=rule_result["factors"],
    )
