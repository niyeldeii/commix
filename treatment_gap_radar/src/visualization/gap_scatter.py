"""
Gap scatter plot: RNI (y-axis) vs RDAI (x-axis) with quadrant shading.
Points in the top-left quadrant (IV) are the critical gaps.
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

QUADRANT_COLORS = {
    "I_Well_Addressed":  "#2ecc71",
    "II_Over_Invested":  "#3498db",
    "III_Low_Priority":  "#95a5a6",
    "IV_Critical_Gap":   "#e74c3c",
}
QUADRANT_LABELS = {
    "I_Well_Addressed":  "Well-addressed",
    "II_Over_Invested":  "Over-invested",
    "III_Low_Priority":  "Low priority",
    "IV_Critical_Gap":   "CRITICAL GAP",
}


class GapScatterPlot:

    def __init__(self, output_dir: str = None,
                 rni_thresh: float = 0.5, rdai_thresh: float = 0.5):
        self.output_dir   = output_dir or OUTPUT_DIR
        self.rni_thresh   = rni_thresh
        self.rdai_thresh  = rdai_thresh
        os.makedirs(self.output_dir, exist_ok=True)

    def plot(self, gap_df, label_top_n: int = 10, save: bool = True):
        fig, ax = plt.subplots(figsize=(12, 9))

        # Quadrant background shading
        ax.axhspan(self.rni_thresh, 1.05, xmin=0,
                   xmax=(self.rdai_thresh),
                   alpha=0.08, color="#e74c3c")    # IV red
        ax.axhspan(self.rni_thresh, 1.05,
                   xmin=self.rdai_thresh, xmax=1,
                   alpha=0.08, color="#2ecc71")    # I green
        ax.axhspan(0, self.rni_thresh, xmin=0,
                   xmax=self.rdai_thresh,
                   alpha=0.08, color="#95a5a6")    # III grey
        ax.axhspan(0, self.rni_thresh,
                   xmin=self.rdai_thresh, xmax=1,
                   alpha=0.08, color="#3498db")    # II blue

        # Threshold lines
        ax.axhline(self.rni_thresh, color="black", linestyle="--",
                   linewidth=1, alpha=0.5)
        ax.axvline(self.rdai_thresh, color="black", linestyle="--",
                   linewidth=1, alpha=0.5)

        # Scatter points
        for _, row in gap_df.iterrows():
            color = QUADRANT_COLORS.get(row.get("quadrant", ""), "#7f8c8d")
            size  = 80 + 120 * row["RNI"]
            ax.scatter(row["RDAI"], row["RNI"], c=color,
                       s=size, alpha=0.75, edgecolors="white", linewidths=0.5)

        # Label top-N gaps
        top = gap_df.nlargest(label_top_n, "gap_score")
        for _, row in top.iterrows():
            label = f"{row['organism'].split()[-1]}\n/{row['drug']}"
            ax.annotate(
                label,
                (row["RDAI"], row["RNI"]),
                textcoords="offset points", xytext=(6, 4),
                fontsize=7, color="#2c3e50",
                arrowprops=dict(arrowstyle="-", color="grey", lw=0.5),
            )

        # Quadrant annotations
        ax.text(0.02, 0.98, "IV: CRITICAL GAP",
                transform=ax.transAxes, fontsize=9, color="#c0392b",
                fontweight="bold", va="top")
        ax.text(0.75, 0.98, "I: Well-addressed",
                transform=ax.transAxes, fontsize=9, color="#27ae60",
                fontweight="bold", va="top")
        ax.text(0.02, 0.48, "III: Low priority",
                transform=ax.transAxes, fontsize=9, color="#7f8c8d")
        ax.text(0.75, 0.48, "II: Over-invested",
                transform=ax.transAxes, fontsize=9, color="#2980b9")

        # Legend
        patches = [
            mpatches.Patch(color=c, label=QUADRANT_LABELS[q], alpha=0.75)
            for q, c in QUADRANT_COLORS.items()
        ]
        ax.legend(handles=patches, loc="lower right", fontsize=9)

        ax.set_xlabel("R&D Attention Index (RDAI)", fontsize=12)
        ax.set_ylabel("Resistance Need Index (RNI)", fontsize=12)
        ax.set_title(
            "Treatment Gap Radar — RNI vs RDAI\n"
            "Pathogen × Drug Combinations",
            fontsize=14, fontweight="bold"
        )
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save:
            path = os.path.join(self.output_dir, "gap_scatter.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            logger.info(f"Saved gap scatter plot: {path}")
        return fig
