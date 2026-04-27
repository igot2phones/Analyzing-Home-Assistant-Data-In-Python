from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def find_csv_folder(script_dir: Path) -> Path:
    candidates = []
    for base_dir in (script_dir, *script_dir.parents):
        candidates.extend(
            [
                base_dir / "data_in_csv",
                base_dir / "datata_in_csv",
            ]
        )

    for folder in candidates:
        if folder.exists() and folder.is_dir():
            return folder

    searched_paths = "\n".join(str(folder) for folder in candidates)
    raise FileNotFoundError(
        "Could not find a CSV data folder. Checked:\n"
        f"{searched_paths}"
    )


def load_series(csv_path: Path, value_name: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    required_cols = {"state", "last_changed"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"{csv_path.name} missing required columns: {required_cols}")

    df["state"] = pd.to_numeric(df["state"], errors="coerce")
    df["last_changed"] = pd.to_datetime(df["last_changed"], errors="coerce", utc=True)

    df = df.dropna(subset=["state", "last_changed"]).sort_values("last_changed")
    if df.empty:
        raise ValueError(f"{csv_path.name} has no valid data.")

    return df.rename(columns={"state": value_name})[["last_changed", value_name]]


def load_ac_power_series(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    required_cols = {"state", "last_changed"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"{csv_path.name} missing required columns: {required_cols}")

    df["state"] = pd.to_numeric(df["state"], errors="coerce")
    df["last_changed"] = pd.to_datetime(df["last_changed"], errors="coerce", utc=True)

    df = df.dropna(subset=["state", "last_changed"]).sort_values("last_changed")
    if df.empty:
        raise ValueError(f"{csv_path.name} has no valid data.")

    # Calculate instantaneous power consumption
    # Energy is in kWh, so convert difference to W
    df["energy_diff_kwh"] = df["state"].diff()
    df["time_diff_hours"] = df["last_changed"].diff().dt.total_seconds() / 3600
    df["power_w"] = (df["energy_diff_kwh"] / df["time_diff_hours"]) * 1000  # Convert kWh to W
    df = df.dropna(subset=["power_w"])
    
    # Remove outliers (negative power or extremely high values due to meter resets)
    df = df[df["power_w"] >= 0]

    return df[["last_changed", "power_w"]]


def format_stats(series: pd.Series, label: str, unit: str = "") -> str:
    stats = series.agg(["min", "max", "mean"])
    return (
        f"{label}\n"
        f"Min: {stats['min']:.2f}{unit}\n"
        f"Max: {stats['max']:.2f}{unit}\n"
        f"Mean: {stats['mean']:.2f}{unit}"
    )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    csv_folder = find_csv_folder(script_dir)
    output_folder = script_dir.parent / "plots-layerd-with-avarage"
    output_folder.mkdir(parents=True, exist_ok=True)

    ac_csv = csv_folder / "history-Midea-living room-AC.csv"
    humidity_csv = csv_folder / "Tapo_humidity_history.csv"
    temp_csv = csv_folder / "Tapo_temp_history.csv"

    if not ac_csv.exists():
        raise FileNotFoundError(f"Missing file: {ac_csv}")
    if not humidity_csv.exists():
        raise FileNotFoundError(f"Missing file: {humidity_csv}")
    if not temp_csv.exists():
        raise FileNotFoundError(f"Missing file: {temp_csv}")

    ac_df = load_ac_power_series(ac_csv)
    humidity_df = load_series(humidity_csv, "humidity_pct")
    temp_df = load_series(temp_csv, "temp_c")

    ac_hourly = (
        ac_df.set_index("last_changed")
        .resample("1h")
        .mean()
        .dropna()
        .reset_index()
    )

    ac_stats_text = format_stats(ac_hourly["power_w"], "AC Power hourly avg", " W")
    humidity_stats_text = format_stats(humidity_df["humidity_pct"], "Humidity", " %")
    temp_stats_text = format_stats(temp_df["temp_c"], "Temperature", " °C")

    fig, ax1 = plt.subplots(figsize=(13, 6))

    ax1.bar(
        ac_hourly["last_changed"],
        ac_hourly["power_w"],
        width=0.03,
        color="tab:blue",
        alpha=0.65,
        label="Hourly AC Power Avg",
    )
    ax1.set_ylabel("Average Power per Hour (W)", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.set_xlabel("Time")
    ax1.grid(True, alpha=0.3)

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

    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 60))
    ax3.plot(
        temp_df["last_changed"],
        temp_df["temp_c"],
        color="tab:orange",
        linewidth=2.0,
        label="Temperature",
    )
    ax3.set_ylabel("Temperature (°C)", color="tab:orange")
    ax3.tick_params(axis="y", labelcolor="tab:orange")

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    plt.xticks(rotation=30)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    handles3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(handles1 + handles2 + handles3, labels1 + labels2 + labels3, loc="upper left")

    ax1.text(
        0.02, 0.98, ac_stats_text,
        transform=ax1.transAxes,
        fontsize=10,
        va="top",
        ha="left",
        color="tab:blue",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="tab:blue"),
    )

    ax2.text(
        0.98, 0.98, humidity_stats_text,
        transform=ax2.transAxes,
        fontsize=10,
        va="top",
        ha="right",
        color="tab:green",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="tab:green"),
    )

    ax3.text(
        0.98, 0.75, temp_stats_text,
        transform=ax3.transAxes,
        fontsize=10,
        va="top",
        ha="right",
        color="tab:orange",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="tab:orange"),
    )

    plt.title("Midea AC Hourly Average Power (bars), Humidity (green line) and Temperature (orange line)")
    plt.tight_layout()

    output_file = output_folder / "midea_ac_power_humidity_and_temperature.png"
    plt.savefig(output_file, dpi=300)
    plt.close()

    print(f"Saved plot: {output_file}")


if __name__ == "__main__":
    main()