#!/usr/bin/env python3
"""
Test script to verify diagnostic logging in UAV_ENVIRONMENT_8.

This script runs a simple random policy for a few steps to:
1. Verify the environment initializes correctly with debug flags
2. Confirm diagnostics are being tracked
3. Print diagnostic summary at the end
"""

import numpy as np
from UAV_ENVIRONMENT_8 import ThreeObjectiveDroneDeliveryEnv

def test_diagnostics():
    """Test diagnostics with random actions."""
    print("="*80)
    print("Testing UAV_ENVIRONMENT_8 Diagnostics")
    print("="*80)
    
    # Create environment with debug flags enabled
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=10,
        num_drones=3,
        max_orders=20,
        steps_per_hour=4,
        debug_env_dynamics=True,  # Enable dynamics diagnostics
        debug_state_warnings=False,  # Disable state warnings for cleaner output
        delivery_sla_steps=3,
        timeout_factor=4.0,
    )
    
    print("\nEnvironment created with debug_env_dynamics=True")
    print(f"Grid size: {env.grid_size}")
    print(f"Num drones: {env.num_drones}")
    print(f"Max orders: {env.max_obs_orders}")
    
    # Reset environment
    obs, info = env.reset(seed=42)
    print(f"\nEnvironment reset. Initial active orders: {len(env.active_orders)}")
    
    # Run for 20 steps with random actions
    num_steps = 20
    print(f"\nRunning {num_steps} steps with random actions...")
    
    for step in range(num_steps):
        # Random action - check action space first
        # For U7, action space should be (num_drones, action_dim)
        # Let's use zeros for simplicity (no action)
        action = env.action_space.sample()  # Use proper action sampling
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        if step % 5 == 0:
            print(f"  Step {step}: Active orders={len(env.active_orders)}, "
                  f"Completed={env.daily_stats['orders_completed']}, "
                  f"Cancelled={env.daily_stats['orders_cancelled']}")
        
        if terminated or truncated:
            print(f"  Episode ended at step {step}")
            break
    
    # Print diagnostics summary
    print("\n" + "="*80)
    print("Diagnostics Summary:")
    print("="*80)
    env.print_dynamics_diagnostics()
    
    # Print some basic stats
    print("\n" + "="*80)
    print("Basic Environment Stats:")
    print("="*80)
    print(f"Orders generated: {env.daily_stats['orders_generated']}")
    print(f"Orders completed: {env.daily_stats['orders_completed']}")
    print(f"Orders cancelled: {env.daily_stats['orders_cancelled']}")
    print(f"On-time deliveries: {env.daily_stats['on_time_deliveries']}")
    
    if env.daily_stats['orders_completed'] > 0:
        on_time_rate = env.daily_stats['on_time_deliveries'] / env.daily_stats['orders_completed']
        print(f"On-time rate: {on_time_rate*100:.1f}%")
        
        completion_rate = env.daily_stats['orders_completed'] / env.daily_stats['orders_generated']
        print(f"Completion rate: {completion_rate*100:.1f}%")
    
    print("\n" + "="*80)
    print("Test completed successfully!")
    print("="*80)

if __name__ == "__main__":
    test_diagnostics()
