"""
Baseline Heuristics for U7 Environment

Provides clean comparisons using different assignment and action policies:
1. Random assignment + random action
2. Random assignment + cargo-first action
3. Greedy assignment (min incremental distance) + cargo-first action
4. EDF assignment (earliest deadline / minimum slack) + cargo-first action

Usage:
    python baseline_heuristics.py --policy random-random --episodes 10
    python baseline_heuristics.py --policy random-cargo --episodes 10
    python baseline_heuristics.py --policy greedy-cargo --episodes 10
    python baseline_heuristics.py --policy edf-cargo --episodes 10
    python baseline_heuristics.py --policy all --episodes 5
"""

import argparse
import sys
import os
import numpy as np
from typing import Tuple, List, Dict

# Add repo to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv, OrderStatus, DroneStatus


def euclidean_distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))


def random_assignment(env: ThreeObjectiveDroneDeliveryEnv, max_ready: int = 400) -> int:
    """
    Random assignment policy: Assign each READY order to a random drone that can accept more.
    Returns number of orders assigned.
    """
    ready_orders = env.get_ready_orders_snapshot(limit=max_ready)
    if not ready_orders:
        return 0

    drones = env.get_drones_snapshot()
    available_drones = [d for d in drones if d.get("can_accept_more", False)]
    
    if not available_drones:
        return 0

    assigned = 0
    for order in ready_orders:
        order_id = int(order["order_id"])
        
        # Randomly select an available drone
        drone = np.random.choice(available_drones)
        drone_id = int(drone["drone_id"])
        
        before = env.drones[drone_id]["current_load"]
        env._process_single_assignment(drone_id, order_id, allow_busy=True)
        after = env.drones[drone_id]["current_load"]
        
        if after > before:
            assigned += 1
    
    return assigned


def greedy_assignment(env: ThreeObjectiveDroneDeliveryEnv, max_ready: int = 400) -> int:
    """
    Greedy assignment policy: Assign each READY order to the nearest drone that can accept more.
    Uses incremental distance from drone's current location to merchant.
    Returns number of orders assigned.
    """
    ready_orders = env.get_ready_orders_snapshot(limit=max_ready)
    if not ready_orders:
        return 0

    drones = env.get_drones_snapshot()
    if not drones:
        return 0

    assigned = 0
    for order in ready_orders:
        order_id = int(order["order_id"])
        merchant_loc = order["merchant_location"]

        # Find nearest available drone
        best_drone = None
        best_distance = float('inf')
        
        for drone in drones:
            if not drone.get("can_accept_more", False):
                continue
            
            distance = euclidean_distance(drone["location"], merchant_loc)
            if distance < best_distance:
                best_distance = distance
                best_drone = int(drone["drone_id"])
        
        if best_drone is None:
            continue

        before = env.drones[best_drone]["current_load"]
        env._process_single_assignment(best_drone, order_id, allow_busy=True)
        after = env.drones[best_drone]["current_load"]
        
        if after > before:
            assigned += 1
    
    return assigned


def edf_assignment(env: ThreeObjectiveDroneDeliveryEnv, max_ready: int = 400) -> int:
    """
    EDF (Earliest Deadline First) assignment policy:
    1. Sort orders by deadline (earliest first)
    2. For each order, assign to the nearest drone that can accept more
    Returns number of orders assigned.
    """
    ready_orders = env.get_ready_orders_snapshot(limit=max_ready)
    if not ready_orders:
        return 0

    drones = env.get_drones_snapshot()
    if not drones:
        return 0

    # Sort orders by deadline (earliest first)
    ready_orders.sort(key=lambda o: o.get("deadline_step", float('inf')))

    assigned = 0
    for order in ready_orders:
        order_id = int(order["order_id"])
        merchant_loc = order["merchant_location"]

        # Find nearest available drone
        best_drone = None
        best_distance = float('inf')
        
        for drone in drones:
            if not drone.get("can_accept_more", False):
                continue
            
            distance = euclidean_distance(drone["location"], merchant_loc)
            if distance < best_distance:
                best_distance = distance
                best_drone = int(drone["drone_id"])
        
        if best_drone is None:
            continue

        before = env.drones[best_drone]["current_load"]
        env._process_single_assignment(best_drone, order_id, allow_busy=True)
        after = env.drones[best_drone]["current_load"]
        
        if after > before:
            assigned += 1
    
    return assigned


def random_action(env: ThreeObjectiveDroneDeliveryEnv) -> np.ndarray:
    """
    Random action policy: Generate random actions for all drones.
    Action shape: (num_drones, 2) where:
        [:, 0] is task choice in [-1, 1]
        [:, 1] is speed in [-1, 1]
    """
    return np.random.uniform(-1.0, 1.0, size=(env.num_drones, 2)).astype(np.float32)


def cargo_first_action(env: ThreeObjectiveDroneDeliveryEnv) -> np.ndarray:
    """
    Cargo-first action policy:
    - For each drone, prioritize delivering already-picked-up orders (in cargo)
    - If no cargo, select first assigned order to pick up
    - If no orders, random action
    
    Action shape: (num_drones, 2) where:
        [:, 0] is task choice in [-1, 1]
        [:, 1] is speed in [-1, 1] (always 1.0 for max speed)
    """
    action = np.zeros((env.num_drones, 2), dtype=np.float32)
    
    for drone_id in range(env.num_drones):
        drone = env.drones[drone_id]
        
        # Always use max speed
        action[drone_id, 1] = 1.0
        
        # Get candidate list for this drone
        if drone_id not in env.drone_candidate_mappings:
            action[drone_id, 0] = 0.0  # Default choice
            continue
        
        candidates = env.drone_candidate_mappings[drone_id]
        
        # Find first cargo order (PICKED_UP) or assigned order (ASSIGNED)
        best_idx = -1
        best_priority = 0  # 2 = cargo (highest), 1 = assigned, 0 = none
        
        for idx, (order_id, is_valid) in enumerate(candidates):
            if not is_valid or order_id < 0 or order_id not in env.orders:
                continue
            
            order = env.orders[order_id]
            
            # Priority: cargo first, then assigned
            if order['status'] == OrderStatus.PICKED_UP:
                if best_priority < 2:
                    best_idx = idx
                    best_priority = 2
            elif order['status'] == OrderStatus.ASSIGNED and best_priority < 1:
                best_idx = idx
                best_priority = 1
        
        # Convert index to action value in [-1, 1]
        if best_idx >= 0 and len(candidates) > 0:
            # Map [0, K-1] -> [-1, 1]
            choice_normalized = (best_idx / max(len(candidates) - 1, 1)) * 2.0 - 1.0
            action[drone_id, 0] = np.clip(choice_normalized, -1.0, 1.0)
        else:
            # No valid order, default to first candidate
            action[drone_id, 0] = -1.0
    
    return action


def run_episode(env: ThreeObjectiveDroneDeliveryEnv, 
                assignment_fn, 
                action_fn,
                verbose: bool = False) -> Dict[str, float]:
    """
    Run a single episode with specified assignment and action policies.
    
    Args:
        env: Environment instance
        assignment_fn: Function to assign orders (called each step)
        action_fn: Function to generate actions (called each step)
        verbose: Whether to print step-by-step info
    
    Returns:
        Dictionary with episode metrics
    """
    obs, info = env.reset()
    terminated = False
    truncated = False
    step_count = 0
    
    while not (terminated or truncated):
        # Assignment phase
        if assignment_fn is not None:
            num_assigned = assignment_fn(env)
            if verbose and num_assigned > 0:
                print(f"Step {step_count}: Assigned {num_assigned} orders")
        
        # Action phase
        action = action_fn(env)
        obs, reward, terminated, truncated, info = env.step(action)
        step_count += 1
    
    # Extract metrics
    daily_stats = info['episode']['daily_stats']
    completed = daily_stats.get('orders_completed', 0)
    generated = daily_stats.get('orders_generated', 1)  # Avoid division by zero
    on_time = daily_stats.get('on_time_deliveries', 0)
    
    completion_rate = completed / max(generated, 1)
    on_time_rate = on_time / max(completed, 1)
    
    metrics = {
        'completion_rate': completion_rate,
        'on_time_rate': on_time_rate,
        'completed': completed,
        'generated': generated,
        'on_time': on_time,
        'cancelled': daily_stats.get('orders_cancelled', 0),
        'energy_consumed': daily_stats.get('energy_consumed', 0),
        'total_distance': daily_stats.get('total_flight_distance', 0.0),
        'legacy_blocked': info.get('legacy_blocked_count', 0),
    }
    
    return metrics


def run_baseline(policy_name: str, num_episodes: int = 10, seed: int = 42) -> None:
    """
    Run baseline experiments with specified policy.
    
    Args:
        policy_name: One of 'random-random', 'random-cargo', 'greedy-cargo', 'edf-cargo'
        num_episodes: Number of episodes to run
        seed: Random seed
    """
    print(f"\n{'='*60}")
    print(f"Running baseline: {policy_name}")
    print(f"Episodes: {num_episodes}, Seed: {seed}")
    print(f"{'='*60}\n")
    
    # Parse policy
    parts = policy_name.split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid policy name: {policy_name}. Expected format: 'assignment-action'")
    
    assignment_type, action_type = parts
    
    # Select assignment function
    if assignment_type == 'random':
        assignment_fn = random_assignment
    elif assignment_type == 'greedy':
        assignment_fn = greedy_assignment
    elif assignment_type == 'edf':
        assignment_fn = edf_assignment
    else:
        raise ValueError(f"Unknown assignment type: {assignment_type}")
    
    # Select action function
    if action_type == 'random':
        action_fn = random_action
    elif action_type == 'cargo':
        action_fn = cargo_first_action
    else:
        raise ValueError(f"Unknown action type: {action_type}")
    
    # Create environment
    # Note: baseline script does its own assignment/action selection, so it can work
    # with legacy disabled. Standard MOPSO+PPO training should use enable_legacy_fallback=True.
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=50,
        max_orders=400,
        enable_legacy_fallback=True,  # Keep enabled - baselines use assignment+action policies
        debug_state_warnings=False,  # Reduce console spam
        enable_random_events=True,
        reward_output_mode="zero",
    )
    
    # Run episodes
    all_metrics = []
    for episode in range(num_episodes):
        episode_seed = seed + episode
        np.random.seed(episode_seed)
        
        metrics = run_episode(env, assignment_fn, action_fn, verbose=False)
        all_metrics.append(metrics)
        
        print(f"Episode {episode+1}/{num_episodes}: "
              f"completion_rate={metrics['completion_rate']:.3f}, "
              f"on_time_rate={metrics['on_time_rate']:.3f}, "
              f"completed={metrics['completed']}, "
              f"generated={metrics['generated']}, "
              f"legacy_blocked={metrics['legacy_blocked']}")
    
    # Compute statistics
    completion_rates = [m['completion_rate'] for m in all_metrics]
    on_time_rates = [m['on_time_rate'] for m in all_metrics]
    completed_counts = [m['completed'] for m in all_metrics]
    
    print(f"\n{'='*60}")
    print(f"Summary for {policy_name}:")
    print(f"  Completion rate: {np.mean(completion_rates):.3f} ± {np.std(completion_rates):.3f}")
    print(f"  On-time rate:    {np.mean(on_time_rates):.3f} ± {np.std(on_time_rates):.3f}")
    print(f"  Avg completed:   {np.mean(completed_counts):.1f} ± {np.std(completed_counts):.1f}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Run baseline heuristics for U7 environment')
    parser.add_argument('--policy', type=str, default='all',
                        choices=['random-random', 'random-cargo', 'greedy-cargo', 'edf-cargo', 'all'],
                        help='Baseline policy to run (default: all)')
    parser.add_argument('--episodes', type=int, default=5,
                        help='Number of episodes per policy (default: 5)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    
    args = parser.parse_args()
    
    if args.policy == 'all':
        policies = ['random-random', 'random-cargo', 'greedy-cargo', 'edf-cargo']
    else:
        policies = [args.policy]
    
    for policy in policies:
        try:
            run_baseline(policy, num_episodes=args.episodes, seed=args.seed)
        except Exception as e:
            print(f"Error running policy {policy}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
