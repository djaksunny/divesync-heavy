# Placeholder BC before full online RL

import torch
import joblib
import pandas as pd
from ml.train_bc import BCModel

class RLController:

    def __init__(self, stroke, model_path="python/ml/bc_model_weights.pt"):
        self.model = BCModel()
        self.model.load_state_dict(torch.load(model_path))

        self.model.eval()

        self._x_scaler = joblib.load("python/ml/x_scaler.pkl")
        self._y_scaler = joblib.load("python/ml/y_scaler.pkl")

        self._stroke = float(stroke)

    def get_command(self, state):
        raw_state = pd.DataFrame([{
            "depth_m": state.depth_m,
            "depth_setpoint_m": state.depth_setpoint_m,
            "depth_error_m": state.depth_error_m,
            "velocity_mps": state.velocity_mps,
        }])

        scaled_state = self._x_scaler.transform(raw_state)
        state_tensor = torch.tensor(scaled_state, dtype=torch.float32)

        with torch.no_grad():
            prediction = self.model(state_tensor)
            
            prediction_mm = self._y_scaler.inverse_transform(
                prediction.numpy()
            )

            prediction_mm = float(prediction_mm[0, 0])
            
            prediction_mm = max(0.0, min(self._stroke, prediction_mm))

            return prediction_mm
        
        print(
    state.depth_m,
    state.depth_setpoint_m,
    state.depth_error_m,
    prediction_mm
)
