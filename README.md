## Control Strategies

Three outer-loop control strategies were implemented and compared:

1. **PID** — classical outer-loop depth PID feeding actuator position setpoints to the inner PID. Cascaded/nested PID across both loops was tested and found unstable (~99% of trials); the current architecture uses a single outer PID plus a fixed inner actuator-position PID instead.
2. **Behavior Cloning (BC)** — a small feedforward network (4→64→64→1, ReLU) trained via supervised learning on manually-piloted dive data, using `StandardScaler`-normalized inputs/outputs. Achieved bounded but persistently oscillatory depth tracking; further diagnosis found this ceiling was partly caused by a tank-specific confound (a negatively buoyant tether providing an unmodeled restorative force near the tank floor in shallow-tank testing), which didn't generalize to deeper open-water testing.
3. **Reinforcement Learning (TD3)** — an off-policy, deterministic actor-critic algorithm (Twin Delayed DDPG), warm-started from the trained BC network's weights and fine-tuned online on real hardware. Chosen over SAC/PPO/DDPG because its deterministic actor maps directly onto the BC architecture for warm-starting, its replay buffer suits the limited real-hardware sample budget, and its twin critics counter the Q-value overestimation that made vanilla DDPG unreliable.

### TD3 Implementation Notes

- Built on `stable_baselines3` (Gymnasium 1.3.0 / SB3 2.9.0), with a shape-only `DiveSyncEnvSpec` env used purely to satisfy SB3's constructor — no vectorized-env training loop is used. `main.py`'s own 20Hz loop *is* the environment loop; each dive is treated as one training episode.
- `warmstart.py` converts BC's trained weights into an SB3 TD3 actor: the first two linear layers copy directly, and the final layer is analytically rescaled to account for SB3's `tanh`-squashed output (BC's output layer has no output activation).
- The reward function combines a depth-tracking error penalty, a velocity-damping penalty, and a smooth exponential barrier discouraging surfacing (and, in later iterations, an analogous barrier for the tank floor and an action-delta smoothness penalty).
- Both online (small periodic updates during a dive) and end-of-dive (`finalize()`, larger update) training were implemented; see **Known Issues** below regarding online training stability.

## Running an Experiment

```bash
python main.py
```

You'll be prompted for:
- **Control mode:** `manual` / `pid` / `rl` / `sysid`
- **Experiment duration** (seconds)
- **Notes** (optional, stored in `metadata.json`)
- **COM port** for the ESP32

Each run creates a timestamped folder under `data/` containing `raw.csv`, `processed.csv`, `state.csv`, `boot.txt`, and `metadata.json`. After the experiment ends, `training_data.csv` is generated (merging `state.csv` and `processed.csv`), and a results plot is shown automatically if `processed.csv` exists.

### Training the BC baseline

```bash
python -m ml.train_bc
```
Select one or more `manual`-mode experiment folders to train on. Produces `bc_model_weights.pt`, `x_scaler.pkl`, and `y_scaler.pkl`.

### Warm-starting TD3 from BC

```bash
python -m ml.warmstart
```
Run once before the first RL dive. Produces `td3_warmstart.zip`. Does not need to be re-run unless BC is retrained from scratch.

### Testing the RL controller without hardware

## Known Issues / Future Work

- **Online (mid-dive) training instability:** periodic training updates during a dive were found to occasionally collapse the policy into a degenerate constant-action output, likely due to the critic training on too little, too-correlated data early in a dive. Online training is currently disabled by default (`online_gradient_steps=0`); all TD3 updates happen in `finalize()`, once per dive.
- **Reward scale sensitivity:** TD3 training was found to be highly sensitive to reward term magnitudes — a ~40x increase in one reward weight relative to another was sufficient to destabilize training into bang-bang actuator behavior. Current weights are tuned empirically; a more principled reward-normalization approach is a natural next step.
- **Residual steady-state tracking error:** the current TD3 policy shows a repeatable damped-oscillation response to setpoint changes, converging to a small but consistent depth offset rather than exact tracking. Believed limited primarily by the small amount of real-dive training data available; a larger and more diverse replay buffer (more dives, more setpoint variety) is the most likely path to improvement.
- **Battery cutoff enforcement:** `BATTERY_CUTOFF_V` is defined in `main.py` but not currently checked against live telemetry during the control loop — worth adding before longer unattended dives.

## Results

Comparison plots (behavior cloning, cascaded/fixed/variable PID, fixed/variable-setpoint RL, system identification, step response) are in `/results` and `/results/divesync-heavy-v1-results`.
