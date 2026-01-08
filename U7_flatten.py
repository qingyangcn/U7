"""
Flatten Action Wrapper for Stable-Baselines3 compatibility.

Task 4: Updated for U7 environment which uses (N, 2) action space:
- SB3 Box(N*2,) - flat 1D action space
- Environment Box(N, 2) - structured action space (choice + speed)
"""
import gymnasium as gym
import numpy as np
from gymnasium import spaces


class FlattenActionWrapper(gym.Wrapper):
    """
    Wrapper to flatten/unflatten action space for SB3 compatibility.

    Task 4: Updated for U7 which uses (N, 2) instead of (N, 3).
    Environment expects: (N, 2) array where N is number of drones
    SB3 provides: (N*2,) flat array

    This wrapper handles the conversion.
    """

    def __init__(self, env):
        """
        Initialize wrapper.

        Args:
            env: Gymnasium environment with Box(N, 2) or Box(N, 3) action space
        """
        super().__init__(env)

        # Get original action space
        orig_space = env.action_space

        if not isinstance(orig_space, spaces.Box):
            raise ValueError(f"Expected Box action space, got {type(orig_space)}")

        if len(orig_space.shape) != 2:
            raise ValueError(f"Expected 2D action space (N, D), got shape {orig_space.shape}")

        self.n_drones = orig_space.shape[0]
        self.action_dim = orig_space.shape[1]

        # Task 4: Support both 2 and 3 dimensions
        if self.action_dim not in [2, 3]:
            raise ValueError(f"Expected action dimension 2 (choice, speed) or 3 (hx, hy, u), got {self.action_dim}")

        # Create flattened action space
        flat_size = self.n_drones * self.action_dim

        # Properly flatten bounds to maintain per-dimension constraints
        low_flat = orig_space.low.flatten()
        high_flat = orig_space.high.flatten()

        self.action_space = spaces.Box(
            low=low_flat,
            high=high_flat,
            shape=(flat_size,),
            dtype=orig_space.dtype
        )

    def step(self, action):
        """
        Step with flattened action.

        Args:
            action: Flat array of shape (N*D,) where D is action_dim

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Reshape flat action to (N, D)
        action_reshaped = action.reshape(self.n_drones, self.action_dim)

        # Call environment step
        return self.env.step(action_reshaped)

    def reset(self, **kwargs):
        """Reset environment."""
        return self.env.reset(**kwargs)


class UnflattenActionWrapper(gym.Wrapper):
    """
    Reverse of FlattenActionWrapper.

    Converts (N*D,) from policy to (N, D) for environment.
    Use this if you want to keep the original action space interface.
    """

    def __init__(self, env, n_drones: int, action_dim: int = 2):
        """
        Initialize wrapper.

        Args:
            env: Environment with flat action space
            n_drones: Number of drones
            action_dim: Action dimension per drone (default 2 for U7, was 3 for U6)
        """
        super().__init__(env)

        self.n_drones = n_drones
        self.action_dim = action_dim

        # Create structured action space
        flat_size = n_drones * action_dim
        orig_low = env.action_space.low[0]
        orig_high = env.action_space.high[0]

        self.action_space = spaces.Box(
            low=orig_low,
            high=orig_high,
            shape=(n_drones, action_dim),
            dtype=env.action_space.dtype
        )

    def step(self, action):
        """
        Step with structured action.

        Args:
            action: Array of shape (N, D)

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Flatten action to (N*D,)
        action_flat = action.flatten()

        # Call environment step
        return self.env.step(action_flat)

    def reset(self, **kwargs):
        """Reset environment."""
        return self.env.reset(**kwargs)