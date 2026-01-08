#!/usr/bin/env python3
"""Test script to verify on_time_deliveries counter with a longer run."""

import sys
import numpy as np

# Try to import the environment
try:
    from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv
except ImportError as e:
    print(f"Error importing environment: {e}")
    sys.exit(1)

def test_on_time_deliveries_comprehensive():
    """Run a longer test to get actual deliveries completed."""
    print("Running comprehensive on_time_deliveries test...")
    
    # Create environment
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=10,  # Smaller grid for faster completion
        num_drones=4,  # Fewer drones
        max_orders=50,
        debug_state_warnings=True,
        reward_output_mode="zero"
    )
    
    # Reset the environment
    obs, info = env.reset(seed=42)
    print(f"Initial on_time_deliveries: {env.daily_stats['on_time_deliveries']}")
    print(f"Initial orders_completed: {env.daily_stats['orders_completed']}")
    
    # Track statistics
    on_time_history = []
    completed_history = []
    monotonic = True
    
    # Run for more steps
    max_steps = 200
    for step in range(max_steps):
        # Simple action: all drones head to center
        action = np.random.randn(env.num_drones, 3).astype(np.float32) * 0.1
        
        # Take a step
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Record current stats
        current_on_time = env.daily_stats['on_time_deliveries']
        current_completed = env.daily_stats['orders_completed']
        
        on_time_history.append(current_on_time)
        completed_history.append(current_completed)
        
        # Check monotonicity
        if len(on_time_history) > 1 and current_on_time < on_time_history[-2]:
            print(f"ERROR: on_time_deliveries decreased at step {step + 1}")
            print(f"  Previous: {on_time_history[-2]}, Current: {current_on_time}")
            monotonic = False
            break
        
        # Print progress every 20 steps
        if (step + 1) % 20 == 0:
            print(f"Step {step + 1}: completed={current_completed}, on_time={current_on_time}")
        
        if terminated or truncated:
            print(f"Episode terminated at step {step + 1}")
            break
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Final on_time_deliveries: {env.daily_stats['on_time_deliveries']}")
    print(f"Final orders_completed: {env.daily_stats['orders_completed']}")
    print(f"Final orders_generated: {env.daily_stats['orders_generated']}")
    print(f"Final orders_cancelled: {env.daily_stats['orders_cancelled']}")
    print(f"Total steps run: {len(on_time_history)}")
    
    if env.daily_stats['orders_completed'] > 0:
        on_time_rate = env.daily_stats['on_time_deliveries'] / env.daily_stats['orders_completed']
        print(f"On-time rate: {on_time_rate:.2%}")
    
    # Check results
    if not monotonic:
        print("\n✗ Test FAILED: on_time_deliveries is not monotonic")
        return False
    
    print("\n✓ Test PASSED: on_time_deliveries counter is monotonically non-decreasing")
    
    # Additional checks
    if env.daily_stats['on_time_deliveries'] > env.daily_stats['orders_completed']:
        print("✗ ERROR: on_time_deliveries > orders_completed")
        return False
    
    if env.daily_stats['on_time_deliveries'] < 0:
        print("✗ ERROR: on_time_deliveries is negative")
        return False
    
    print("✓ All consistency checks passed")
    return True

if __name__ == "__main__":
    success = test_on_time_deliveries_comprehensive()
    sys.exit(0 if success else 1)
