from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


# Keep each power/variable pair readable when stacked vertically.
POWER_BAR_WIDTH_DAYS = 0.03


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


def plot_power_with_variable(
    ax: plt.Axes,
    power_hourly: pd.DataFrame,
    variable_df: pd.DataFrame,
    *,
    value_column: str,
    variable_label: str,
    variable_ylabel: str,
    variable_color: str,
    variable_linestyle: str = "-",
) -> None:
    if not isinstance(power_hourly, pd.DataFrame):
        raise TypeError("power_hourly must be a pandas DataFrame.")
    if not isinstance(variable_df, pd.DataFrame):
        raise TypeError("variable_df must be a pandas DataFrame.")

    power_missing_columns = {"last_changed", "power_w"} - set(power_hourly.columns)
    if power_missing_columns:
        raise ValueError(f"power_hourly missing columns: {power_missing_columns}")

    variable_missing_columns = {"last_changed", value_column} - set(variable_df.columns)
    if variable_missing_columns:
        raise ValueError(f"{variable_label} missing columns: {variable_missing_columns}")

    ax.bar(
        power_hourly["last_changed"],
        power_hourly["power_w"],
        width=POWER_BAR_WIDTH_DAYS,
        color="tab:blue",
        alpha=0.6,
        label="Hourly Power Avg",
    )
    ax.set_ylabel("Power (W)", color="tab:blue")
    ax.tick_params(axis="y", labelcolor="tab:blue")
    ax.grid(True, alpha=0.3)

    variable_ax = ax.twinx()
    variable_ax.plot(
        variable_df["last_changed"],
        variable_df[value_column],
        color=variable_color,
        linewidth=1.8,
        linestyle=variable_linestyle,
        label=variable_label,
    )
    variable_ax.set_ylabel(variable_ylabel, color=variable_color)
    variable_ax.tick_params(axis="y", labelcolor=variable_color)

    handles, labels = combine_legends([ax, variable_ax])
    ax.legend(handles, labels, loc="upper left", fontsize=8)
    ax.set_title(f"Dehumidifier Power and {variable_label}")


def plot_stacked_power_variable_graphs(
    axes: list[plt.Axes],
    power_hourly: pd.DataFrame,
    humidity_df: pd.DataFrame,
    temp_df: pd.DataFrame,
    outside_temp_df: pd.DataFrame,
    weather_humidity_df: pd.DataFrame,
) -> None:
    plot_configs = [
        {
            "variable_df": humidity_df,
            "value_column": "humidity_pct",
            "variable_label": "Indoor Humidity",
            "variable_ylabel": "Humidity (%)",
            "variable_color": "tab:green",
        },
        {
            "variable_df": weather_humidity_df,
            "value_column": "weather_humidity_pct",
            "variable_label": "Weather Station Humidity",
            "variable_ylabel": "Humidity (%)",
            "variable_color": "tab:purple",
            "variable_linestyle": ":",
        },
        {
            "variable_df": temp_df,
            "value_column": "temp_c",
            "variable_label": "Indoor Temperature",
            "variable_ylabel": "Temperature (°C)",
            "variable_color": "tab:orange",
        },
        {
            "variable_df": outside_temp_df,
            "value_column": "outside_temp_c",
            "variable_label": "Outside Temperature",
            "variable_ylabel": "Temperature (°C)",
            "variable_color": "tab:red",
            "variable_linestyle": "--",
        },
    ]

    if len(axes) != len(plot_configs):
        raise ValueError(f"Expected {len(plot_configs)} axes, got {len(axes)}.")

    for ax, config in zip(axes, plot_configs):
        plot_power_with_variable(ax, power_hourly, **config)

    format_x_axis(axes[-1])
    axes[-1].set_xlabel("Time")


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

    fig, axes = plt.subplots(
        nrows=4,
        ncols=1,
        figsize=(18, 16),
        sharex=True,
        constrained_layout=True,
    )
    plot_stacked_power_variable_graphs(
        list(axes),
        power_hourly,
        humidity_df,
        temp_df,
        outside_temp_df,
        weather_humidity_df,
    )

    output_file = output_folder / "dehumidifier_power_with_stacked_variables.png"
    fig.savefig(output_file, dpi=300)
    plt.close(fig)

    print(f"Saved plot: {output_file}")


if __name__ == "__main__":
    main()
