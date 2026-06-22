"""
Resistance Need Index (RNI)

Computes a composite 0-1 score for each (organism, drug, country) triplet
by combining six sub-indicators:

  1. resistance_prevalence  – % of isolates classified as R
  2. mic_drift              – linear trend in log2(MIC) over years (normalised)
  3. mdr_frequency          – % isolates resistant to ≥3 drug classes
  4. geographic_spread      – country breadth relative to global maximum
  5. therapeutic_scarcity   – inverse of active drug options (per pathogen)
  6. pediatric_involvement  – % resistant isolates from pediatric patients
"""

import pandas as pd
import numpy as np
from scipy import stats
import logging
from config import RNI_WEIGHTS, MIN_ISOLATE_COUNT, MIN_YEARS_FOR_DRIFT

logger = logging.getLogger(__name__)


class ResistanceNeedIndex:

    def __init__(self, weights: dict = None):
        self.weights = weights or RNI_WEIGHTS
        assert abs(sum(self.weights.values()) - 1.0) < 1e-6, \
            "RNI weights must sum to 1.0"

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parameters
        ----------
        df : harmonized DataFrame from DataHarmonizer.harmonize()

        Returns
        -------
        rni_df : DataFrame indexed by (organism, drug, country) with columns
                 for each sub-indicator, the weighted RNI score, and metadata.
        """
        logger.info("Computing Resistance Need Index …")

        prev   = self._resistance_prevalence(df)
        drift  = self._mic_drift(df)
        mdr    = self._mdr_frequency(df)
        spread = self._geographic_spread(df)
        scar   = self._therapeutic_scarcity(df)
        peds   = self._pediatric_involvement(df)

        components = [prev, drift, mdr, spread, scar, peds]
        rni = pd.concat([c.to_frame() if isinstance(c, pd.Series) else c
                         for c in components], axis=1, join="outer")

        # Fill missing sub-scores with 0 (no data = lowest need estimate)
        for col in ["resistance_prevalence", "mic_drift", "mdr_frequency",
                    "geographic_spread", "therapeutic_scarcity",
                    "pediatric_involvement"]:
            rni[col] = pd.to_numeric(rni[col], errors="coerce").fillna(0).clip(0, 1)

        # Weighted composite
        rni["RNI"] = sum(
            rni[col] * self.weights[col]
            for col in self.weights
        )

        rni = rni.reset_index().sort_values("RNI", ascending=False)
        logger.info(f"RNI computed for {len(rni)} (organism, drug, country) combinations.")
        return rni

    # ------------------------------------------------------------------
    # Sub-indicators
    # ------------------------------------------------------------------

    def _resistance_prevalence(self, df: pd.DataFrame) -> pd.Series:
        """Proportion of resistant isolates per (organism, drug, country)."""
        grp = df.groupby(["organism", "drug", "country"])
        counts = grp["is_resistant"].agg(["sum", "count"])
        counts = counts[counts["count"] >= MIN_ISOLATE_COUNT]
        prev = (counts["sum"] / counts["count"]).rename("resistance_prevalence")
        return prev

    def _mic_drift(self, df: pd.DataFrame) -> pd.Series:
        """
        Linear slope of log2(MIC) over years per (organism, drug, country).
        Positive slope = MIC increasing = worsening resistance.
        Normalised to [0, 1] across all combinations.
        """
        df = df.dropna(subset=["mic", "year"])
        df = df[df["mic"] > 0]
        df = df.copy()
        df["log2_mic"] = np.log2(df["mic"])

        records = {}
        for key, grp in df.groupby(["organism", "drug", "country"]):
            yearly = grp.groupby("year")["log2_mic"].median().reset_index()
            if len(yearly) < MIN_YEARS_FOR_DRIFT:
                continue
            slope, _, _, p, _ = stats.linregress(yearly["year"], yearly["log2_mic"])
            # Only count statistically significant positive drift
            records[key] = slope if (slope > 0 and p < 0.1) else 0.0

        drift = pd.Series(records, name="mic_drift")
        drift.index = pd.MultiIndex.from_tuples(drift.index,
                                                names=["organism", "drug", "country"])
        # Normalise to [0, 1]
        if drift.max() > 0:
            drift = drift / drift.max()
        return drift

    def _mdr_frequency(self, df: pd.DataFrame) -> pd.Series:
        """
        Proportion of isolates resistant to ≥3 drug classes per isolate per
        (organism, country) — then averaged per (organism, drug, country).

        Requires 'drug_class' column. If absent, returns empty Series.
        """
        if "drug_class" not in df.columns or df["drug_class"].isna().all():
            return pd.Series(name="mdr_frequency", dtype=float)

        # Count resistant drug classes per isolate proxy:
        # group by organism + country + year + age_group as proxy for an isolate
        proxy_cols = ["organism", "country", "year", "age_group", "specimen"]
        proxy_cols = [c for c in proxy_cols if c in df.columns]

        resist_classes = (
            df[df["is_resistant"]]
            .groupby(proxy_cols)["drug_class"]
            .nunique()
            .reset_index(name="n_resist_classes")
        )
        resist_classes["is_mdr"] = resist_classes["n_resist_classes"] >= 3

        # Merge back to full dataset to get (organism, drug, country) level
        merged = df.merge(
            resist_classes[proxy_cols + ["is_mdr"]],
            on=proxy_cols, how="left"
        )
        merged["is_mdr"] = merged["is_mdr"].fillna(False)

        grp = merged.groupby(["organism", "drug", "country"])
        counts = grp["is_mdr"].agg(["sum", "count"])
        counts = counts[counts["count"] >= MIN_ISOLATE_COUNT]
        mdr = (counts["sum"] / counts["count"]).rename("mdr_frequency")
        return mdr

    def _geographic_spread(self, df: pd.DataFrame) -> pd.Series:
        """
        For each (organism, drug): number of countries with resistance > 20%,
        normalised by the maximum across all combinations.
        Broadcast to (organism, drug, country) level.
        """
        grp = df.groupby(["organism", "drug", "country"])
        counts = grp["is_resistant"].agg(["sum", "count"])
        counts = counts[counts["count"] >= MIN_ISOLATE_COUNT]
        prev = counts["sum"] / counts["count"]
        resistant_countries = (prev > 0.2).groupby(
            level=["organism", "drug"]).sum().rename("n_resist_countries")

        max_val = resistant_countries.max()
        if max_val == 0:
            return pd.Series(name="geographic_spread", dtype=float)
        spread_norm = resistant_countries / max_val

        # Broadcast to (organism, drug, country) level
        spread_idx = counts.index  # (organism, drug, country)
        spread = spread_norm.reindex(spread_idx.droplevel("country"))
        spread.index = spread_idx
        spread.name = "geographic_spread"
        return spread

    def _therapeutic_scarcity(self, df: pd.DataFrame) -> pd.Series:
        """
        For each (organism, country): number of drugs with susceptibility > 50%
        (= still useful). Scarcity = 1 - (useful_drugs / total_tested_drugs).
        """
        grp = df.groupby(["organism", "drug", "country"])
        counts = grp["is_resistant"].agg(["sum", "count"])
        counts = counts[counts["count"] >= MIN_ISOLATE_COUNT]
        prev = counts["sum"] / counts["count"]

        # Drug is "active" if resistance prevalence < 0.5
        active = (prev < 0.5)
        n_active = active.groupby(level=["organism", "country"]).sum()
        n_total  = active.groupby(level=["organism", "country"]).count()
        scarcity = 1 - (n_active / n_total.clip(lower=1))

        # Broadcast to (organism, drug, country)
        scarcity_broadcast = scarcity.reindex(
            counts.index.droplevel("drug"))
        scarcity_broadcast.index = counts.index
        scarcity_broadcast.name = "therapeutic_scarcity"
        return scarcity_broadcast.clip(0, 1)

    def _pediatric_involvement(self, df: pd.DataFrame) -> pd.Series:
        """
        Proportion of resistant isolates that come from pediatric patients,
        per (organism, drug, country).
        """
        if "is_pediatric" not in df.columns:
            return pd.Series(name="pediatric_involvement", dtype=float)

        resist = df[df["is_resistant"]]
        grp = resist.groupby(["organism", "drug", "country"])
        counts = grp["is_pediatric"].agg(["sum", "count"])
        counts = counts[counts["count"] >= MIN_ISOLATE_COUNT]
        ped_pct = (counts["sum"] / counts["count"]).rename("pediatric_involvement")
        return ped_pct
