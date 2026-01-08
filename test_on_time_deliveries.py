#!/usr/bin/env python3
"""Test script to verify on_time_deliveries counter is monotonically non-decreasing."""

import sys
import numpy as np

# Try to import the environment
try:
    from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv
except ImportError as e:
    print(f"Error importing environment: {e}")
    sys.exit(1)

def test_on_time_deliveries_monotonic():
    """Test that on_time_deliveries never decreases during an episode."""
    print("Testing on_time_deliveries counter...")
    
    # Create environment with debug warnings enabled
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=6,
        max_orders=100,
        debug_state_warnings=True,  # Enable debug warnings
        reward_output_mode="zero"
    )
    
    # Reset the environment
    obs, info = env.reset(seed=42)
    print(f"Initial on_time_deliveries: {env.daily_stats['on_time_deliveries']}")
    
    # Track on_time_deliveries across steps
    on_time_history = [env.daily_stats['on_time_deliveries']]
    
    # Run for a number of steps
    max_steps = 100
    for step in range(max_steps):
        # Random action (just for testing)
        action = np.zeros((env.num_drones, 3), dtype=np.float32)
        
        # Take a step
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Record current on_time_deliveries
        current_on_time = env.daily_stats['on_time_deliveries']
        on_time_history.append(current_on_time)
        
        # Check monotonicity
        if current_on_time < on_time_history[-2]:
            print(f"ERROR: on_time_deliveries decreased at step {step + 1}")
            print(f"  Previous: {on_time_history[-2]}, Current: {current_on_time}")
            return False
        
        if terminated or truncated:
            print(f"Episode terminated at step {step + 1}")
            break
    
    # Print summary
    print(f"\nTest completed successfully!")
    print(f"Final on_time_deliveries: {env.daily_stats['on_time_deliveries']}")
    print(f"Total steps: {len(on_time_history) - 1}")
    print(f"On-time deliveries history (first 20): {on_time_history[:20]}")
    
    # Verify monotonicity
    for i in range(1, len(on_time_history)):
        if on_time_history[i] < on_time_history[i-1]:
            print(f"ERROR: Monotonicity violated at index {i}")
            return False
    
    print("\n✓ on_time_deliveries counter is monotonically non-decreasing")
    return True

if __name__ == "__main__":
    success = test_on_time_deliveries_monotonic()
    sys.exit(0 if success else 1)
