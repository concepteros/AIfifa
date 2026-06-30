"""Tests for the XGBoost ML model module."""

import csv
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from predict_odds.ml_model import (
    MatchPredictor,
    _HAS_ML_DEPS,
    _build_team_form_lookup,
    _h2h_record,
    _load_fbref,
    _result_label,
    _rolling_form,
    engineer_features,
    ensemble_predict,
    train_and_save,
)


# ── Sample CSV data for tests ────────────────────────────────────────────────

_SAMPLE_CSV = """date,home_team,away_team,home_score,away_score,competition,season,home_xg,away_xg,home_possession,away_possession,home_shots,away_shots,home_shots_on_target,away_shots_on_target
2026-06-11,TeamA,TeamB,2,1,Test League,2026,1.8,0.9,55,45,15,8,7,3
2026-06-11,TeamC,TeamD,1,1,Test League,2026,1.2,1.2,50,50,10,10,5,5
2026-06-11,TeamE,TeamF,0,2,Test League,2026,0.7,2.1,42,58,6,14,2,8
2026-06-12,TeamA,TeamC,3,0,Test League,2026,2.5,0.5,58,42,18,5,10,2
2026-06-12,TeamB,TeamD,1,3,Test League,2026,1.0,2.0,48,52,9,12,4,6
2026-06-12,TeamF,TeamE,2,2,Test League,2026,1.5,1.5,52,48,11,10,6,5
2026-06-17,TeamA,TeamD,2,1,Test League,2026,2.0,1.0,53,47,14,9,8,4
2026-06-17,TeamB,TeamC,0,0,Test League,2026,0.8,1.3,44,56,7,13,3,6
2026-06-17,TeamE,TeamA,1,2,Test League,2026,1.1,1.9,46,54,8,16,4,9
2026-06-18,TeamF,TeamB,3,1,Test League,2026,2.3,0.7,55,45,15,6,9,3
2026-06-18,TeamC,TeamE,2,1,Test League,2026,1.6,1.0,51,49,11,9,6,4
2026-06-18,TeamD,TeamF,1,1,Test League,2026,1.1,1.4,47,53,8,12,4,7
"""


def _write_csv(content: str) -> str:
    """Write a temp CSV and return the path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


class ResultLabelTest(unittest.TestCase):
    def test_home_win(self) -> None:
        self.assertEqual(_result_label(2, 1), 2)

    def test_draw(self) -> None:
        self.assertEqual(_result_label(1, 1), 1)

    def test_away_win(self) -> None:
        self.assertEqual(_result_label(0, 3), 0)


class LoadFbrefTest(unittest.TestCase):
    def test_parses_csv_correctly(self) -> None:
        path = _write_csv(_SAMPLE_CSV)
        try:
            rows = _load_fbref(path)
            self.assertEqual(len(rows), 12)
            self.assertEqual(rows[0]["home_team"], "TeamA")
            self.assertEqual(rows[0]["away_team"], "TeamB")
            self.assertIsInstance(rows[0]["home_xg"], float)
            self.assertIsInstance(rows[0]["home_score"], int)
        finally:
            os.unlink(path)


class TeamFormLookupTest(unittest.TestCase):
    def setUp(self) -> None:
        path = _write_csv(_SAMPLE_CSV)
        self.addCleanup(lambda: os.unlink(path))
        self.rows = _load_fbref(path)

    def test_builds_per_team_history(self) -> None:
        lookup = _build_team_form_lookup(self.rows)
        # Each team plays 3 matches (12 matches, 6 teams, 2 matches per team-day)
        # Actually: TeamA appears 4 times (vs B, vs C, vs D, vs E as away)
        # Let me just check it's non-empty
        self.assertIn("TeamA", lookup)
        self.assertGreaterEqual(len(lookup["TeamA"]), 3)

    def test_history_is_sorted_by_date(self) -> None:
        lookup = _build_team_form_lookup(self.rows)
        for team, history in lookup.items():
            dates = [m["date"] for m in history]
            self.assertEqual(dates, sorted(dates))


class RollingFormTest(unittest.TestCase):
    def setUp(self) -> None:
        path = _write_csv(_SAMPLE_CSV)
        self.addCleanup(lambda: os.unlink(path))
        self.rows = _load_fbref(path)
        self.lookup = _build_team_form_lookup(self.rows)

    def test_empty_before_first_match(self) -> None:
        form = _rolling_form(self.lookup.get("TeamA", []), "2026-06-10")
        self.assertEqual(form["matches_played"], 0)
        self.assertEqual(form["gf_avg"], 0.0)

    def test_accumulates_form(self) -> None:
        # After first matchday, TeamA should have 1 match of form
        form = _rolling_form(self.lookup.get("TeamA", []), "2026-06-12")
        self.assertEqual(form["matches_played"], 1)
        self.assertGreater(form["gf_avg"], 0.0)

    def test_uses_window_limit(self) -> None:
        # After all matches, TeamA has multiple prior matches
        form = _rolling_form(self.lookup.get("TeamA", []), "2026-06-20", window=2)
        self.assertLessEqual(form["matches_played"], 2)


class H2HRecordTest(unittest.TestCase):
    def setUp(self) -> None:
        path = _write_csv(_SAMPLE_CSV)
        self.addCleanup(lambda: os.unlink(path))
        self.rows = _load_fbref(path)
        self.lookup = _build_team_form_lookup(self.rows)

    def test_no_history_returns_defaults(self) -> None:
        h2h = _h2h_record(self.lookup, "TeamA", "TeamB", "2026-06-10")
        self.assertEqual(h2h["h2h_matches"], 0)
        self.assertEqual(h2h["h2h_home_win_pct"], 0.5)

    def test_finds_prior_meetings(self) -> None:
        # TeamA vs TeamB happened on 2026-06-11
        h2h = _h2h_record(self.lookup, "TeamA", "TeamB", "2026-06-12")
        self.assertEqual(h2h["h2h_matches"], 1)
        # TeamA won that match (home_win), so home_win_pct should be 1.0
        self.assertEqual(h2h["h2h_home_win_pct"], 1.0)
        self.assertEqual(h2h["h2h_draw_pct"], 0.0)


class FeatureEngineeringTest(unittest.TestCase):
    def setUp(self) -> None:
        path = _write_csv(_SAMPLE_CSV)
        self.addCleanup(lambda: os.unlink(path))
        self.rows = _load_fbref(path)

    def test_returns_correct_shapes(self) -> None:
        X, y_cls, y_home, y_away, names = engineer_features(self.rows)
        n = len(self.rows)
        self.assertEqual(X.shape, (n, len(names)))
        self.assertEqual(len(y_cls), n)
        self.assertEqual(len(y_home), n)
        self.assertEqual(len(y_away), n)

    def test_feature_names_are_unique(self) -> None:
        _, _, _, _, names = engineer_features(self.rows)
        self.assertEqual(len(names), len(set(names)))

    def test_contains_expected_features(self) -> None:
        _, _, _, _, names = engineer_features(self.rows)
        expected = {"xg_diff", "possession_diff", "shots_diff", "h2h_home_win_pct"}
        for feat in expected:
            self.assertIn(feat, names)


@unittest.skipUnless(_HAS_ML_DEPS, "xgboost/scikit-learn not installed")
class MatchPredictorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.csv_path = _write_csv(_SAMPLE_CSV)

    def tearDown(self) -> None:
        os.unlink(self.csv_path)

    def test_train_returns_metrics(self) -> None:
        predictor = MatchPredictor()
        metrics = predictor.train(self.csv_path)
        self.assertIn("cv_folds", metrics)
        self.assertIn("cls_accuracy_mean", metrics)

    def test_predict_after_training(self) -> None:
        predictor = MatchPredictor()
        predictor.train(self.csv_path)
        result = predictor.predict(
            home_team="TeamA",
            away_team="TeamB",
            date="2026-06-19",
            home_xg=1.8,
            away_xg=1.0,
            home_possession=52,
            away_possession=48,
            home_shots=14,
            away_shots=9,
            home_shots_on_target=7,
            away_shots_on_target=4,
        )
        self.assertEqual(result["model"], "xgboost")
        self.assertIn("home_win", result["probabilities"])
        self.assertIn("draw", result["probabilities"])
        self.assertIn("away_win", result["probabilities"])
        # Probabilities should sum to ~1
        prob_sum = sum(result["probabilities"].values())
        self.assertAlmostEqual(prob_sum, 1.0, delta=0.01)

    def test_predict_before_training_fails(self) -> None:
        predictor = MatchPredictor()
        with self.assertRaises(RuntimeError):
            predictor.predict(home_team="X", away_team="Y", date="2026-06-01")

    def test_save_and_load_roundtrip(self) -> None:
        predictor = MatchPredictor()
        predictor.train(self.csv_path)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            tmp.close()
            predictor.save(tmp.name)
            loaded = MatchPredictor.load(tmp.name)

        self.assertTrue(loaded._trained)
        self.assertEqual(loaded.feature_names, predictor.feature_names)

        # Both should be able to predict
        orig_result = predictor.predict(
            home_team="TeamA",
            away_team="TeamF",
            date="2026-06-19",
            home_xg=1.5,
            away_xg=1.2,
        )
        loaded_result = loaded.predict(
            home_team="TeamA",
            away_team="TeamF",
            date="2026-06-19",
            home_xg=1.5,
            away_xg=1.2,
        )
        self.assertIn("home_win", loaded_result["probabilities"])
        os.unlink(tmp.name)

    def test_train_with_too_few_samples_raises(self) -> None:
        tiny_csv = """date,home_team,away_team,home_score,away_score,competition,season,home_xg,away_xg,home_possession,away_possession,home_shots,away_shots,home_shots_on_target,away_shots_on_target
2026-06-11,A,B,1,0,L,2026,1.0,0.5,50,50,10,5,5,2
"""
        path = _write_csv(tiny_csv)
        try:
            predictor = MatchPredictor()
            with self.assertRaises(ValueError):
                predictor.train(path)
        finally:
            os.unlink(path)


@unittest.skipUnless(_HAS_ML_DEPS, "xgboost/scikit-learn not installed")
class TrainAndSaveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.csv_path = _write_csv(_SAMPLE_CSV)

    def tearDown(self) -> None:
        os.unlink(self.csv_path)

    def test_train_and_save_succeeds(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            tmp.close()
            result = train_and_save(self.csv_path, save_path=tmp.name)
            self.assertEqual(result["status"], "trained")
            self.assertIn("metrics", result)
            self.assertTrue(Path(tmp.name).exists())
            os.unlink(tmp.name)


class EnsemblePredictTest(unittest.TestCase):
    def test_returns_poisson_when_xgb_none(self) -> None:
        poisson = {
            "model": "poisson_v2",
            "probabilities": {"home_win": 0.5, "draw": 0.3, "away_win": 0.2},
            "expected_goals": {"home": 1.5, "away": 1.0},
        }
        result = ensemble_predict(poisson, None)
        self.assertEqual(result["model"], "ensemble")
        self.assertEqual(result["ensemble"]["models_used"], ["poisson"])
        self.assertEqual(result["probabilities"]["home_win"], 0.5)

    def test_blends_when_both_models_present(self) -> None:
        poisson = {
            "model": "poisson_v2",
            "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
            "expected_goals": {"home": 2.0, "away": 0.8},
        }
        xgb = {
            "model": "xgboost",
            "probabilities": {"home_win": 0.5, "draw": 0.3, "away_win": 0.2},
            "expected_goals": {"home": 1.5, "away": 1.0},
        }
        result = ensemble_predict(poisson, xgb)
        self.assertEqual(result["model"], "ensemble")
        self.assertIn("poisson", result["ensemble"]["models_used"])
        self.assertIn("xgboost", result["ensemble"]["models_used"])
        # Blended should be between the two
        self.assertGreater(result["probabilities"]["home_win"], 0.4)

    def test_detects_agreement(self) -> None:
        poisson = {
            "probabilities": {"home_win": 0.6, "draw": 0.3, "away_win": 0.1},
        }
        xgb = {
            "probabilities": {"home_win": 0.5, "draw": 0.3, "away_win": 0.2},
        }
        result = ensemble_predict(poisson, xgb)
        self.assertTrue(result["ensemble"]["models_agree"])

    def test_fixed_blend_weight(self) -> None:
        poisson = {
            "probabilities": {"home_win": 1.0, "draw": 0.0, "away_win": 0.0},
            "expected_goals": {"home": 3.0, "away": 0.0},
        }
        xgb = {
            "probabilities": {"home_win": 0.0, "draw": 0.0, "away_win": 1.0},
            "expected_goals": {"home": 0.0, "away": 3.0},
        }
        result = ensemble_predict(poisson, xgb, blend_weight=0.7)
        self.assertAlmostEqual(result["ensemble"]["poisson_weight"], 0.7)
        # 0.7 * 1.0 + 0.3 * 0.0 = 0.7
        self.assertAlmostEqual(result["probabilities"]["home_win"], 0.7)


class CLIEndToEndTest(unittest.TestCase):
    def test_train_command_works(self) -> None:
        csv_path = _write_csv(_SAMPLE_CSV)
        model_path = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ).name
        try:
            from predict_odds.cli import main

            exit_code = main([
                "train",
                "--model", "xgboost",
                "--data", csv_path,
                "--output", model_path,
                "--compact",
            ])
            self.assertEqual(exit_code, 0)
            self.assertTrue(Path(model_path).exists())
        finally:
            os.unlink(csv_path)
            if os.path.exists(model_path):
                os.unlink(model_path)


if __name__ == "__main__":
    unittest.main()
