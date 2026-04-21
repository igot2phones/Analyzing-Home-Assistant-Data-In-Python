from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def find_csv_folder(script_dir: Path) -> Path:
    # Δοκιμάζει πιθανά ονόματα/τοποθεσίες φακέλου CSV.
    candidates = [
        script_dir / "data_in_csv",
        script_dir / "datata_in_csv",
        script_dir.parent / "data_in_csv",
        script_dir.parent / "datata_in_csv",
    ]
    for folder in candidates:
        if folder.exists() and folder.is_dir():
            return folder
    # Προεπιλογή για τη δομή του συγκεκριμένου project.
    return script_dir.parent / "datata_in_csv"


def load_series(csv_path: Path, value_name: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    required_cols = {"state", "last_changed"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"{csv_path.name} missing required columns: {required_cols}")

    # Μετατροπή τύπων: αριθμητικές τιμές και timestamps.
    df["state"] = pd.to_numeric(df["state"], errors="coerce")
    df["last_changed"] = pd.to_datetime(df["last_changed"], errors="coerce", utc=True)

    # Αφαίρεση άκυρων γραμμών και ταξινόμηση χρονικά.
    df = df.dropna(subset=["state", "last_changed"]).sort_values("last_changed")
    if df.empty:
        raise ValueError(f"{csv_path.name} has no valid data.")

    return df.rename(columns={"state": value_name})[["last_changed", value_name]]


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    csv_folder = find_csv_folder(script_dir)
    output_folder = script_dir.parent / "plots"
    output_folder.mkdir(parents=True, exist_ok=True)

    power_csv = csv_folder / "history-Dehulidifier-plug.csv"
    humidity_csv = csv_folder / "Tapo_humidity_history.csv"

    if not power_csv.exists():
        raise FileNotFoundError(f"Missing file: {power_csv}")
    if not humidity_csv.exists():
        raise FileNotFoundError(f"Missing file: {humidity_csv}")

    power_df = load_series(power_csv, "power_w")
    humidity_df = load_series(humidity_csv, "humidity_pct")

    # Ωριαίος μέσος όρος τιμών ισχύος.
    power_hourly = (
        power_df.set_index("last_changed")
        .resample("1h")
        .mean()
        .dropna()
        .reset_index()
    )

    fig, ax1 = plt.subplots(figsize=(13, 6))

    # Μπάρες για τον ωριαίο μέσο όρο ισχύος.
    # Το πλάτος σε ημερομηνίες είναι σε "ημέρες" (0.03 ≈ 43 λεπτά).
    ax1.bar(
        power_hourly["last_changed"],
        power_hourly["power_w"],
        width=0.03,
        color="tab:blue",
        alpha=0.65,
        label="Hourly Power Avg",
    )
    ax1.set_ylabel("Average Power per Hour (W)", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_xlabel("Time")
    ax1.grid(True, alpha=0.3)

    # Γραμμή για την υγρασία σε δεύτερο άξονα y.
    ax2 = ax1.twinx()
    ax2.plot(
        humidity_df["last_changed"],
        humidity_df["humidity_pct"],
        color="tab:green",
        linewidth=2.0,
        label="Humidity",
    )
    ax2.set_ylabel("Humidity (%)", color="tab:green")
    ax2.tick_params(axis="y", labelcolor="tab:green")

    # Μορφοποίηση του άξονα χρόνου.
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    plt.xticks(rotation=30)

    # Ενιαίο υπόμνημα από τους δύο άξονες.
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left")

    plt.title("Dehumidifier Hourly Average Power (bars) and Humidity (line)")
    plt.tight_layout()

    output_file = output_folder / "dehumidifier_hourly_power_and_humidity.png"
    plt.savefig(output_file, dpi=300)
    plt.close()

    print(f"Saved plot: {output_file}")


if __name__ == "__main__":
    main()