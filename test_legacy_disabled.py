#!/usr/bin/env python3
"""
Quick test to verify legacy disabled works with READY orders in candidates.
Run for a few steps and check:
1. Drones have valid candidates including READY orders
2. Legacy blocked count remains low
3. Completed orders increase reasonably
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv

def test_legacy_disabled():
    print("=" * 70)
    print("Testing: Legacy Disabled + READY orders in candidates")
    print("=" * 70)
    
    # Create environment with legacy disabled
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=10,
        max_orders=400,
        num_bases=2,
        steps_per_hour=12,
        drone_max_capacity=10,
        top_k_merchants=100,
        reward_output_mode="scalar",
        enable_random_events=False,
        debug_state_warnings=True,  # Enable detailed logging
        fixed_objective_weights=(0.5, 0.3, 0.2),
        num_candidates=20,
        enable_legacy_fallback=False,  # DISABLED
    )
    
    # Reset and run (without MOPSO wrapper for simplicity)
    obs, info = env.reset(seed=42)
    print(f"\nInitial state:")
    print(f"  Active orders: {len(env.active_orders)}")
    ready_count = sum(1 for oid in env.active_orders if env.orders[oid]['status'].name == 'READY')
    print(f"  READY orders: {ready_count}")
    
    total_steps = 200
    for step in range(total_steps):
        # Random action for testing
        action = env.action_space.sample()
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        if (step + 1) % 50 == 0:
            print(f"\n[Step {step + 1}]")
            print(f"  Active orders: {len(env.active_orders)}")
            print(f"  Completed: {env.daily_stats['orders_completed']}")
            print(f"  Cancelled: {env.daily_stats['orders_cancelled']}")
            print(f"  Legacy blocked: {env.legacy_blocked_count}")
            
            # Check candidate validity
            ready_in_candidates = 0
            assigned_in_candidates = 0
            cargo_in_candidates = 0
            valid_candidates = 0
            
            for drone_id in range(env.num_drones):
                if drone_id not in env.drone_candidate_mappings:
                    continue
                candidate_list = env.drone_candidate_mappings[drone_id]
                for order_id, is_valid in candidate_list:
                    if is_valid and order_id >= 0 and order_id in env.orders:
                        valid_candidates += 1
                        order = env.orders[order_id]
                        if order['status'].name == 'READY':
                            ready_in_candidates += 1
                        elif order['status'].name == 'ASSIGNED':
                            assigned_in_candidates += 1
                        elif order['status'].name == 'PICKED_UP':
                            cargo_in_candidates += 1
            
            print(f"  Valid candidates: {valid_candidates}")
            print(f"    - READY: {ready_in_candidates}")
            print(f"    - ASSIGNED: {assigned_in_candidates}")
            print(f"    - PICKED_UP (cargo): {cargo_in_candidates}")
        
        if terminated or truncated:
            print(f"\nEpisode ended at step {step + 1}")
            break
    
    print("\n" + "=" * 70)
    print("Final Results:")
    print("=" * 70)
    print(f"Orders generated: {env.daily_stats['orders_generated']}")
    print(f"Orders completed: {env.daily_stats['orders_completed']}")
    print(f"Orders cancelled: {env.daily_stats['orders_cancelled']}")
    print(f"Legacy blocked count: {env.legacy_blocked_count}")
    print(f"On-time deliveries: {env.daily_stats['on_time_deliveries']}")
    
    # Assertions
    completion_rate = env.daily_stats['orders_completed'] / max(env.daily_stats['orders_generated'], 1)
    print(f"\nCompletion rate: {completion_rate:.2%}")
    
    # Check that READY orders are actually included in candidates
    ready_in_any_candidate = 0
    for drone_id in range(env.num_drones):
        if drone_id not in env.drone_candidate_mappings:
            continue
        candidate_list = env.drone_candidate_mappings[drone_id]
        for order_id, is_valid in candidate_list:
            if is_valid and order_id >= 0 and order_id in env.orders:
                order = env.orders[order_id]
                if order['status'].name == 'READY':
                    ready_in_any_candidate += 1
                    break  # Count each drone only once
    
    print(f"Drones with READY candidates: {ready_in_any_candidate}/{env.num_drones}")
    
    if ready_in_any_candidate > 0:
        print("✓ SUCCESS: READY orders are included in candidates")
    else:
        print("✗ WARNING: No READY orders found in candidates")
    
    if completion_rate > 0.01:  # Lower threshold since we're not using MOPSO
        print("✓ SUCCESS: Some orders completed (reasonable with random actions)")
    else:
        print("✗ WARNING: Very low completion rate")
    
    if env.legacy_blocked_count < 100:
        print(f"✓ SUCCESS: Legacy blocked count ({env.legacy_blocked_count}) is acceptable")
    else:
        print(f"✗ WARNING: Legacy blocked count ({env.legacy_blocked_count}) is high")
    
    print("\nTest completed.")
    print("=" * 70)

if __name__ == "__main__":
    test_legacy_disabled()
