import gymnasium as gym
import numpy as np


class DiveSyncEnv(gym.Env):
    def __init__(
        self,
        serial_manager,
        telemetry,
        processor,
        state,
        inner_pid,
        reward_fn,
        stroke,
        max_steps=400,
    ):
        super().__init__()

        self.ser = serial_manager
        self.tel = telemetry
        self.pro = processor
        self.state = state
        self.inner = inner_pid
        self.reward_fn = reward_fn

        self.stroke = float(stroke)

        self.step_count = 0
        self.max_steps = max_steps

        self.observation_space = gym.spaces.Box(
            low=np.array([0.0, 0.0, -2.0, -0.5], dtype=np.float32),
            high=np.array([2.0, 2.0, 2.0, 0.5], dtype=np.float32),
            dtype=np.float32,
        )

        self.action_space = gym.spaces.Box(
            low=np.array([0.0], dtype=np.float32),
            high=np.array([self.stroke], dtype=np.float32),
            dtype=np.float32,
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.step_count = 0

        #
        # TODO:
        # Decide how an episode begins.
        #
        # For real hardware this might mean:
        #   - wait until operator presses Enter
        #   - move actuator to equilibrium
        #   - wait for depth to stabilize
        #

        observation = np.array([
            self.state.depth_m,
            self.state.depth_setpoint_m,
            self.state.depth_error_m,
            self.state.velocity_mps,
        ], dtype=np.float32)

        return observation, {}

    def step(self, action):

        self.step_count += 1

        #
        # Agent outputs desired actuator position
        #

        actuator_setpoint = float(action[0])

        #
        # Existing architecture:
        #
        # actuator setpoint
        #      ↓
        # inner PID
        #      ↓
        # PWM
        #      ↓
        # ESP32
        #

        pwm = self.inner.get_command(
            self.pro.actuator_mm,
            actuator_setpoint,
        )

        self.ser.write_command(pwm)

        #
        # Wait for next telemetry packet
        #

        while True:

            line = self.ser.read_line()

            if not line:
                continue

            #
            # You already have CSV validation somewhere.
            # Reuse it here.
            #

            break

        self.tel.update(line)

        self.pro.process_depth(self.tel)
        self.pro.process_actuator(
            actuator_setpoint,
            self.state.depth_setpoint_m,
        )

        self.state.update(self.pro)

        reward = self.reward_fn(self.state)

        observation = np.array([
            self.state.depth_m,
            self.state.depth_setpoint_m,
            self.state.depth_error_m,
            self.state.velocity_mps,
        ], dtype=np.float32)

        terminated = False

        truncated = self.step_count >= self.max_steps

        info = {}

        return observation, reward, terminated, truncated, info
