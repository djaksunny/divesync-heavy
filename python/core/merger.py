import json
import sys
import pandas as pd
from pathlib import Path


class Merger:
    def __init__(self, folder_path):
        self._folder_path = folder_path
        self._state_path = Path(folder_path) / "state.csv"
        self._processed_path = Path(folder_path) / "processed.csv"

    def merge(self):
        if not self._state_path.exists():
            raise FileNotFoundError(f"'state.csv' not found inside {self._folder_path}")
        if not self._processed_path.exists():
            raise FileNotFoundError(f"'processed.csv' not found inside {self._folder_path}")

        state = pd.read_csv(self._state_path)
        proc = pd.read_csv(self._processed_path)

        state.dropna(how="all", inplace=True)
        proc.dropna(how="all", inplace=True)

        # Only pull actuator/motor fields from processed -- state stays the
        # source of truth for depth/error/velocity (what a live policy sees).
        merged = state.merge(
            proc[["time_s", "actuator_setpoint_mm"]],
            on="time_s",
            how="inner"
        )

        out_path = Path(self._folder_path) / "training_data.csv"
        merged.to_csv(out_path, index=False)

        return merged, out_path


if __name__ == "__main__":
    # Map target path to relative directory
    data_dir = Path("data")

    if not data_dir.exists() or not data_dir.is_dir():
        print("Error: The 'data' directory does not exist.\n")
        sys.exit(1)

    print("=== DIVESYNC HEAVY - TRAINING DATA MERGE INTERFACE ===\n")

    print("Available experiments:\n")

    # Gather available folders
    folder_list = sorted([str(f) for f in data_dir.iterdir() if f.is_dir()])

    def get_notes(folder):
        metadata_path = Path(folder) / "metadata.json"
        if not metadata_path.exists():
            return ""
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            return metadata.get("notes", "")
        except (json.JSONDecodeError, OSError):
            return ""

    # Display available choices in terminal
    for idx, folder in enumerate(folder_list):
        notes = get_notes(folder)
        if notes:
            print(f"[{idx}] {Path(folder).name} - {notes}")
        else:
            print(f"[{idx}] {Path(folder).name}")
    print()

    selected_folder_path = None

    while True:
        try:
            if len(folder_list) == 0:
                print("No folders available. Exiting merger.\n")
                sys.exit(0)

            folder_index = int(input("Select a folder (index): ").strip())
            selected_folder_path = folder_list[folder_index]
            print(f"\nSelected folder path: {selected_folder_path}. Merging...\n")
            break

        except ValueError:
            print("Error: please enter a valid number\n")
        except IndexError:
            if len(folder_list) == 1:
                print("Error: enter 0")
            else:
                print(f"Error: enter a number between 0 and {len(folder_list) - 1}\n")

    # Merge execution
    try:
        merger = Merger(folder_path=selected_folder_path)
        merged_df, out_path = merger.merge()
        print(f"[MERGE COMPLETE] Wrote {len(merged_df)} rows to {out_path}")
    except FileNotFoundError as e:
        print(f"Error: {e}\n")
