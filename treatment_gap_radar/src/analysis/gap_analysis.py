"""
Gap Analysis: compares RNI vs RDAI to identify treatment gaps.

Quadrant classification:
  I   (High RNI, High RDAI) → Well-addressed
  II  (Low RNI,  High RDAI) → Over-invested
  III (Low RNI,  Low RDAI)  → Low priority (correctly de-emphasised)
  IV  (High RNI, Low RDAI)  → CRITICAL GAP ← primary targets

Gap Score = RNI - RDAI  (higher = larger unmet need)
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class GapAnalysis:

    def __init__(self, rni_threshold: float = 0.5, rdai_threshold: float = 0.5):
        self.rni_threshold  = rni_threshold
        self.rdai_threshold = rdai_threshold

    # ------------------------------------------------------------------

    def merge(self, rni_df: pd.DataFrame, rdai_df: pd.DataFrame,
              auto_threshold: bool = True) -> pd.DataFrame:
        """
        Merge RNI (organism, drug, country) with RDAI (organism, drug) and
        compute gap metrics.
        """
        # Aggregate RNI to (organism, drug) level for matching with RDAI
        rni_agg = (
            rni_df.groupby(["organism", "drug"])
            .agg(
                RNI=("RNI", "mean"),
                resistance_prevalence=("resistance_prevalence", "mean"),
                mic_drift=("mic_drift", "mean"),
                mdr_frequency=("mdr_frequency", "mean"),
                geographic_spread=("geographic_spread", "mean"),
                therapeutic_scarcity=("therapeutic_scarcity", "mean"),
                pediatric_involvement=("pediatric_involvement", "mean"),
                n_countries=("country", "count"),
            )
            .reset_index()
        )

        merged = rni_agg.merge(rdai_df, on=["organism", "drug"], how="outer")
        merged["RNI"]  = merged["RNI"].fillna(0)
        merged["RDAI"] = merged["RDAI"].fillna(0)

        merged["gap_score"] = (merged["RNI"] - merged["RDAI"]).astype(float)

        # Use data-adaptive thresholds so critical gaps are meaningful
        # regardless of data scale. RNI: top 40% = high need.
        # RDAI: use median of non-zero values to separate funded vs. neglected.
        rni_th  = self.rni_threshold
        rdai_th = self.rdai_threshold
        if auto_threshold:
            rni_th  = float(merged["RNI"].quantile(0.60))
            nonzero_rdai = merged.loc[merged["RDAI"] > 0, "RDAI"]
            rdai_th = float(nonzero_rdai.median()) if len(nonzero_rdai) > 0 else 0.3
            logger.info(f"Adaptive thresholds — RNI: {rni_th:.3f}, RDAI: {rdai_th:.3f}")

        merged["quadrant"] = merged.apply(
            lambda r: self._classify_thresh(r, rni_th, rdai_th), axis=1
        )
        merged = merged.sort_values("gap_score", ascending=False).reset_index(drop=True)
        merged["rank"] = merged.index + 1

        logger.info(f"Gap analysis: {len(merged)} combinations. "
                    f"Critical gaps: {(merged['quadrant'] == 'IV_Critical_Gap').sum()}")
        return merged

    def critical_gaps(self, gap_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
        """Return the top-N critical gap combinations (Quadrant IV)."""
        return (
            gap_df[gap_df["quadrant"] == "IV_Critical_Gap"]
            .head(top_n)
            .reset_index(drop=True)
        )

    def country_gaps(self, rni_df: pd.DataFrame, rdai_df: pd.DataFrame,
                     top_n: int = 15) -> pd.DataFrame:
        """Country-level gap: mean RNI per country across all combinations."""
        country_rni = (
            rni_df.groupby("country")
            .agg(
                mean_RNI=("RNI", "mean"),
                n_combinations=("RNI", "count"),
                max_RNI=("RNI", "max"),
                region=("region", "first") if "region" in rni_df.columns else ("country", "first"),
            )
            .reset_index()
            .sort_values("mean_RNI", ascending=False)
        )
        return country_rni.head(top_n)

    def pathogen_summary(self, gap_df: pd.DataFrame) -> pd.DataFrame:
        """Summarise gap scores by pathogen."""
        return (
            gap_df.groupby("organism")
            .agg(
                mean_RNI=("RNI", "mean"),
                mean_RDAI=("RDAI", "mean"),
                mean_gap=("gap_score", "mean"),
                critical_drug_count=("quadrant",
                                     lambda x: (x == "IV_Critical_Gap").sum()),
                n_drugs=("drug", "count"),
            )
            .reset_index()
            .sort_values("mean_gap", ascending=False)
        )

    # ------------------------------------------------------------------

    def _classify(self, row: pd.Series) -> str:
        return self._classify_thresh(row, self.rni_threshold, self.rdai_threshold)

    def _classify_thresh(self, row: pd.Series, rni_th: float, rdai_th: float) -> str:
        hi_rni  = row["RNI"]  >= rni_th
        hi_rdai = row["RDAI"] >= rdai_th
        if hi_rni and hi_rdai:
            return "I_Well_Addressed"
        if not hi_rni and hi_rdai:
            return "II_Over_Invested"
        if not hi_rni and not hi_rdai:
            return "III_Low_Priority"
        return "IV_Critical_Gap"
