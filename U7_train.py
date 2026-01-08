"""
U7 PPO Training (Task Selection + Speed Control) + MOPSO Assignment-Only

- Env: UAV_ENVIRONMENT_7.ThreeObjectiveDroneDeliveryEnv
  * Action: Box(shape=(num_drones,2)) where:
      action[d,0] = choice_raw in [-1,1] (env discretizes to candidate index)
      action[d,1] = speed_raw  in [-1,1] (env maps to speed multiplier)
  * Observation: Dict includes candidates (num_drones, K=20, 12)
  * reward_output_mode: "scalar" (required for SB3 PPO learning)

- Dispatcher: U7_mopso_dispatcher.MOPSOPlanner
  * This script runs "assignment-only" each step:
      READY orders -> ASSIGNED with assigned_drone set, respecting capacity.
  * No planned_stops route is installed (avoid queueing/append issues).

Run:
  python U7_train_ppo_task_selection.py --total-steps 200000 --seed 42 --num-drones 50 --obs-max-orders 400
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, List, Dict, Tuple

import numpy as np
import gymnasium as gym

# repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv
from U7_mopso_dispatcher import MOPSOPlanner


def _euclid(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def greedy_assignment_only(env: ThreeObjectiveDroneDeliveryEnv, max_ready: int = 400) -> int:
    """
    Fallback assignment-only policy:
    - For each READY order (up to max_ready), assign to the nearest drone that can_accept_more.
    - Uses env._process_single_assignment(drone_id, order_id, allow_busy=True).
    Returns number of orders newly assigned.
    """
    ready_orders = env.get_ready_orders_snapshot(limit=max_ready)
    if not ready_orders:
        return 0

    drones = env.get_drones_snapshot()
    if not drones:
        return 0

    assigned = 0
    for o in ready_orders:
        oid = int(o["order_id"])
        mloc = o["merchant_location"]

        best = None
        best_cost = 1e18
        for d in drones:
            if not d.get("can_accept_more", False):
                continue
            # keep it simple: choose nearest by current location
            cost = _euclid(d["location"], mloc)
            if cost < best_cost:
                best_cost = cost
                best = int(d["drone_id"])

        if best is None:
            continue

        before = env.drones[best]["current_load"]
        env._process_single_assignment(best, oid, allow_busy=True)
        after = env.drones[best]["current_load"]
        if after > before:
            assigned += 1

    return assigned


def mopso_assignment_only(env: ThreeObjectiveDroneDeliveryEnv, planner: MOPSOPlanner) -> int:
    """
    Preferred assignment-only path using the new U7MOPSOAssigner.

    Task 3: Uses prioritize_idle=True and allow_busy_fallback=False by default
    to avoid assigning new READY orders to busy drones, improving on-time rate.

    Args:
        env: Environment instance
        planner: MOPSOPlanner instance (used to create U7MOPSOAssigner)

    Returns:
        Number of orders assigned
    """
    # 1) Use the new U7MOPSOAssigner with proper configuration
    try:
        from U7_mopso_dispatcher import U7MOPSOAssigner
        
        # Create assigner with safe defaults: IDLE drones only, no busy fallback
        assigner = U7MOPSOAssigner(
            n_particles=planner.n_particles,
            n_iterations=planner.n_iterations,
            max_orders=planner.max_orders,
            max_orders_per_drone=planner.max_orders_per_drone,
            prioritize_idle=True,  # Task 3: Prioritize IDLE drones
            allow_busy_fallback=False,  # Task 3: Do not assign to busy drones
        )
        
        # Get assignment from MOPSO
        assignment = assigner.assign_orders(env)
        
        # Apply assignments to environment using _process_single_assignment
        assigned = 0
        for drone_id, order_ids in assignment.items():
            for oid in order_ids:
                before = env.drones[int(drone_id)]["current_load"]
                env._process_single_assignment(int(drone_id), int(oid), allow_busy=True)
                after = env.drones[int(drone_id)]["current_load"]
                if after > before:
                    assigned += 1
        return assigned
    except Exception as e:
        # Fallback to greedy assignment if something goes wrong
        import warnings
        warnings.warn(f"Failed to use U7MOPSOAssigner: {e}. Falling back to greedy assignment.")
        return greedy_assignment_only(env)


class MOPSOAssignWrapper(gym.Wrapper):
    """Call assignment-only every step before PPO action is applied."""

    def __init__(self, env: gym.Env, planner: MOPSOPlanner):
        super().__init__(env)
        self.planner = planner

    def step(self, action):
        mopso_assignment_only(self.env, self.planner)  # type: ignore[arg-type]
        return self.env.step(action)

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        mopso_assignment_only(self.env, self.planner)  # type: ignore[arg-type]
        return obs, info


def make_env(
    seed: int,
    num_drones: int,
    obs_max_orders: int,
    top_k_merchants: int,
    candidate_k: int,
    enable_random_events: bool,
    debug_state_warnings: bool,
    mopso_max_orders: int,
    mopso_max_orders_per_drone: int,
) -> gym.Env:
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=num_drones,
        max_orders=obs_max_orders,          # 订单观测窗口
        num_bases=2,
        steps_per_hour=4,
        drone_max_capacity=10,
        top_k_merchants=top_k_merchants,
        reward_output_mode="scalar",        # IMPORTANT: PPO必须是scalar才会学
        enable_random_events=enable_random_events,
        debug_state_warnings=debug_state_warnings,
        fixed_objective_weights=(0.5, 0.3, 0.2),
        num_candidates=candidate_k,         # K=20
    )

    planner = MOPSOPlanner(
        n_particles=30,
        n_iterations=10,
        max_orders=mopso_max_orders,
        max_orders_per_drone=mopso_max_orders_per_drone,
        eta_speed_scale_assumption=0.7,
        eta_stop_service_steps=1,
    )

    env = MOPSOAssignWrapper(env, planner)
    return env


def train(args):
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv
        from stable_baselines3.common.callbacks import CheckpointCallback
    except ImportError as e:
        raise RuntimeError("Please install stable-baselines3: pip install stable-baselines3") from e

    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(args.model_dir, exist_ok=True)

    def env_fn():
        return make_env(
            seed=args.seed,
            num_drones=args.num_drones,
            obs_max_orders=args.obs_max_orders,
            top_k_merchants=args.top_k_merchants,
            candidate_k=args.candidate_k,
            enable_random_events=args.enable_random_events,
            debug_state_warnings=args.debug_state_warnings,
            mopso_max_orders=args.mopso_max_orders,
            mopso_max_orders_per_drone=args.mopso_max_orders_per_drone,
        )

    env = DummyVecEnv([env_fn])

    print("=" * 70)
    print("U7 PPO: per-drone task selection (K=20) + speed control; MOPSO assignment-only each step")
    print("=" * 70)
    print(f"num_drones={args.num_drones}, obs_max_orders={args.obs_max_orders}, top_k_merchants={args.top_k_merchants}")
    print(f"candidate_k={args.candidate_k}")
    print(f"MOPSO assignment: M={args.mopso_max_orders}, max_orders_per_drone={args.mopso_max_orders_per_drone}")
    print(f"reward_output_mode=scalar, enable_random_events={args.enable_random_events}")
    print("=" * 70)

    model = PPO(
        policy="MultiInputPolicy",
        env=env,
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        clip_range=args.clip_range,
        verbose=1,
        tensorboard_log=args.log_dir,
        seed=args.seed,
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=args.save_freq,
        save_path=args.model_dir,
        name_prefix="ppo_u7_task",
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    model.learn(total_timesteps=args.total_steps, callback=checkpoint_callback, progress_bar=True)

    final_path = os.path.join(args.model_dir, "ppo_u7_task_final")
    model.save(final_path)
    print(f"Saved final model to: {final_path}")

    env.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--total-steps", type=int, default=200000)
    p.add_argument("--seed", type=int, default=42)

    # env knobs
    p.add_argument("--num-drones", type=int, default=10)
    p.add_argument("--obs-max-orders", type=int, default=400)
    p.add_argument("--top-k-merchants", type=int, default=100)
    p.add_argument("--candidate-k", type=int, default=20)

    p.add_argument("--enable-random-events", action="store_true")
    p.add_argument("--debug-state-warnings", action="store_true")

    # mopso knobs
    p.add_argument("--mopso-max-orders", type=int, default=400)
    p.add_argument("--mopso-max-orders-per-drone", type=int, default=5)

    # ppo knobs
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--n-steps", type=int, default=2048)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--n-epochs", type=int, default=10)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--clip-range", type=float, default=0.2)

    p.add_argument("--save-freq", type=int, default=10000)
    p.add_argument("--log-dir", type=str, default="./logs/u7_task")
    p.add_argument("--model-dir", type=str, default="./models/u7_task")

    args = p.parse_args()
    train(args)


if __name__ == "__main__":
    main()