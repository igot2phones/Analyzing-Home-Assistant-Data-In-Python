import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

csv_folder = "csv_files"
output_folder = "plots"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

csv_files = [f for f in os.listdir(csv_folder) if f.endswith(".csv")]

if len(csv_files) == 0:
    print("Δεν βρέθηκαν CSV αρχεία.")
else:
    for file_name in csv_files:
        file_path = os.path.join(csv_folder, file_name)

        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.strip()

            required_columns = ["entity_id", "state", "last_changed"]
            if not all(col in df.columns for col in required_columns):
                print(f"Το αρχείο {file_name} δεν έχει τις σωστές στήλες.")
                continue

            df["last_changed"] = pd.to_datetime(df["last_changed"], errors="coerce")
            df["state"] = pd.to_numeric(df["state"], errors="coerce")

            df = df.dropna(subset=["last_changed", "state"])
            df = df.sort_values("last_changed")

            if df.empty:
                print(f"Το αρχείο {file_name} δεν έχει έγκυρα δεδομένα.")
                continue

            time_data = np.array(df["last_changed"])
            power_data = np.array(df["state"])

            max_idx = df["state"].idxmax()
            min_idx = df["state"].idxmin()

            max_time = df.loc[max_idx, "last_changed"]
            max_value = df.loc[max_idx, "state"]

            min_time = df.loc[min_idx, "last_changed"]
            min_value = df.loc[min_idx, "state"]

            mean_value = df["state"].mean()

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(time_data, power_data, color="blue")

            ax.scatter(max_time, max_value, color="red", zorder=5)
            ax.scatter(min_time, min_value, color="green", zorder=5)

            ax.annotate(
                f"Max: {max_value:.2f}",
                xy=(max_time, max_value),
                xytext=(10, 10),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="red"),
                color="red"
            )

            ax.annotate(
                f"Min: {min_value:.2f}",
                xy=(min_time, min_value),
                xytext=(10, -15),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="green"),
                color="green"
            )

            ax.text(
                0.98, 0.02,
                f"Μέσος όρος: {mean_value:.2f}",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=10,
                bbox=dict(facecolor="white", alpha=0.8, edgecolor="black")
            )

            ax.set_title(f"Consumption vs Time - {file_name}")
            ax.set_xlabel("last_changed")
            ax.set_ylabel("state")
            ax.grid(True)

            fig.autofmt_xdate()
            plt.tight_layout()

            output_file = os.path.join(output_folder, file_name.replace(".csv", ".png"))
            plt.savefig(output_file, dpi=300)
            plt.close()

            print(f"Αποθηκεύτηκε το γράφημα: {output_file}")

        except Exception as e:
            print(f"Σφάλμα στο αρχείο {file_name}: {e}")