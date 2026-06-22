"""Unit tests for GapAnalysis."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest

from src.data_ingestion.loaders import _base_synthetic
from src.data_ingestion.harmonizer import DataHarmonizer
from src.indices import ResistanceNeedIndex, RDAttentionIndex
from src.analysis import GapAnalysis


@pytest.fixture(scope="module")
def gap_result():
    raw = _base_synthetic("test", n=2000)
    harmonized = DataHarmonizer().harmonize(raw)
    rni_df = ResistanceNeedIndex().compute(harmonized)
    rdai_df = RDAttentionIndex().compute()
    return GapAnalysis().merge(rni_df, rdai_df), rni_df, rdai_df


def test_gap_quadrants(gap_result):
    gap_df, _, _ = gap_result
    valid = {"I_Well_Addressed", "II_Over_Invested", "III_Low_Priority", "IV_Critical_Gap"}
    assert set(gap_df["quadrant"].unique()).issubset(valid)


def test_gap_score_range(gap_result):
    gap_df, _, _ = gap_result
    assert gap_df["gap_score"].between(-1, 1).all()


def test_critical_gaps_subset(gap_result):
    gap_df, _, _ = gap_result
    ga = GapAnalysis()
    crits = ga.critical_gaps(gap_df, top_n=10)
    assert all(crits["quadrant"] == "IV_Critical_Gap")
    assert len(crits) <= 10


def test_pathogen_summary(gap_result):
    gap_df, _, _ = gap_result
    summary = GapAnalysis().pathogen_summary(gap_df)
    assert "mean_gap" in summary.columns
    assert len(summary) > 0


def test_country_gaps(gap_result):
    gap_df, rni_df, rdai_df = gap_result
    country = GapAnalysis().country_gaps(rni_df, rdai_df)
    assert "mean_RNI" in country.columns
    assert len(country) > 0
