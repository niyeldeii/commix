"""
Resistance heatmap: countries × pathogens, coloured by mean RNI.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
import logging
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class ResistanceHeatmap:

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def plot_country_pathogen(self, rni_df: pd.DataFrame, save: bool = True):
        """Heatmap of mean RNI per country × pathogen."""
        pivot = (
            rni_df.groupby(["country", "organism"])["RNI"]
            .mean()
            .unstack(fill_value=0)
            .astype(float)
        )
        # Keep top-20 countries by max RNI for readability
        pivot = pivot.loc[pivot.max(axis=1).nlargest(min(20, len(pivot))).index]

        fig, ax = plt.subplots(
            figsize=(max(10, len(pivot.columns) * 1.5),
                     max(8, len(pivot) * 0.45))
        )
        sns.heatmap(
            pivot, ax=ax, cmap="YlOrRd",
            vmin=0, vmax=1,
            linewidths=0.4, linecolor="white",
            cbar_kws={"label": "Mean RNI", "shrink": 0.6},
            annot=len(pivot.columns) <= 10,
            fmt=".2f", annot_kws={"size": 8},
        )
        ax.set_title(
            "Resistance Need Index — Country × Pathogen",
            fontsize=13, fontweight="bold", pad=12
        )
        ax.set_xlabel("Pathogen", fontsize=11)
        ax.set_ylabel("Country", fontsize=11)
        plt.xticks(rotation=35, ha="right", fontsize=9)
        plt.yticks(fontsize=9)
        plt.tight_layout()

        if save:
            path = os.path.join(self.output_dir, "heatmap_country_pathogen.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Saved heatmap: {path}")
        return fig

    def plot_drug_pathogen(self, rni_df: pd.DataFrame, save: bool = True):
        """Heatmap of mean resistance prevalence per drug × pathogen."""
        pivot = (
            rni_df.groupby(["drug", "organism"])["resistance_prevalence"]
            .mean()
            .unstack(fill_value=0)
            .astype(float)
        )

        fig, ax = plt.subplots(
            figsize=(max(10, len(pivot.columns) * 1.5),
                     max(6, len(pivot) * 0.4))
        )
        sns.heatmap(
            pivot, ax=ax, cmap="RdYlGn_r",
            vmin=0, vmax=1,
            linewidths=0.4, linecolor="white",
            cbar_kws={"label": "Resistance Prevalence", "shrink": 0.6},
            annot=True, fmt=".2f", annot_kws={"size": 8},
        )
        ax.set_title(
            "Resistance Prevalence — Drug × Pathogen",
            fontsize=13, fontweight="bold", pad=12
        )
        ax.set_xlabel("Pathogen", fontsize=11)
        ax.set_ylabel("Drug", fontsize=11)
        plt.xticks(rotation=35, ha="right", fontsize=9)
        plt.yticks(fontsize=9)
        plt.tight_layout()

        if save:
            path = os.path.join(self.output_dir, "heatmap_drug_pathogen.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Saved heatmap: {path}")
        return fig
