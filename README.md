# DiveSync Heavy

An autonomous underwater depth-control vehicle built around an ESP32 and MS5837 depth sensor, using a linear actuator syringe mechanism (0–100mm stroke) for buoyancy-based depth control. This repo contains the firmware, hardware design files, and control software — including PID and reinforcement learning (TD3) controllers — developed as part of ongoing research under Umar.

## Hardware Overview

- **Depth sensing:** MS5837 pressure/depth sensor
- **Actuation:** Linear actuator-driven syringe mechanism, 0–100mm stroke, adjusts buoyancy by changing displaced volume
- **Compute:** ESP32, communicating over USB serial (115200 baud) with a host machine running the Python control stack
- **Control loop:** 20Hz telemetry/state/actuator loop, with an inner PID stabilizing actuator position and an outer controller (PID / BC / RL) setting the depth-tracking target

Full schematics, PCB layout, and BOM are under `/eda`.

## Repository Structure

```
divesync-heavy/
├── data/                     # Raw experiment logs, grouped by hardware/software version -- see "Experiment Data" below
├── eda/                      # KiCad schematic, PCB, BOM, and exported schematic PDF
├── firmware/                 # ESP32 firmware (PlatformIO project)
├── python/
│   ├── controllers/
│   │   ├── inner.py           # Inner PID loop — actuator position control
│   │   ├── manual.py          # Gamepad/keyboard manual control
│   │   ├── pid.py             # Outer PID depth controller
│   │   ├── rl.py              # TD3 (fully online) depth controller
│   │   └── waveform.py        # Square-wave setpoint/actuator generator
│   ├── core/
│   │   ├── experiment.py      # Experiment setup, handshake, state machine
│   │   ├── logger.py          # CSV logging (raw/processed/state)
│   │   ├── merger.py          # Merges state + processed CSVs into training_data.csv
│   │   ├── processor.py       # Depth filtering, actuator unit conversion
│   │   ├── serial_manager.py  # Serial I/O with the ESP32
│   │   ├── state.py           # Computes depth error, filtered velocity
│   │   └── telemetry.py       # Raw serial line parsing
│   ├── ml/
│   │   ├── reward.py              # TD3 reward function
│   │   ├── td3_env_spec.py        # Gym shape-declaration env for SB3 (also defines the fixed obs-normalization bounds)
│   │   ├── td3_model.zip          # Actively-training TD3 model (updated after each RL dive)
│   │   └── td3_replay_buffer.pkl  # Persisted replay buffer across dives
│   └── visualization/
│       ├── display.py         # Live Tkinter depth/setpoint/error display
│       └── plotter.py         # Post-dive matplotlib plotting (depth/actuator/motor voltage)
├── results/
│   ├── divesync-heavy-v1-results/   # Behavior cloning, cascaded PID, step response, sysid plots
│   ├── divesync-heavy-v2-results/   # Behavior cloning, cascaded PID (fixed/variable), RL (fixed/variable)
│   └── divesync-heavy-v3-results/   # Fully-online RL: early / failure / converged
├── main.py                    # Experiment entry point / main control loop
├── requirements.txt
├── .gitignore
└── README.md
```

## Control Strategies

Two outer-loop control strategies were implemented and compared:

1. **PID** — classical outer-loop depth PID feeding actuator position setpoints to the inner PID. Cascaded/nested PID across both loops was tested and found unstable (~99% of trials); the current architecture uses a single outer PID plus a fixed inner actuator-position PID instead.
2. **Reinforcement Learning (TD3)** — an off-policy, deterministic actor-critic algorithm (Twin Delayed DDPG), trained fully online on real hardware from a randomly-initialized actor and critics (no warm-start). Chosen over SAC/PPO/DDPG because its replay buffer suits the limited real-hardware sample budget, and its twin critics counter the Q-value overestimation that made vanilla DDPG unreliable.

### TD3 Implementation Notes

- Built on `stable_baselines3` (Gymnasium 1.3.0 / SB3 2.9.0), with a shape-only `DiveSyncEnvSpec` env used purely to satisfy SB3's constructor — no vectorized-env training loop is used. `main.py`'s own 20Hz loop *is* the environment loop; each dive is treated as one training episode.
- State inputs to the actor are normalized using the fixed bounds declared in `DiveSyncEnvSpec` (`OBS_LOW`/`OBS_HIGH`), not a data-fitted scaler.
- The reward function combines a depth-tracking error penalty, a velocity-damping penalty, and a smooth exponential barrier discouraging surfacing (and, in later iterations, an analogous barrier for the tank floor and an action-delta smoothness penalty).
- Both online (small periodic updates during a dive) and end-of-dive (`finalize()`, larger update) training were implemented; see **Known Issues** below regarding online training stability.
- Reward isn't logged during a dive. `python/reward_backfill.py` (gitignored, not part of the tracked pipeline) computes it after the fact from a run's `state.csv` (`depth_error_m`, `velocity_mps`) using the weights currently defined in `controllers/rl.py`, across every RL experiment under `data/` at once, writing a gitignored `reward.csv` / `reward_plot.png` per folder. Intent going forward is for `visualization/plotter.py` to compute this the same way but on the fly for a single experiment, rather than relying on a separate batch pass — not wired up yet.

## Running an Experiment

```bash
pip install -r requirements.txt
python main.py
```

You'll be prompted for:
- **Control mode:** `manual` / `pid` / `rl` / `sysid`
- **Experiment duration** (seconds)
- **Notes** (optional, stored in `metadata.json`)
- **COM port** for the ESP32

Each run creates a timestamped folder under `data/` containing `raw.csv`, `processed.csv`, `state.csv`, `boot.txt`, and `metadata.json`. After the experiment ends, `training_data.csv` is generated (merging `state.csv` and `processed.csv`), and a results plot is shown automatically if `processed.csv` exists.

The first `rl`-mode run initializes a fresh TD3 model (random actor + critics) since there is no warm-start; `python/ml/td3_model.zip` and `td3_replay_buffer.pkl` are created after `finalize()` and reused/extended on subsequent RL dives.

## Known Issues / Future Work

- **Online (mid-dive) training instability:** periodic training updates during a dive were found to occasionally collapse the policy into a degenerate constant-action output, likely due to the critic training on too little, too-correlated data early in a dive. Online training is currently disabled by default (`online_gradient_steps=0`); all TD3 updates happen in `finalize()`, once per dive. This was directly reproduced on the first fully-online (no warm-start) dive: the policy overshot to the tank floor, recovered, then froze at a near-constant near-minimum actuator output for the remaining ~9 minutes of a ~11-minute dive despite a large, persistent tracking error. `RLController` now has a `random_warmup_decisions` phase (default 50 decisions, ~50s) where actions are sampled randomly (still delta-clamped for hardware safety) instead of drawn from the untrained actor, so the critic sees diverse transitions before any training happens.
- **Reward scale sensitivity:** TD3 training was found to be highly sensitive to reward term magnitudes — a ~40x increase in one reward weight relative to another was sufficient to destabilize training into bang-bang actuator behavior. Current weights are tuned empirically; a more principled reward-normalization approach is a natural next step.
- **Residual steady-state tracking error:** the current TD3 policy shows a repeatable damped-oscillation response to setpoint changes, converging to a small but consistent depth offset rather than exact tracking. Believed limited primarily by the small amount of real-dive training data available; a larger and more diverse replay buffer (more dives, more setpoint variety) is the most likely path to improvement.

## Experiment Data

Raw experiment logs under `data/`, grouped to match the hardware/software progression documented in `/results`. Each leaf folder is one experiment run (`YYYYMMDD-HHMMSS`), containing `raw.csv`, `processed.csv`, `state.csv`, `boot.txt`, `metadata.json`, and (once merged) `training_data.csv`.

### `divesync-heavy-v1-data/` (2026-07-06 -- 2026-07-09, 14 dives)

Earliest hardware iteration (50mm actuator stroke). Manual piloting, initial PID characterization, step-response/system-ID runs, and the first behavior-cloning + BC-warmstarted-RL attempts. Corresponds to `results/divesync-heavy-v1-results/`.

### `divesync-heavy-v2-data/` (2026-07-10, 2026-07-14, 31 dives)

100mm actuator stroke. Manual piloting for BC training data, PID validation (fixed/variable setpoint), and BC-pretraining-warmstarted TD3 -- the warmstart approach later found to underperform and replaced in v3. Corresponds to `results/divesync-heavy-v2-results/`.

### `divesync-heavy-v3-data/` -- fully-online TD3, no BC warm-start

The BC/warmstart pipeline was removed; TD3 trains entirely online from real dives from here on. Corresponds to `results/divesync-heavy-v3-results/` (reinforcement-learning-early/failure/converged). Split into three subfolders:

- **`pid-validation/`** (2026-07-16, 11 dives) -- pure PID control-mode dives, re-validating the classical baseline on this hardware revision before RL work resumed.
- **`pre-swap/`** (2026-07-17, 23 dives) -- first fully-online TD3 dives on this hardware. Includes the full progression from cold-start collapse through the stuck-recovery and velocity-penalty fixes; best sustained result is `20260717-161502` (81% of samples within 0.05m of setpoint over a 10-minute dive).
- **`post-swap/`** (2026-07-21 -- 2026-07-22, 15 dives) -- after the actuator/buoyancy device was physically swapped, changing the depth dynamics enough to require a model reset (the pre-swap model/replay buffer no longer matched reality -- see `divesync-heavy-v3-data-incomplete-runs/README` for how that was diagnosed). Training restarted fully online on this dataset, converging faster than the original cold start since the warmup/stuck-recovery/reward fixes were already in place.

**Note for reuse:** `pre-swap` and `post-swap` reflect two physically different dynamical systems (same v3 software/methodology, different hardware buoyancy characteristics). Don't pool them for a single tracking-accuracy statistic without accounting for that split.

### `divesync-heavy-v3-data-incomplete-runs/`

Crashed/aborted experiments with no meaningful data (empty or header-only CSVs, no `metadata.json`) -- kept rather than deleted in case they're ever useful for debugging, but excluded from all of the above.

## Results

Comparison plots (behavior cloning, cascaded/fixed/variable PID, fixed/variable-setpoint RL, system identification, step response) are in `/results` and `/results/divesync-heavy-v1-results`.
