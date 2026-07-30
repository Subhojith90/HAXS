from __future__ import annotations
import matplotlib.pyplot as plt

def apply_style() -> None:
    plt.rcParams.update({"font.size": 9, "axes.grid": True, "figure.dpi": 140, "savefig.bbox": "tight"})
