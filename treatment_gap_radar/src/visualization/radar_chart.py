"""
Treatment Gap Radar — spider/radar chart for a single pathogen showing
each RNI sub-indicator as a spoke.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
import logging
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class RadarChart:

    INDICATORS = [
        "resistance_prevalence",
        "mic_drift",
        "mdr_frequency",
        "geographic_spread",
        "therapeutic_scarcity",
        "pediatric_involvement",
    ]
    LABELS = [
        "Resistance\nPrevalence",
        "MIC Drift",
        "MDR\nFrequency",
        "Geographic\nSpread",
        "Therapeutic\nScarcity",
        "Pediatric\nInvolvement",
    ]

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------

    def plot_pathogen(self, rni_df, organism: str,
                      top_drugs: int = 5, save: bool = True):
        """
        Radar chart showing RNI sub-indicators for the top drugs
        against a single pathogen.
        """
        subset = rni_df[rni_df["organism"] == organism].copy()
        if subset.empty:
            logger.warning(f"No data for {organism}")
            return

        # Aggregate to drug level
        drug_profiles = (
            subset.groupby("drug")[self.INDICATORS]
            .mean()
            .reset_index()
            .sort_values("resistance_prevalence", ascending=False)
            .head(top_drugs)
        )

        n_spokes = len(self.INDICATORS)
        angles = np.linspace(0, 2 * np.pi, n_spokes, endpoint=False).tolist()
        angles += angles[:1]  # close the polygon

        fig, ax = plt.subplots(figsize=(8, 8),
                               subplot_kw=dict(polar=True))
        colors = plt.cm.tab10(np.linspace(0, 1, len(drug_profiles)))

        for (_, row), color in zip(drug_profiles.iterrows(), colors):
            values = [row[ind] for ind in self.INDICATORS]
            values += values[:1]
            ax.plot(angles, values, color=color, linewidth=2, label=row["drug"])
            ax.fill(angles, values, color=color, alpha=0.15)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(self.LABELS, size=10)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], size=8, color="grey")
        ax.grid(color="grey", linestyle="--", linewidth=0.5, alpha=0.7)

        ax.set_title(
            f"Treatment Gap Radar\n{organism}",
            size=14, fontweight="bold", pad=20
        )
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1),
                  fontsize=9, title="Drug", title_fontsize=10)

        plt.tight_layout()
        if save:
            safe_name = organism.replace(" ", "_").replace("/", "-")
            path = os.path.join(self.output_dir, f"radar_{safe_name}.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Saved radar chart: {path}")
        return fig

    def plot_all_pathogens(self, rni_df):
        """Generate radar charts for every organism in the dataset."""
        for organism in rni_df["organism"].unique():
            self.plot_pathogen(rni_df, organism)
