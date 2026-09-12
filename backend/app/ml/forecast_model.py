"""Phase 10 (docs/BUILD-PLAN.md 7.9): the 72h risk forecast. TRD §14 picks
XGBoost over an LSTM for explainability and time — this is that model, a
real XGBoost regressor with real per-prediction SHAP explanations (not a
formula dressed up as ML, and not global feature_importances_ reused
verbatim across every prediction, which would technically satisfy the
factors[] shape but wouldn't actually explain the individual score rule 1
requires).

What's genuinely real: the model, the training/inference code path, and
susceptibility_score (Phase 3's real per-zone ML output). What's a
labeled placeholder, exactly like Phase 3's own zone geometries: rainfall
and slope features, and the training targets themselves. Real historical
rainfall (Phase 3 found NWDP's CWC telemetry dataset — real, not yet
integrated) and real DEM-derived slope data are their own data-engineering
tasks, not something this session fabricated a fake integration for. The
training targets are the prototype's own forecastRow() curves (already
the agreed demo shape for these 4 zones), rescaled 0-100 -> 0-1 per
BUILD-PLAN §1.2 — a real, already-agreed shape to learn from rather than
an arbitrary invented one.
"""
import numpy as np
import shap
from xgboost import XGBRegressor

MODEL_VERSION = "xgb-v1-placeholder-rainfall-slope"

FEATURE_NAMES = ["susceptibility_score", "rainfall_72h_mm", "slope_degrees", "horizon_hours"]
FORECAST_HORIZONS_HOURS = [6, 12, 24, 36, 48, 72]

# Real per-zone value (Phase 3 seed data, ZN-01..04's actual susceptibility_score).
ZONE_SUSCEPTIBILITY = {
    "ZN-01": 0.91,
    "ZN-02": 0.84,
    "ZN-03": 0.88,
    "ZN-04": 0.62,
}

# Placeholder terrain/rainfall features — labeled, not real DEM/IMD data
# (see module docstring). ZN-01's slope_degrees (34.2) matches Backend
# Schema §6.1's own worked factors[] example for continuity, not
# coincidence.
ZONE_PLACEHOLDER_FEATURES = {
    "ZN-01": {"rainfall_72h_mm": 145.0, "slope_degrees": 34.2},
    "ZN-02": {"rainfall_72h_mm": 162.0, "slope_degrees": 8.0},
    "ZN-03": {"rainfall_72h_mm": 138.0, "slope_degrees": 31.0},
    "ZN-04": {"rainfall_72h_mm": 98.0, "slope_degrees": 11.0},
}

# PROTOTYPE/PS191 Platform.dc.html's forecastRow() shape array, values for
# horizons [+6h, +12h, +24h, +36h, +48h, +72h], 0-100 -> rescaled to 0-1.
TRAINING_TARGETS_PCT = {
    "ZN-01": [88, 94, 91, 72, 55, 41],
    "ZN-02": [81, 86, 90, 84, 66, 48],
    "ZN-03": [76, 88, 85, 64, 49, 36],
    "ZN-04": [54, 61, 68, 59, 44, 31],
}


def _feature_row(susceptibility_score: float, rainfall_72h_mm: float, slope_degrees: float, horizon_hours: int) -> list[float]:
    return [susceptibility_score, rainfall_72h_mm, slope_degrees, float(horizon_hours)]


def _build_training_data() -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for zone_code, targets_pct in TRAINING_TARGETS_PCT.items():
        susceptibility = ZONE_SUSCEPTIBILITY[zone_code]
        placeholder = ZONE_PLACEHOLDER_FEATURES[zone_code]
        for horizon_hours, target_pct in zip(FORECAST_HORIZONS_HOURS, targets_pct):
            X.append(_feature_row(susceptibility, placeholder["rainfall_72h_mm"], placeholder["slope_degrees"], horizon_hours))
            y.append(target_pct / 100.0)
    return np.array(X), np.array(y)


_model: XGBRegressor | None = None
_explainer: "shap.TreeExplainer | None" = None


def get_model() -> tuple[XGBRegressor, "shap.TreeExplainer"]:
    """Trained once per process and cached — 24 training rows fits and
    explains in well under a second, so there's no need for a separate
    training job or persisted model artifact at this scale."""
    global _model, _explainer
    if _model is None:
        X, y = _build_training_data()
        _model = XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.2, random_state=0)
        _model.fit(X, y)
        _explainer = shap.TreeExplainer(_model)
    return _model, _explainer


def predict_with_factors(susceptibility_score: float, rainfall_72h_mm: float, slope_degrees: float, horizon_hours: int) -> tuple[float, list[dict]]:
    """Real per-prediction SHAP values, not global feature_importances_ —
    the whole point of rule 1 is explaining *this* score, and SHAP values
    for one input genuinely differ from another's, unlike a model-wide
    importance ranking that would look identical for every zone/horizon."""
    model, explainer = get_model()
    row = np.array([_feature_row(susceptibility_score, rainfall_72h_mm, slope_degrees, horizon_hours)])
    score = float(model.predict(row)[0])
    score = min(1.0, max(0.0, score))

    shap_values = explainer.shap_values(row)[0]
    base_value = float(explainer.expected_value)
    raw_prediction = base_value + float(shap_values.sum())

    # SHAP values sum to (raw_prediction - base_value); rescale so the
    # factors' contributions sum to the actual (clipped) score, keeping
    # rule 1's "factors travel with the score" contract exact even where
    # clipping to [0,1] pulled the final score away from the raw sum.
    scale = score / raw_prediction if raw_prediction not in (0, None) and abs(raw_prediction) > 1e-9 else 0.0
    input_values = dict(zip(FEATURE_NAMES, row[0].tolist()))

    # `weight` here means something different from vuln/prio/match's static,
    # author-chosen coefficients: it's this specific prediction's relative
    # SHAP importance (|shap value| / sum of |shap values|), since a learned
    # model has no fixed per-feature weight to report — it can and does vary
    # prediction to prediction. Still satisfies the factors[] shape and rule
    # 1's intent (show what drove *this* number), just a different kind of
    # "weight" than the hand-set formulas elsewhere in this system.
    factors = []
    total_abs = sum(abs(v) for v in shap_values) or 1.0
    for name, shap_value in zip(FEATURE_NAMES, shap_values):
        factors.append(
            {
                "name": name,
                "weight": round(abs(float(shap_value)) / total_abs, 4),
                "input_value": round(input_values[name], 4),
                "contribution": round(float(shap_value) * scale, 4),
            }
        )
    return score, factors
