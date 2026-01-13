#!/usr/bin/env python3
"""
Test script to verify debug instrumentation works and diagnose PPO+MOPSO issues.

This runs a short simulation with:
- enable_legacy_fallback=False (the problematic configuration)
- debug_task_selection=True (to see what's happening)
- Small number of drones and short duration for quick testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv, OrderStatus

def simple_greedy_assignment(env, max_assign=10):
    """Simple greedy assignment: assign READY orders to idle drones."""
    assigned_count = 0
    
    # Find idle drones
    idle_drones = [did for did, d in env.drones.items() 
                   if d['status'].name == 'IDLE' and d['current_load'] < d['max_capacity']]
    
    if not idle_drones:
        return assigned_count
    
    # Find READY orders
    ready_orders = []
    for oid in env.active_orders:
        if oid in env.orders:
            order = env.orders[oid]
            if order['status'] == OrderStatus.READY and order.get('assigned_drone', -1) == -1:
                ready_orders.append(oid)
    
    # Assign orders to drones
    for oid in ready_orders[:min(max_assign, len(idle_drones))]:
        if not idle_drones:
            break
        drone_id = idle_drones.pop(0)
        try:
            env._process_single_assignment(drone_id, oid, allow_busy=True)
            assigned_count += 1
        except Exception as e:
            print(f"Failed to assign order {oid} to drone {drone_id}: {e}")
    
    return assigned_count

def main():
    print("=" * 80)
    print("Testing Debug Instrumentation - Legacy Fallback DISABLED")
    print("=" * 80)
    
    # Create environment with debug instrumentation
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=10,  # More drones for better testing
        max_orders=200,
        num_bases=2,
        steps_per_hour=12,
        drone_max_capacity=10,
        top_k_merchants=50,
        reward_output_mode="scalar",
        enable_random_events=False,  # Disable for deterministic testing
        debug_state_warnings=False,  # Reduce noise
        debug_task_selection=True,  # Enable debug instrumentation
        debug_task_selection_interval=50,  # Print every 50 steps
        fixed_objective_weights=(0.5, 0.3, 0.2),
        num_candidates=20,
        enable_legacy_fallback=False,  # DISABLED - this is the problematic config
    )
    
    # Reset environment
    obs, info = env.reset(seed=42)
    
    print(f"\nStarting simulation...")
    print(f"  Drones: {env.num_drones}")
    print(f"  Enable legacy fallback: {env.enable_legacy_fallback}")
    print(f"  Debug task selection: {env.debug_task_selection}")
    print(f"  Debug interval: {env.debug_task_selection_interval}")
    print()
    
    # Run simulation for 200 steps
    max_steps = 200
    for step in range(max_steps):
        # Apply simple greedy assignment (READY -> ASSIGNED)
        assigned = simple_greedy_assignment(env, max_assign=5)
        
        # Generate random PPO-like action
        # action shape: (num_drones, 2) where [:, 0] is choice, [:, 1] is speed
        action = np.random.uniform(-1, 1, size=(env.num_drones, 2))
        
        # Step environment
        obs, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            print(f"\nEpisode ended at step {step}")
            break
    
    # Print final summary
    print("\n" + "=" * 80)
    print("Final Summary")
    print("=" * 80)
    print(f"Orders generated: {info['daily_stats']['orders_generated']}")
    print(f"Orders completed: {info['daily_stats']['orders_completed']}")
    print(f"Orders cancelled: {info['daily_stats']['orders_cancelled']}")
    print(f"On-time deliveries: {info['daily_stats']['on_time_deliveries']}")
    print(f"Legacy blocked count: {info['legacy_blocked_count']}")
    print(f"Active orders: {info['backlog_size']}")
    print("=" * 80)
    
    # Diagnose the issue
    if info['daily_stats']['orders_completed'] < 10:
        print("\n⚠️  WARNING: Very low completion rate detected!")
        print("This confirms the issue with enable_legacy_fallback=False")
    
    env.close()
    print("\nTest complete!")

if __name__ == "__main__":
    main()
