import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def find_csv_folder(script_dir: Path) -> Path:
    """Find the folder that contains input CSV files."""
    candidates = [
        script_dir / "datata_in_csv",  # existing folder in this workspace
        script_dir / "csv_files",
        script_dir.parent / "datata_in_csv",
        script_dir.parent / "csv_files",
    ]

    for folder in candidates:
        if folder.exists() and folder.is_dir():
            return folder

    # Default to expected workspace folder name.
    return script_dir.parent / "datata_in_csv"


def plot_csv(file_path: Path, output_folder: Path) -> None:
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    required_cols = {"state", "last_changed"}
    if not required_cols.issubset(df.columns):
        print(
            f"Το αρχείο {file_path.name} δεν έχει τις σωστές στήλες. "
            f"Βρέθηκαν: {list(df.columns)}"
        )
        return

    # Convert values to proper types and remove invalid rows.
    df["state"] = pd.to_numeric(df["state"], errors="coerce")
    df["last_changed"] = pd.to_datetime(df["last_changed"], errors="coerce", utc=True)
    df = df.dropna(subset=["state", "last_changed"]).sort_values("last_changed")

    # state is cumulative kWh
    df["delta_kwh"] = df["state"].diff()
    df["delta_h"] = df["last_changed"].diff().dt.total_seconds() / 3600.0

    # Instantaneous average power over each interval, in Watts
    df["power_w"] = (df["delta_kwh"] / df["delta_h"]) * 1000.0

    # Keep only valid forward intervals
    df = df[(df["delta_h"] > 0) & (df["delta_kwh"] >= 0)].copy()
    df = df.dropna(subset=["power_w"])

    if df.empty:
        print(f"Το αρχείο {file_path.name} δεν έχει έγκυρα στιγμιαία δεδομένα ισχύος.")
        return

    # Στατιστικά
    min_idx = df["power_w"].idxmin()
    max_idx = df["power_w"].idxmax()

    min_row = df.loc[min_idx]
    max_row = df.loc[max_idx]

    min_power = min_row["power_w"]
    max_power = max_row["power_w"]
    mean_power = df["power_w"].mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df["last_changed"], df["power_w"], color="blue", linewidth=1)

    # Σημεία min/max
    ax.scatter(min_row["last_changed"], min_power, color="orange", s=60, zorder=5)
    ax.scatter(max_row["last_changed"], max_power, color="red", s=60, zorder=5)

    # Annotation για min
    ax.annotate(
        f"Min\n{min_power:.2f} W",
        xy=(min_row["last_changed"], min_power),
        xytext=(15, -20),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        arrowprops=dict(arrowstyle="->", color="orange")
    )

    # Annotation για max
    ax.annotate(
        f"Max\n{max_power:.2f} W",
        xy=(max_row["last_changed"], max_power),
        xytext=(15, 15),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        arrowprops=dict(arrowstyle="->", color="red")
    )

    # Box κάτω δεξιά για mean
    stats_text = f"Mean: {mean_power:.2f} W"
    ax.text(
        0.98, 0.02,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        ha="right",
        va="bottom",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
    )

    ax.set_title(f"Instantaneous Power - {file_path.name}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Power [W]")
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=30)
    plt.tight_layout()

    output_file = output_folder / file_path.with_suffix(".png").name
    plt.savefig(output_file, dpi=300)
    plt.close()

    print(f"Αποθηκεύτηκε το γράφημα: {output_file}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    csv_folder = find_csv_folder(script_dir)
    output_folder = script_dir.parent / "plots"
    output_folder.mkdir(parents=True, exist_ok=True)

    if not csv_folder.exists():
        print(f"Δεν βρέθηκε φάκελος CSV: {csv_folder}")
        return

    csv_files = [
        f for f in sorted(csv_folder.glob("history-Midea-living room-AC*.csv"))
    ]

    if not csv_files:
        print(f"Δεν βρέθηκαν CSV αρχεία στο: {csv_folder}")
        return

    for csv_file in csv_files:
        try:
            plot_csv(csv_file, output_folder)
        except Exception as exc:
            print(f"Σφάλμα στο αρχείο {csv_file.name}: {exc}")


if __name__ == "__main__":
    main()