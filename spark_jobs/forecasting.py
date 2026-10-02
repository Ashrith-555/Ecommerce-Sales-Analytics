"""
Fast time-series forecasting for dashboard ML cards.

Trains only on small monthly aggregates (typically < 150 points), so model
selection stays in the low-milliseconds range and does not slow the UI.
Spark remains the heavy step; this module is lightweight sklearn only.
"""
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score
from sklearn.base import clone

MONTHS_MAP = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def _default_month_nums(length):
    return [((i % 12) + 1) for i in range(length)]


def _build_features(indices, month_nums):
    """Trend + yearly seasonality (sin/cos month)."""
    t = np.asarray(indices, dtype=float)
    months = np.asarray(month_nums, dtype=float)
    sin_m = np.sin(2 * np.pi * months / 12.0)
    cos_m = np.cos(2 * np.pi * months / 12.0)
    return np.column_stack([t, sin_m, cos_m])


def _candidate_models():
    return {
        "ridge_seasonal": Ridge(alpha=8.0, random_state=42),
        "linear_seasonal": LinearRegression(),
        "gbr_seasonal": GradientBoostingRegressor(
            n_estimators=35,
            max_depth=3,
            learning_rate=0.08,
            subsample=0.9,
            random_state=42,
        ),
    }


def _score_model(model, X, y):
    """Time-series cross-validated R² (higher is better)."""
    n = len(y)
    if n < 8:
        model_fit = clone(model)
        model_fit.fit(X, y)
        preds = model_fit.predict(X)
        return r2_score(y, preds)

    splits = min(3, n // 4)
    tscv = TimeSeriesSplit(n_splits=splits)
    scores = []

    for train_idx, val_idx in tscv.split(X):
        m = clone(model)
        m.fit(X[train_idx], y[train_idx])
        preds = m.predict(X[val_idx])
        scores.append(r2_score(y[val_idx], preds))

    return float(np.mean(scores))


def _pick_best_model(X, y):
    best_name = "linear_seasonal"
    best_score = -np.inf
    best_model = LinearRegression()

    for name, model in _candidate_models().items():
        try:
            score = _score_model(model, X, y)
            if score > best_score:
                best_score = score
                best_name = name
                best_model = model
        except Exception:
            continue

    fitted = clone(best_model)
    fitted.fit(X, y)
    return fitted, best_name, best_score


def _accuracy_from_r2(r2):
    if r2 is None or np.isnan(r2):
        return 0.0
    return round(float(max(0.0, min(99.0, r2 * 100.0))), 1)


def _future_month_nums(last_month, count):
    months = []
    m = int(last_month)
    for _ in range(count):
        m += 1
        if m > 12:
            m = 1
        months.append(m)
    return months


def _future_labels(last_year, last_month, count=3):
    labels = []
    y = int(last_year)
    m = int(last_month)
    for _ in range(count):
        m += 1
        if m > 12:
            m = 1
            y += 1
        labels.append(f"{MONTHS_MAP[m]} {y}")
    return labels


def forecast_time_series(
    values,
    month_nums=None,
    horizon=3,
    last_year=None,
    last_month=None,
):
    """
    Auto-select the best fast sklearn model and forecast the next `horizon` steps.

    Returns the same dict shape used by prediction.generate_dynamic_forecast().
    """
    empty = {
        "forecast_value": 0.0,
        "forecast_accuracy": 0.0,
        "forecast_trend": 0.0,
        "trend_class": "up",
        "historical_labels": [],
        "historical_values": [],
        "forecast_labels": [],
        "forecast_values": [],
        "model_name": "none",
    }

    if not values:
        return empty

    y = np.asarray(values, dtype=float)
    n = len(y)
    months = list(month_nums) if month_nums and len(month_nums) == n else _default_month_nums(n)
    indices = list(range(n))

    # Build historical labels from month sequence when year context exists
    if last_year is not None and last_month is not None:
        cy, cm = int(last_year), int(last_month)
        hist_labels = []
        for i in range(n - 1, -1, -1):
            hist_labels.append(f"{MONTHS_MAP[cm]} {cy}")
            cm -= 1
            if cm < 1:
                cm = 12
                cy -= 1
        historical_labels = list(reversed(hist_labels))
    else:
        historical_labels = [f"Period {i + 1}" for i in range(n)]

    if n < 2:
        val = float(y[-1]) if n else 0.0
        return {
            **empty,
            "forecast_value": round(val, 2),
            "forecast_accuracy": 75.0,
            "forecast_labels": ["Next Period"],
            "forecast_values": [round(val, 2)],
            "historical_labels": historical_labels,
            "historical_values": [round(float(v), 2) for v in y.tolist()],
            "model_name": "fallback",
        }

    X = _build_features(indices, months)
    model, model_name, _cv_score = _pick_best_model(X, y)

    last_idx = n - 1
    future_months = _future_month_nums(months[-1], horizon)
    future_indices = [last_idx + i for i in range(1, horizon + 1)]
    X_future = _build_features(future_indices, future_months)
    forecast_values = [max(0.0, float(v)) for v in model.predict(X_future)]

    in_sample_pred = model.predict(X)
    r2 = r2_score(y, in_sample_pred)
    accuracy = _accuracy_from_r2(r2)

    forecast_value = forecast_values[0]
    last_actual = float(y[-1])
    trend = ((forecast_value - last_actual) / last_actual * 100) if last_actual > 0 else 0.0

    forecast_labels = (
        _future_labels(last_year, last_month, horizon)
        if last_year is not None and last_month is not None
        else [f"Next +{i}" for i in range(1, horizon + 1)]
    )

    return {
        "forecast_value": round(forecast_value, 2),
        "forecast_accuracy": accuracy,
        "forecast_trend": round(trend, 1),
        "trend_class": "up" if trend >= 0 else "down",
        "historical_labels": historical_labels,
        "historical_values": [round(float(v), 2) for v in y.tolist()],
        "forecast_labels": forecast_labels,
        "forecast_values": [round(v, 2) for v in forecast_values],
        "model_name": model_name,
    }


def forecast_simple(values, month_nums=None):
    """Compact tuple for dynamic dashboard: (value, trend_pct, accuracy_pct)."""
    result = forecast_time_series(values, month_nums=month_nums, horizon=1)
    return (
        result["forecast_value"],
        result["forecast_trend"],
        result["forecast_accuracy"],
    )
