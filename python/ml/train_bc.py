import sys
from pathlib import Path
import json
import pandas as pd
import torch
import joblib
from sklearn.preprocessing import StandardScaler

class BCModel(torch.nn.Module):
    def __init__(self):
        super().__init__()

        self.layer1 = torch.nn.Linear(4, 64)
        self.layer2 = torch.nn.Linear(64, 64)
        self.layer3 = torch.nn.Linear(64, 1)

    def forward(self, x):
        x = self.layer1(x)

        x = torch.relu(x)

        x = self.layer2(x)

        x = torch.relu(x)

        x = self.layer3(x)

        return x

if __name__ == "__main__":
    # Map target path to relative directory
    data_dir = Path("data")

    if not data_dir.exists() or not data_dir.is_dir():
        print("Error: The 'data' directory does not exist.\n")
        sys.exit(1)

    print("=== DIVESYNC HEAVY - BEHAVIOR CLONING BASELINE TRAINING INTERFACE ===\n")

    print("Available experiments (Manual Control & Contains Training Data):\n")

    # Gather all subdirectories
    all_folders = sorted([f for f in data_dir.iterdir() if f.is_dir()])
    folder_list = []
    folder_notes = {}

    # Filter folders based on your exact conditions
    for folder in all_folders:
        training_data_path = folder / "training_data.csv"
        metadata_path = folder / "metadata.json"

        # Condition 1: Must contain training_data.csv
        if not training_data_path.exists():
            continue

        # Condition 2: Must have control-mode == "manual" inside metadata.json
        if not metadata_path.exists():
            continue

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            # Check the control mode filter
            if metadata.get("control-mode") == "pid":
                folder_str = str(folder)
                folder_list.append(folder_str)
                # Store notes for display later
                folder_notes[folder_str] = metadata.get("notes", "")
        except (json.JSONDecodeError, OSError):
            # Skip folders with corrupt or unreadable metadata
            continue

    # Display filtered choices in terminal
    for idx, folder in enumerate(folder_list):
        notes = folder_notes.get(folder, "")
        if notes:
            print(f"[{idx}] {Path(folder).name} - {notes}")
        else:
            print(f"[{idx}] {Path(folder).name}")
    print()

    selected_folder_paths = []

    while True:
        try:
            if len(folder_list) == 0:
                print("No valid manual training folders available. Exiting.\n")
                sys.exit(0)
                
            user_input = input("Select folders (e.g., 0,1,4 or 'all'): ").strip()
            
            # Allow shorthand to select everything easily
            if user_input.lower() == "all":
                selected_indices = list(range(len(folder_list)))
            else:
                # Parse comma-separated inputs
                selected_indices = [int(x.strip()) for x in user_input.split(",")]
            
            # Validate all indices are within bounds
            invalid_indices = [idx for idx in selected_indices if idx < 0 or idx >= len(folder_list)]
            if invalid_indices:
                print(f"Error: Indices {invalid_indices} are out of range. Use 0 to {len(folder_list) - 1}.\n")
                continue
                
            selected_folder_paths = [folder_list[idx] for idx in selected_indices]
            print(f"\nSelected {len(selected_folder_paths)} folders. Processing and combining data...\n")
            break
            
        except ValueError:
            print("Error: Please enter numbers separated by commas (e.g., 0,1,4)\n")

    # Load and combine data from all selected experiments
    df_list = []
    for path in selected_folder_paths:
        csv_path = Path(path) / "training_data.csv"
        individual_df = pd.read_csv(csv_path)
        df_list.append(individual_df)
        
    # Merge them vertically into one single DataFrame
    data = pd.concat(df_list, ignore_index=True)

    # Split into X and y
    X = data[[
        "depth_m",
        "depth_setpoint_m",
        "depth_error_m",
        "velocity_mps",
    ]]

    y = data[[
        "actuator_setpoint_mm"
    ]]

    # Convert to tensors
    X_scaler = StandardScaler()
    y_scaler = StandardScaler()

    X_scaled = X_scaler.fit_transform(X)
    y_scaled = y_scaler.fit_transform(y)

    X = torch.tensor(X_scaled, dtype=torch.float32)
    y = torch.tensor(y_scaled, dtype=torch.float32)    

    model = BCModel()
    loss_fn = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    epochs = 15000

    for epoch in range(epochs):
        predictions = model(X)
        loss = loss_fn(predictions, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 100 == 0:
            print(f"Epoch {epoch}, Loss: {loss.item()}")

    joblib.dump(X_scaler, "python/ml/x_scaler.pkl")
    joblib.dump(y_scaler, "python/ml/y_scaler.pkl")
    torch.save(model.state_dict(), "python/ml/bc_model_weights.pt")
