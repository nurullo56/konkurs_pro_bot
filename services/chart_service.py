from __future__ import annotations

import io
from typing import List, Tuple
from aiogram.types import BufferedInputFile


def generate_registration_chart(growth_data: List[Tuple[str, int]]) -> BufferedInputFile:
    """
    growth_data: List of (date_string, count_of_users)
    Returns a BufferedInputFile containing PNG image.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dates = [row[0] for row in growth_data] if growth_data else ["Bugun"]
    counts = [row[1] for row in growth_data] if growth_data else [0]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ax.plot(dates, counts, marker="o", color="#2563EB", linewidth=2.5, markersize=6)
    ax.fill_between(dates, counts, color="#93C5FD", alpha=0.4)

    ax.set_title("A'zolar o'sish statistikasi (Kunlar bo'yicha)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Sana", fontsize=11, labelpad=10)
    ax.set_ylabel("Yangi a'zolar soni", fontsize=11, labelpad=10)

    ax.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return BufferedInputFile(buf.getvalue(), filename="statistics_chart.png")
