"""Unit tests for ResistanceNeedIndex."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
import pytest

from src.data_ingestion.loaders import _base_synthetic
from src.data_ingestion.harmonizer import DataHarmonizer
from src.indices.resistance_need_index import ResistanceNeedIndex


@pytest.fixture(scope="module")
def harmonized():
    raw = _base_synthetic("test", n=2000)
    return DataHarmonizer().harmonize(raw)


def test_rni_columns(harmonized):
    rni = ResistanceNeedIndex().compute(harmonized)
    expected_cols = {
        "organism", "drug", "country", "RNI",
        "resistance_prevalence", "mic_drift", "mdr_frequency",
        "geographic_spread", "therapeutic_scarcity", "pediatric_involvement",
    }
    assert expected_cols.issubset(set(rni.columns))


def test_rni_range(harmonized):
    rni = ResistanceNeedIndex().compute(harmonized)
    assert rni["RNI"].between(0, 1).all(), "RNI must be in [0, 1]"
    for col in ["resistance_prevalence", "mic_drift", "mdr_frequency",
                "geographic_spread", "therapeutic_scarcity", "pediatric_involvement"]:
        assert rni[col].between(0, 1).all(), f"{col} must be in [0, 1]"


def test_rni_not_empty(harmonized):
    rni = ResistanceNeedIndex().compute(harmonized)
    assert len(rni) > 0, "RNI DataFrame must not be empty"


def test_weight_sensitivity(harmonized):
    """Changing weights should change the RNI values."""
    default = ResistanceNeedIndex().compute(harmonized)
    custom = ResistanceNeedIndex(weights={
        "resistance_prevalence": 0.60,
        "mic_drift":             0.10,
        "mdr_frequency":         0.10,
        "geographic_spread":     0.10,
        "therapeutic_scarcity":  0.05,
        "pediatric_involvement": 0.05,
    }).compute(harmonized)
    # RNI values should differ when weights differ
    merged = default[["organism", "drug", "country", "RNI"]].merge(
        custom[["organism", "drug", "country", "RNI"]],
        on=["organism", "drug", "country"], suffixes=("_default", "_custom")
    )
    assert not np.allclose(merged["RNI_default"], merged["RNI_custom"])
