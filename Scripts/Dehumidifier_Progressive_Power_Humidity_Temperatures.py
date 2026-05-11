from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


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


def plot_progressive_graph(
    ax: plt.Axes,
    title: str,
    power_hourly: pd.DataFrame,
    humidity_df: pd.DataFrame | None = None,
    temp_df: pd.DataFrame | None = None,
    outside_temp_df: pd.DataFrame | None = None,
) -> None:
    axes = [ax]

    ax.bar(
        power_hourly["last_changed"],
        power_hourly["power_w"],
        width=0.03,
        color="tab:blue",
        alpha=0.65,
        label="Hourly Power Avg",
    )
    ax.set_title(title)
    ax.set_ylabel("Power (W)", color="tab:blue")
    ax.tick_params(axis="y", labelcolor="tab:blue")
    ax.grid(True, alpha=0.3)

    if humidity_df is not None:
        humidity_ax = ax.twinx()
        axes.append(humidity_ax)
        humidity_ax.plot(
            humidity_df["last_changed"],
            humidity_df["humidity_pct"],
            color="tab:green",
            linewidth=1.8,
            label="Humidity",
        )
        humidity_ax.set_ylabel("Humidity (%)", color="tab:green")
        humidity_ax.tick_params(axis="y", labelcolor="tab:green")

    if temp_df is not None or outside_temp_df is not None:
        temp_ax = ax.twinx()
        axes.append(temp_ax)
        if humidity_df is not None:
            temp_ax.spines["right"].set_position(("outward", 50))
        if temp_df is not None:
            temp_ax.plot(
                temp_df["last_changed"],
                temp_df["temp_c"],
                color="tab:orange",
                linewidth=1.8,
                label="Indoor Temperature",
            )
        if outside_temp_df is not None:
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

    for path in (power_csv, humidity_csv, temp_csv, outside_temp_csv):
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

    power_df = load_series(power_csv, "power_w")
    humidity_df = load_series(humidity_csv, "humidity_pct")
    temp_df = load_series(temp_csv, "temp_c")
    outside_temp_df = load_series(outside_temp_csv, "outside_temp_c")

    power_hourly = (
        power_df.set_index("last_changed")
        .resample("1h")
        .mean()
        .dropna()
        .reset_index()
    )

    fig, axes = plt.subplots(2, 2, figsize=(18, 10), constrained_layout=True)
    flat_axes = axes.flatten()

    plot_progressive_graph(flat_axes[0], "1. Dehumidifier Power", power_hourly)
    plot_progressive_graph(
        flat_axes[1],
        "2. Power + Humidity",
        power_hourly,
        humidity_df=humidity_df,
    )
    plot_progressive_graph(
        flat_axes[2],
        "3. Power + Humidity + Indoor Temperature",
        power_hourly,
        humidity_df=humidity_df,
        temp_df=temp_df,
    )
    plot_progressive_graph(
        flat_axes[3],
        "4. Power + Humidity + Indoor and Outside Temperature",
        power_hourly,
        humidity_df=humidity_df,
        temp_df=temp_df,
        outside_temp_df=outside_temp_df,
    )

    fig.suptitle(
        "Dehumidifier data shown progressively: power, humidity, indoor temp, outside temp",
        fontsize=16,
    )

    output_file = output_folder / "dehumidifier_progressive_power_humidity_temperatures.png"
    fig.savefig(output_file, dpi=300)
    plt.close(fig)

    print(f"Saved plot: {output_file}")


if __name__ == "__main__":
    main()
