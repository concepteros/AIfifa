"""
XGBoost-based match outcome prediction model that complements the Poisson model.

Provides:
- MatchPredictor: trains XGBoost classifier + regressor on historical match data
- ensemble_predict(): blends Poisson and XGBoost predictions for higher confidence
- CLI integration: python -m predict_odds train --model xgboost
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

# ── Optional dependency handling ──────────────────────────────────────────────
try:
    import xgboost as xgb
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler

    _HAS_ML_DEPS = True
except ImportError:
    _HAS_ML_DEPS = False
    xgb = None  # type: ignore[assignment]
    CalibratedClassifierCV = None  # type: ignore[assignment]
    TimeSeriesSplit = None  # type: ignore[assignment]
    StandardScaler = None  # type: ignore[assignment]

# ── Constants ─────────────────────────────────────────────────────────────────
MODEL_SAVE_PATH_DEFAULT = "data/xgboost_model.json"
MIN_TRAIN_SAMPLES = 6
FEATURE_WINDOW = 3  # number of prior matches for rolling form
XGB_PARAMS = {
    "max_depth": 3,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.5,
    "reg_lambda": 1.0,
    "min_child_weight": 3,
    "random_state": 42,
    "verbosity": 0,
    "objective": "multi:softprob",
    "num_class": 3,
}
REGRESSOR_PARAMS = {
    "max_depth": 3,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.5,
    "reg_lambda": 1.0,
    "min_child_weight": 3,
    "random_state": 42,
    "verbosity": 0,
    "objective": "reg:squarederror",
}


def _check_deps() -> None:
    """Raise ImportError with install instructions if ML deps are missing."""
    if not _HAS_ML_DEPS:
        raise ImportError(
            "xgboost and scikit-learn are required for ML model support. "
            "Install with: pip install xgboost scikit-learn"
        )


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_fbref(path: str | Path) -> list[dict[str, Any]]:
    """Load fbref.csv into a list of row dicts with numeric columns parsed."""
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed: dict[str, Any] = {}
            for key, val in row.items():
                key_clean = key.strip().lower().replace(" ", "_")
                # Try numeric conversion
                try:
                    parsed[key_clean] = float(val) if "." in val or "e" in val.lower() else int(val)
                except (ValueError, TypeError):
                    parsed[key_clean] = val.strip()
            rows.append(parsed)
    return rows


def _result_label(home_score: int, away_score: int) -> int:
    """Convert score to classification label: 2=home_win, 1=draw, 0=away_win."""
    if home_score > away_score:
        return 2
    if home_score == away_score:
        return 1
    return 0


# ── Feature engineering ───────────────────────────────────────────────────────

def _build_team_form_lookup(
    rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Build a per-team list of match stats, sorted by date ascending.
    Each entry is the team's stats from that match (goals, xG, possession, etc.).
    """
    team_matches: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        home = row["home_team"]
        away = row["away_team"]
        date = row["date"]

        home_stats = {
            "date": date,
            "goals_for": row["home_score"],
            "goals_against": row["away_score"],
            "xg_for": row["home_xg"],
            "xg_against": row["away_xg"],
            "possession": row["home_possession"],
            "shots": row["home_shots"],
            "shots_on_target": row["home_shots_on_target"],
            "opponent": away,
            "venue": "home",
            "result": _result_label(row["home_score"], row["away_score"]),
        }
        away_stats = {
            "date": date,
            "goals_for": row["away_score"],
            "goals_against": row["home_score"],
            "xg_for": row["away_xg"],
            "xg_against": row["home_xg"],
            "possession": row["away_possession"],
            "shots": row["away_shots"],
            "shots_on_target": row["away_shots_on_target"],
            "opponent": home,
            "venue": "away",
            "result": _result_label(row["away_score"], row["home_score"]),
        }

        team_matches.setdefault(home, []).append(home_stats)
        team_matches.setdefault(away, []).append(away_stats)

    # Sort each team's matches by date
    for team in team_matches:
        team_matches[team].sort(key=lambda m: m["date"])
    return team_matches


def _rolling_form(team_history: list[dict[str, Any]], before_date: str, window: int = FEATURE_WINDOW) -> dict[str, float]:
    """Compute rolling averages from matches strictly before `before_date`."""
    prior = [m for m in team_history if m["date"] < before_date]
    recent = prior[-window:] if len(prior) >= window else prior
    n = len(recent)
    if n == 0:
        return {
            "gf_avg": 0.0,
            "ga_avg": 0.0,
            "xg_for_avg": 0.0,
            "xg_against_avg": 0.0,
            "possession_avg": 0.0,
            "shots_avg": 0.0,
            "shots_on_target_avg": 0.0,
            "points_per_game": 0.0,
            "matches_played": 0,
        }

    def _avg(key: str) -> float:
        return sum(m[key] for m in recent) / n

    points = sum(
        3 if m["result"] == 2 else (1 if m["result"] == 1 else 0)
        for m in recent
    )
    # Points are from team's perspective — result is encoded with team as "home" lens
    # Actually, result in team_history always uses the encoding where the team is "home"
    # Let me re-read: in _build_team_form_lookup, result is always encoded relative
    # to the team being treated as "home" in the stats dict. So result=2 means the
    # team won, result=1 draw, result=0 loss. That's correct.
    return {
        "gf_avg": _avg("goals_for"),
        "ga_avg": _avg("goals_against"),
        "xg_for_avg": _avg("xg_for"),
        "xg_against_avg": _avg("xg_against"),
        "possession_avg": _avg("possession"),
        "shots_avg": _avg("shots"),
        "shots_on_target_avg": _avg("shots_on_target"),
        "points_per_game": points / n if n > 0 else 0.0,
        "matches_played": n,
    }


def _h2h_record(
    team_matches: dict[str, list[dict[str, Any]]],
    home_team: str,
    away_team: str,
    before_date: str,
) -> dict[str, float]:
    """Compute head-to-head record between two teams before a given date."""
    home_history = team_matches.get(home_team, [])

    # Only count from home team's perspective to avoid double-counting
    home_vs_away = [
        m for m in home_history
        if m["opponent"] == away_team and m["date"] < before_date
    ]

    total = len(home_vs_away)
    if total == 0:
        return {"h2h_matches": 0, "h2h_home_win_pct": 0.5, "h2h_draw_pct": 0.0}

    home_wins = sum(1 for m in home_vs_away if m["result"] == 2)
    draws = sum(1 for m in home_vs_away if m["result"] == 1)

    return {
        "h2h_matches": float(total),
        "h2h_home_win_pct": home_wins / total,
        "h2h_draw_pct": draws / total,
    }


def engineer_features(
    rows: list[dict[str, Any]],
    *,
    window: int = FEATURE_WINDOW,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """
    Build feature matrix X and targets (y_cls, y_home_goals, y_away_goals).

    Returns:
        X: feature matrix (n_samples, n_features)
        y_cls: classification labels (2=home_win, 1=draw, 0=away_win)
        y_home: home goals target
        y_away: away goals target
        feature_names: list of feature column names
    """
    team_matches = _build_team_form_lookup(rows)

    feature_rows: list[list[float]] = []
    y_cls: list[int] = []
    y_home: list[float] = []
    y_away: list[float] = []

    for row in rows:
        home = row["home_team"]
        away = row["away_team"]
        date = row["date"]

        # ── Rolling form ──
        home_form = _rolling_form(team_matches.get(home, []), date, window=window)
        away_form = _rolling_form(team_matches.get(away, []), date, window=window)

        # ── H2H ──
        h2h = _h2h_record(team_matches, home, away, date)

        # ── Match-level features ──
        home_xg = float(row["home_xg"])
        away_xg = float(row["away_xg"])
        home_poss = float(row["home_possession"])
        away_poss = float(row["away_possession"])
        home_shots = float(row["home_shots"])
        away_shots = float(row["away_shots"])
        home_sot = float(row["home_shots_on_target"])
        away_sot = float(row["away_shots_on_target"])

        features = [
            # Match-level diffs
            home_xg - away_xg,                          # xg_diff
            home_poss - away_poss,                       # possession_diff
            home_shots - away_shots,                     # shots_diff
            home_sot - away_sot,                         # shots_on_target_diff
            home_xg,                                     # home_xg
            away_xg,                                     # away_xg
            # Home team form
            home_form["gf_avg"],                         # home_gf_form
            home_form["ga_avg"],                         # home_ga_form
            home_form["xg_for_avg"],                     # home_xg_for_form
            home_form["xg_against_avg"],                 # home_xg_against_form
            home_form["possession_avg"],                 # home_possession_form
            home_form["shots_avg"],                      # home_shots_form
            home_form["points_per_game"],                # home_ppg_form
            # Away team form
            away_form["gf_avg"],                         # away_gf_form
            away_form["ga_avg"],                         # away_ga_form
            away_form["xg_for_avg"],                     # away_xg_for_form
            away_form["xg_against_avg"],                 # away_xg_against_form
            away_form["possession_avg"],                 # away_possession_form
            away_form["shots_avg"],                      # away_shots_form
            away_form["points_per_game"],                # away_ppg_form
            # Form diffs
            home_form["xg_for_avg"] - away_form["xg_against_avg"],   # xg_form_diff
            home_form["points_per_game"] - away_form["points_per_game"],  # ppg_diff
            # H2H
            h2h["h2h_home_win_pct"],                     # h2h_home_win_pct
            h2h["h2h_draw_pct"],                         # h2h_draw_pct
            h2h["h2h_matches"],                          # h2h_matches
        ]

        feature_rows.append(features)
        y_cls.append(_result_label(int(row["home_score"]), int(row["away_score"])))
        y_home.append(float(row["home_score"]))
        y_away.append(float(row["away_score"]))

    feature_names = [
        "xg_diff", "possession_diff", "shots_diff", "shots_on_target_diff",
        "home_xg", "away_xg",
        "home_gf_form", "home_ga_form", "home_xg_for_form", "home_xg_against_form",
        "home_possession_form", "home_shots_form", "home_ppg_form",
        "away_gf_form", "away_ga_form", "away_xg_for_form", "away_xg_against_form",
        "away_possession_form", "away_shots_form", "away_ppg_form",
        "xg_form_diff", "ppg_diff",
        "h2h_home_win_pct", "h2h_draw_pct", "h2h_matches",
    ]

    return (
        np.array(feature_rows, dtype=np.float64),
        np.array(y_cls, dtype=np.int64),
        np.array(y_home, dtype=np.float64),
        np.array(y_away, dtype=np.float64),
        feature_names,
    )


def _build_single_match_features(
    home_team: str,
    away_team: str,
    date: str,
    home_xg: float,
    away_xg: float,
    home_possession: float,
    away_possession: float,
    home_shots: float,
    away_shots: float,
    home_sot: float,
    away_sot: float,
    team_matches: dict[str, list[dict[str, Any]]],
    window: int = FEATURE_WINDOW,
) -> np.ndarray:
    """Build feature vector for a single match (used at prediction time)."""
    home_form = _rolling_form(team_matches.get(home_team, []), date, window=window)
    away_form = _rolling_form(team_matches.get(away_team, []), date, window=window)
    h2h = _h2h_record(team_matches, home_team, away_team, date)

    features = [
        home_xg - away_xg,
        home_possession - away_possession,
        home_shots - away_shots,
        home_sot - away_sot,
        home_xg,
        away_xg,
        home_form["gf_avg"],
        home_form["ga_avg"],
        home_form["xg_for_avg"],
        home_form["xg_against_avg"],
        home_form["possession_avg"],
        home_form["shots_avg"],
        home_form["points_per_game"],
        away_form["gf_avg"],
        away_form["ga_avg"],
        away_form["xg_for_avg"],
        away_form["xg_against_avg"],
        away_form["possession_avg"],
        away_form["shots_avg"],
        away_form["points_per_game"],
        home_form["xg_for_avg"] - away_form["xg_against_avg"],
        home_form["points_per_game"] - away_form["points_per_game"],
        h2h["h2h_home_win_pct"],
        h2h["h2h_draw_pct"],
        h2h["h2h_matches"],
    ]
    return np.array(features, dtype=np.float64).reshape(1, -1)


# ── Main predictor class ──────────────────────────────────────────────────────

class MatchPredictor:
    """XGBoost-based match outcome predictor.

    Trains:
    - A calibrated multi-class classifier for win/draw/loss probabilities
    - Two regressors for expected home and away goals

    Usage:
        predictor = MatchPredictor()
        metrics = predictor.train("data/fbref.csv")
        result = predictor.predict(home_team="Brazil", away_team="Germany", ...)
        predictor.save("data/xgboost_model.json")
    """

    _RESULT_LABELS = ["away_win", "draw", "home_win"]

    def __init__(self) -> None:
        _check_deps()
        self.classifier: CalibratedClassifierCV | None = None
        self.regressor_home: xgb.XGBRegressor | None = None
        self.regressor_away: xgb.XGBRegressor | None = None
        self.scaler: StandardScaler | None = None
        self.feature_names: list[str] = []
        self._train_rows: list[dict[str, Any]] = []
        self._team_matches: dict[str, list[dict[str, Any]]] = {}
        self._trained: bool = False
        self._cv_metrics: dict[str, Any] = {}

    def train(
        self,
        csv_path: str | Path,
        *,
        window: int = FEATURE_WINDOW,
        n_splits: int = 5,
    ) -> dict[str, Any]:
        """
        Train the XGBoost models on historical match data.

        Args:
            csv_path: Path to fbref.csv or similar match data.
            window: Number of prior matches for rolling form features.
            n_splits: Number of time-series cross-validation splits.

        Returns:
            Dict with cross-validation metrics.
        """
        _check_deps()
        rows = _load_fbref(csv_path)
        if len(rows) < MIN_TRAIN_SAMPLES:
            raise ValueError(
                f"Need at least {MIN_TRAIN_SAMPLES} matches to train, got {len(rows)}."
            )

        # Sort by date for time-series integrity
        rows.sort(key=lambda r: r["date"])
        self._train_rows = rows
        self._team_matches = _build_team_form_lookup(rows)

        X, y_cls, y_home, y_away, self.feature_names = engineer_features(rows, window=window)

        # ── Handle NaN/Inf from sparse form features ──
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        # ── Scale features ──
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # ── Cross-validation ──
        cv_metrics = self._cross_validate(X_scaled, y_cls, y_home, y_away, n_splits=n_splits)

        # ── Train final models on all data ──
        # Classifier
        base_clf = xgb.XGBClassifier(**XGB_PARAMS)
        self.classifier = CalibratedClassifierCV(
            estimator=base_clf,
            method="sigmoid",  # Platt scaling for probability calibration
            cv="prefit",  # We'll prefit, but need to handle small data
        )
        # Use TimeSeriesSplit for calibration too
        calib_cv = TimeSeriesSplit(n_splits=min(3, len(X_scaled) // 3))
        self.classifier = CalibratedClassifierCV(
            estimator=xgb.XGBClassifier(**XGB_PARAMS),
            method="sigmoid",
            cv=calib_cv,
        )
        self.classifier.fit(X_scaled, y_cls)

        # Regressors
        self.regressor_home = xgb.XGBRegressor(**REGRESSOR_PARAMS)
        self.regressor_away = xgb.XGBRegressor(**REGRESSOR_PARAMS)
        self.regressor_home.fit(X_scaled, y_home)
        self.regressor_away.fit(X_scaled, y_away)

        self._trained = True
        self._cv_metrics = cv_metrics
        return cv_metrics

    def _cross_validate(
        self,
        X: np.ndarray,
        y_cls: np.ndarray,
        y_home: np.ndarray,
        y_away: np.ndarray,
        n_splits: int = 5,
    ) -> dict[str, Any]:
        """Time-series cross-validation with class-presence checks."""
        n_samples = len(X)
        # With 48 samples, use at most 3 folds to keep ~16 samples/fold
        n_splits = min(n_splits, max(2, n_samples // 16))
        if n_splits < 2:
            return {
                "cv_folds": 0,
                "cls_accuracy_mean": 0.0,
                "cls_accuracy_std": 0.0,
                "home_goals_mae_mean": 0.0,
                "away_goals_mae_mean": 0.0,
                "note": "Insufficient data for cross-validation",
            }

        tscv = TimeSeriesSplit(n_splits=n_splits)
        cls_accuracies: list[float] = []
        home_mae: list[float] = []
        away_mae: list[float] = []
        n_folds = 0

        for train_idx, test_idx in tscv.split(X):
            if len(test_idx) < 2:
                continue
            X_train, X_test = X[train_idx], X[test_idx]
            y_train_cls, y_test_cls = y_cls[train_idx], y_cls[test_idx]
            y_train_h, y_test_h = y_home[train_idx], y_home[test_idx]
            y_train_a, y_test_a = y_away[train_idx], y_away[test_idx]

            # Require all 3 classes (0,1,2) in training to avoid xgboost remapping
            unique_train = set(y_train_cls)
            if len(unique_train) < 3:
                continue

            # Classifier
            clf = xgb.XGBClassifier(**XGB_PARAMS)
            clf.fit(X_train, y_train_cls)
            acc = float((clf.predict(X_test) == y_test_cls).mean())
            cls_accuracies.append(acc)

            # Regressors
            reg_h = xgb.XGBRegressor(**REGRESSOR_PARAMS)
            reg_a = xgb.XGBRegressor(**REGRESSOR_PARAMS)
            reg_h.fit(X_train, y_train_h)
            reg_a.fit(X_train, y_train_a)
            home_mae.append(float(np.abs(reg_h.predict(X_test) - y_test_h).mean()))
            away_mae.append(float(np.abs(reg_a.predict(X_test) - y_test_a).mean()))
            n_folds += 1

        return {
            "cv_folds": n_folds,
            "cls_accuracy_mean": float(np.mean(cls_accuracies)) if cls_accuracies else 0.0,
            "cls_accuracy_std": float(np.std(cls_accuracies)) if cls_accuracies else 0.0,
            "home_goals_mae_mean": float(np.mean(home_mae)) if home_mae else 0.0,
            "away_goals_mae_mean": float(np.mean(away_mae)) if away_mae else 0.0,
        }

    def predict(
        self,
        *,
        home_team: str,
        away_team: str,
        date: str = "",
        home_xg: float = 0.0,
        away_xg: float = 0.0,
        home_possession: float = 50.0,
        away_possession: float = 50.0,
        home_shots: float = 0.0,
        away_shots: float = 0.0,
        home_shots_on_target: float = 0.0,
        away_shots_on_target: float = 0.0,
    ) -> dict[str, Any]:
        """
        Predict match outcome probabilities and expected goals.

        Args:
            home_team: Home team name.
            away_team: Away team name.
            date: Match date (YYYY-MM-DD) for form/h2h lookups.
            home_xg, away_xg: Expected goals stats (optional, use 0 if unknown).
            home_possession, away_possession: Possession stats (optional).
            home_shots, away_shots: Shot counts (optional).
            home_shots_on_target, away_shots_on_target: SOT counts (optional).

        Returns:
            Dict with probabilities, expected goals, and model metadata.
        """
        if not self._trained:
            raise RuntimeError("Model not trained. Call train() first.")

        X = _build_single_match_features(
            home_team=home_team,
            away_team=away_team,
            date=date,
            home_xg=home_xg,
            away_xg=away_xg,
            home_possession=home_possession,
            away_possession=away_possession,
            home_shots=home_shots,
            away_shots=away_shots,
            home_sot=home_shots_on_target,
            away_sot=away_shots_on_target,
            team_matches=self._team_matches,
        )
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        X_scaled = self.scaler.transform(X) if self.scaler else X

        # Classification probabilities (calibrated)
        probs = self.classifier.predict_proba(X_scaled)[0]  # type: ignore[union-attr]
        # Map class indices to labels
        prob_dict: dict[str, float] = {
            self._RESULT_LABELS[i]: round(float(probs[i]), 6)
            for i in range(len(self._RESULT_LABELS))
        }

        # Expected goals
        exp_home = float(self.regressor_home.predict(X_scaled)[0])  # type: ignore[union-attr]
        exp_away = float(self.regressor_away.predict(X_scaled)[0])  # type: ignore[union-attr]
        exp_home = max(0.0, round(exp_home, 3))
        exp_away = max(0.0, round(exp_away, 3))

        # Agreement score between predicted probabilities and expected goals
        # If prob(home_win) > prob(away_win) and exp_home > exp_away -> high confidence
        goals_agree = (exp_home > exp_away and prob_dict["home_win"] > prob_dict["away_win"]) or \
                      (exp_home < exp_away and prob_dict["home_win"] < prob_dict["away_win"]) or \
                      (abs(exp_home - exp_away) < 0.15 and abs(prob_dict["home_win"] - prob_dict["away_win"]) < 0.1)
        max_prob = max(prob_dict.values())
        confidence = "high" if (goals_agree and max_prob > 0.4) else ("medium" if max_prob > 0.35 else "low")

        return {
            "model": "xgboost",
            "probabilities": prob_dict,
            "expected_goals": {
                "home": exp_home,
                "away": exp_away,
            },
            "confidence": confidence,
            "feature_names": self.feature_names,
            "cv_metrics": self._cv_metrics,
        }

    def save(self, path: str | Path) -> None:
        """Save trained models to XGBoost native JSON format plus metadata."""
        if not self._trained:
            raise RuntimeError("Model not trained. Call train() first.")

        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # CalibratedClassifierCV stores calibrated classifiers in calibrated_classifiers_
        # Each _CalibratedClassifier wraps the base estimator in .estimator
        calib_estimators = getattr(self.classifier, "calibrated_classifiers_", [])
        if calib_estimators:
            booster = calib_estimators[0].estimator.get_booster()
        else:
            booster = self.classifier.estimator.get_booster()  # type: ignore[union-attr]
        clf_json = booster.save_raw(raw_format="json")
        reg_home_json = self.regressor_home.get_booster().save_raw(raw_format="json")  # type: ignore[union-attr]
        reg_away_json = self.regressor_away.get_booster().save_raw(raw_format="json")  # type: ignore[union-attr]

        # Save scaler parameters
        scaler_params = {
            "mean_": self.scaler.mean_.tolist() if self.scaler else [],
            "scale_": self.scaler.scale_.tolist() if self.scaler else [],
        }

        model_data = {
            "classifier_raw": clf_json if isinstance(clf_json, str) else clf_json.decode("utf-8"),
            "regressor_home_raw": reg_home_json if isinstance(reg_home_json, str) else reg_home_json.decode("utf-8"),
            "regressor_away_raw": reg_away_json if isinstance(reg_away_json, str) else reg_away_json.decode("utf-8"),
            "scaler": scaler_params,
            "feature_names": self.feature_names,
            "cv_metrics": self._cv_metrics,
            "result_labels": self._RESULT_LABELS,
            # Store training data for form lookups at prediction time
            "train_rows": self._train_rows,
        }

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2, default=str)

    @classmethod
    def load(cls, path: str | Path) -> MatchPredictor:
        """Load trained models from saved JSON."""
        _check_deps()
        load_path = Path(path)
        if not load_path.exists():
            raise FileNotFoundError(f"Model file not found: {load_path}")

        with open(load_path, "r", encoding="utf-8") as f:
            model_data = json.load(f)

        predictor = cls()
        predictor.feature_names = model_data.get("feature_names", [])

        # Rebuild team form lookup from stored training rows
        train_rows = model_data.get("train_rows", [])
        predictor._train_rows = train_rows
        predictor._team_matches = _build_team_form_lookup(train_rows)

        # Rebuild scaler
        scaler_params = model_data.get("scaler", {})
        predictor.scaler = StandardScaler()
        if scaler_params.get("mean_") and scaler_params.get("scale_"):
            predictor.scaler.mean_ = np.array(scaler_params["mean_"])
            predictor.scaler.scale_ = np.array(scaler_params["scale_"])
            # Set fitted flag
            predictor.scaler.n_features_in_ = len(scaler_params["mean_"])

        # Rebuild classifiers
        clf_raw = model_data["classifier_raw"]
        booster_clf = xgb.Booster()
        booster_clf.load_model(bytearray(clf_raw, "utf-8") if isinstance(clf_raw, str) else clf_raw)

        # Rebuild calibrated classifier by re-fitting on stored training data
        predictor.classifier = _rebuild_calibrated_classifier(
            predictor, clf_raw, model_data
        )

        # Regressors
        reg_h_raw = model_data["regressor_home_raw"]
        booster_reg_h = xgb.Booster()
        booster_reg_h.load_model(bytearray(reg_h_raw, "utf-8") if isinstance(reg_h_raw, str) else reg_h_raw)
        predictor.regressor_home = xgb.XGBRegressor(**REGRESSOR_PARAMS)
        predictor.regressor_home._Booster = booster_reg_h

        reg_a_raw = model_data["regressor_away_raw"]
        booster_reg_a = xgb.Booster()
        booster_reg_a.load_model(bytearray(reg_a_raw, "utf-8") if isinstance(reg_a_raw, str) else reg_a_raw)
        predictor.regressor_away = xgb.XGBRegressor(**REGRESSOR_PARAMS)
        predictor.regressor_away._Booster = booster_reg_a

        predictor._cv_metrics = model_data.get("cv_metrics", {})
        predictor._trained = True
        return predictor


def _rebuild_calibrated_classifier(
    predictor: MatchPredictor,
    clf_raw: str,
    model_data: dict[str, Any],
) -> CalibratedClassifierCV:
    """Rebuild calibrated classifier by re-fitting on training data."""
    # Re-engineer features from saved training rows
    train_rows = model_data.get("train_rows", [])
    if not train_rows:
        # Fallback: use base classifier without calibration
        clf = xgb.XGBClassifier(**XGB_PARAMS)
        booster = xgb.Booster()
        booster.load_model(bytearray(clf_raw, "utf-8"))
        clf._Booster = booster
        clf.n_features_in_ = len(predictor.feature_names)
        calib = CalibratedClassifierCV(estimator=xgb.XGBClassifier(**XGB_PARAMS), cv="prefit")
        calib.calibrated_classifiers_ = [clf]
        return calib

    X, y_cls, _, _, _ = engineer_features(train_rows)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    # Scale
    if predictor.scaler:
        X_scaled = predictor.scaler.transform(X)
    else:
        X_scaled = X

    # Fit calibrated classifier on the training data
    n_splits = min(3, max(2, len(X_scaled) // 3))
    calib_cv = TimeSeriesSplit(n_splits=n_splits)
    calib = CalibratedClassifierCV(
        estimator=xgb.XGBClassifier(**XGB_PARAMS),
        method="sigmoid",
        cv=calib_cv,
    )
    calib.fit(X_scaled, y_cls)
    return calib


# ── Ensemble blending ─────────────────────────────────────────────────────────

def ensemble_predict(
    poisson_prediction: dict[str, Any],
    xgb_prediction: dict[str, Any] | None = None,
    *,
    blend_weight: float | None = None,
) -> dict[str, Any]:
    """
    Blend Poisson and XGBoost predictions into an ensemble.

    When both models agree, confidence is boosted. When they disagree,
    the ensemble uses a weighted blend.

    Args:
        poisson_prediction: Output from predict_match() (Poisson model).
        xgb_prediction: Output from MatchPredictor.predict(). If None,
                        returns Poisson prediction as-is with ensemble metadata.
        blend_weight: Weight for Poisson model (0.0-1.0). If None,
                      computed dynamically based on model agreement.

    Returns:
        Ensemble prediction dict with blended probabilities and confidence.
    """
    poisson_probs = poisson_prediction.get("probabilities", {})
    poisson_goals = poisson_prediction.get("expected_goals", {})

    if xgb_prediction is None:
        return {
            **poisson_prediction,
            "model": "ensemble",
            "ensemble": {
                "models_used": ["poisson"],
                "blend_weight": 1.0,
                "agreement": "n/a",
                "note": "XGBoost model not available; Poisson prediction used.",
            },
        }

    xgb_probs = xgb_prediction.get("probabilities", {})

    # ── Compute agreement ──
    poisson_winner = max(poisson_probs, key=lambda k: poisson_probs.get(k, 0))
    xgb_winner = max(xgb_probs, key=lambda k: xgb_probs.get(k, 0))
    models_agree = poisson_winner == xgb_winner

    # ── Dynamic blending weight ──
    if blend_weight is None:
        if models_agree:
            # When both agree, slightly favor the model with higher confidence
            poisson_max = poisson_probs.get(poisson_winner, 0)
            xgb_max = xgb_probs.get(xgb_winner, 0)
            # Weight shifts toward the more confident model
            if poisson_max > xgb_max:
                blend_weight = 0.6
            elif xgb_max > poisson_max:
                blend_weight = 0.4
            else:
                blend_weight = 0.5
        else:
            # Disagreement: default to Poisson with slight weight
            blend_weight = 0.55

    blend_weight = max(0.1, min(0.9, blend_weight))
    xgb_weight = 1.0 - blend_weight

    # ── Blend probabilities ──
    blended_probs: dict[str, float] = {}
    for key in ["home_win", "draw", "away_win"]:
        p_val = poisson_probs.get(key, 0.0)
        x_val = xgb_probs.get(key, 0.0)
        blended_probs[key] = round(blend_weight * p_val + xgb_weight * x_val, 6)

    # ── Blend expected goals ──
    xgb_goals = xgb_prediction.get("expected_goals", {})
    blended_home = round(
        blend_weight * poisson_goals.get("home", 0.0) + xgb_weight * xgb_goals.get("home", 0.0),
        3,
    )
    blended_away = round(
        blend_weight * poisson_goals.get("away", 0.0) + xgb_weight * xgb_goals.get("away", 0.0),
        3,
    )

    # ── Confidence level ──
    if models_agree:
        max_prob = max(blended_probs.values())
        confidence = "high" if max_prob > 0.45 else "medium"
    else:
        confidence = "low"

    return {
        "model": "ensemble",
        "league": poisson_prediction.get("league"),
        "date": poisson_prediction.get("date"),
        "match": poisson_prediction.get("match", {}),
        "expected_goals": {
            "home": blended_home,
            "away": blended_away,
        },
        "probabilities": blended_probs,
        "ensemble": {
            "models_used": ["poisson", "xgboost"],
            "poisson_weight": round(blend_weight, 3),
            "xgboost_weight": round(xgb_weight, 3),
            "models_agree": models_agree,
            "poisson_winner": poisson_winner,
            "xgboost_winner": xgb_winner,
            "confidence": confidence,
        },
        "poisson_raw": {
            "probabilities": poisson_probs,
            "expected_goals": poisson_goals,
        },
        "xgboost_raw": xgb_prediction,
    }


# ── Convenience function ─────────────────────────────────────────────────────

def train_and_save(
    csv_path: str | Path,
    save_path: str | Path = MODEL_SAVE_PATH_DEFAULT,
    **train_kwargs: Any,
) -> dict[str, Any]:
    """Train MatchPredictor on CSV data and save to disk. Returns training metrics."""
    predictor = MatchPredictor()
    metrics = predictor.train(csv_path, **train_kwargs)
    predictor.save(save_path)
    return {
        "status": "trained",
        "save_path": str(save_path),
        "metrics": metrics,
        "n_features": len(predictor.feature_names),
        "feature_names": predictor.feature_names,
    }
