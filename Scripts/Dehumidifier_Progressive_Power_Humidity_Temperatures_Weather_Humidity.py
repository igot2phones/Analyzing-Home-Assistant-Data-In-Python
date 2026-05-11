from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


# 55 points leaves a clear gap between humidity and temperature labels on the figure.
TEMPERATURE_AXIS_OFFSET = 55


def find_csv_folder(script_dir: Path) -> Path:
    candidates = [
        script_dir / "data_in_csv",
        script_dir / "datata_in_csv",
        script_dir.parent / "data_in_csv",
        script_dir.parent / "datata_in_csv",
    ]
    for folder in candidates:
        if folder.exists() and folder.is_dir():
            return folder
    return script_dir.parent / "datata_in_csv"


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


def format_x_axis(ax: plt.Axes) -> None:
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    ax.tick_params(axis="x", rotation=25)


def combine_legends(axes: list[plt.Axes]) -> tuple[list, list]:
    handles = []
    labels = []
    for axis in axes:
        axis_handles, axis_labels = axis.get_legend_handles_labels()
        handles.extend(axis_handles)
        labels.extend(axis_labels)
    return handles, labels


def plot_all_data_graph(
    ax: plt.Axes,
    power_hourly: pd.DataFrame,
    humidity_df: pd.DataFrame,
    temp_df: pd.DataFrame,
    outside_temp_df: pd.DataFrame,
    weather_humidity_df: pd.DataFrame,
) -> None:
    required_plot_data = {
        "power_hourly": (power_hourly, {"last_changed", "power_w"}),
        "humidity_df": (humidity_df, {"last_changed", "humidity_pct"}),
        "temp_df": (temp_df, {"last_changed", "temp_c"}),
        "outside_temp_df": (outside_temp_df, {"last_changed", "outside_temp_c"}),
        "weather_humidity_df": (
            weather_humidity_df,
            {"last_changed", "weather_humidity_pct"},
        ),
    }
    for parameter_name, (df, required_columns) in required_plot_data.items():
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{parameter_name} must be a pandas DataFrame.")
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"{parameter_name} missing columns: {missing_columns}")

    axes = [ax]

    ax.bar(
        power_hourly["last_changed"],
        power_hourly["power_w"],
        width=0.03,
        color="tab:blue",
        alpha=0.65,
        label="Hourly Power Avg",
    )
    ax.set_title(
        "Dehumidifier Power, Indoor Conditions, Outside Temperature, "
        "and Weather Station Humidity"
    )
    ax.set_ylabel("Power (W)", color="tab:blue")
    ax.tick_params(axis="y", labelcolor="tab:blue")
    ax.grid(True, alpha=0.3)

    humidity_ax = ax.twinx()
    axes.append(humidity_ax)
    humidity_ax.plot(
        humidity_df["last_changed"],
        humidity_df["humidity_pct"],
        color="tab:green",
        linewidth=1.8,
        label="Indoor Humidity",
    )
    humidity_ax.plot(
        weather_humidity_df["last_changed"],
        weather_humidity_df["weather_humidity_pct"],
        color="tab:purple",
        linewidth=1.8,
        linestyle=":",
        label="Weather Station Humidity",
    )
    humidity_ax.set_ylabel("Humidity (%)", color="tab:green")
    humidity_ax.tick_params(axis="y", labelcolor="tab:green")

    temp_ax = ax.twinx()
    axes.append(temp_ax)
    temp_ax.spines["right"].set_position(("outward", TEMPERATURE_AXIS_OFFSET))
    temp_ax.plot(
        temp_df["last_changed"],
        temp_df["temp_c"],
        color="tab:orange",
        linewidth=1.8,
        label="Indoor Temperature",
    )
    temp_ax.plot(
        outside_temp_df["last_changed"],
        outside_temp_df["outside_temp_c"],
        color="tab:red",
        linewidth=1.8,
        linestyle="--",
        label="Outside Temperature",
    )
    temp_ax.set_ylabel("Temperature (°C)", color="tab:orange")
    temp_ax.tick_params(axis="y", labelcolor="tab:orange")

    handles, labels = combine_legends(axes)
    ax.legend(handles, labels, loc="upper left", fontsize=8)
    format_x_axis(ax)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    csv_folder = find_csv_folder(script_dir)
    output_folder = script_dir.parent / "plots"
    output_folder.mkdir(parents=True, exist_ok=True)

    power_csv = csv_folder / "history-Dehulidifier-plug.csv"
    humidity_csv = csv_folder / "Tapo_humidity_history.csv"
    temp_csv = csv_folder / "Tapo_temp_history.csv"
    outside_temp_csv = csv_folder / "history-outsidetemp.csv"
    weather_humidity_csv = csv_folder / "weather_station_humidity_history.csv"

    for path in (
        power_csv,
        humidity_csv,
        temp_csv,
        outside_temp_csv,
        weather_humidity_csv,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

    power_df = load_series(power_csv, "power_w")
    humidity_df = load_series(humidity_csv, "humidity_pct")
    temp_df = load_series(temp_csv, "temp_c")
    outside_temp_df = load_series(outside_temp_csv, "outside_temp_c")
    weather_humidity_df = load_series(weather_humidity_csv, "weather_humidity_pct")

    power_hourly = (
        power_df.set_index("last_changed")
        .resample("1h")
        .mean()
        .dropna()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(18, 9), constrained_layout=True)
    plot_all_data_graph(
        ax,
        power_hourly,
        humidity_df,
        temp_df,
        outside_temp_df,
        weather_humidity_df,
    )

    output_file = output_folder / "dehumidifier_all_data_with_weather_humidity.png"
    fig.savefig(output_file, dpi=300)
    plt.close(fig)

    print(f"Saved plot: {output_file}")


if __name__ == "__main__":
    main()
