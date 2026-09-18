from __future__ import annotations

from auragateway.local_abc import final_342_jev_human_calibration_v1 as subject


def test_binary_counts_and_prf() -> None:
    truth = [True, True, False, False]
    predicted = [True, False, True, False]
    tp, fp, fn, tn = subject._binary_counts(truth, predicted)
    assert (tp, fp, fn, tn) == (1, 1, 1, 1)
    precision = subject._safe_div(tp, tp + fp)
    recall = subject._safe_div(tp, tp + fn)
    assert precision == 0.5
    assert recall == 0.5
    assert subject._f1(precision, recall) == 0.5


def test_calibration_probability_one_is_in_last_bin() -> None:
    bins, ece = subject._calibration_bins(
        [0.0, 0.1, 0.99, 1.0],
        [False, False, True, True],
    )
    assert len(bins) == 10
    assert bins[0].count == 1
    assert bins[1].count == 1
    assert bins[9].count == 2
    assert 0.0 <= ece <= 1.0


def test_multiclass_brier_is_zero_for_perfect_probability() -> None:
    probabilities = {"1": 0.0, "2": 0.0, "3": 1.0, "4": 0.0}
    assert subject._multiclass_brier(probabilities, 3) == 0.0


def test_threshold_grid_is_frozen_without_implicit_selection() -> None:
    assert len(subject.THRESHOLD_GRID) == 19
    assert subject.THRESHOLD_GRID[0] == 0.05
    assert subject.THRESHOLD_GRID[-1] == 0.95


def test_f1_is_undefined_when_precision_or_recall_is_undefined() -> None:
    assert subject._f1(None, 0.5) is None
    assert subject._f1(0.5, None) is None
