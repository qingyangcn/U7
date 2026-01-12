"""
Test script to verify diagnostic functionality in UAV_ENVIRONMENT_7.py

This script runs a short episode with debug_diagnostics=True to verify
that all diagnostic counters are being tracked correctly.
"""

import sys
import numpy as np

# Import the environment
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv

def test_diagnostics():
    """Run a short episode with diagnostics enabled."""
    
    print("=" * 70)
    print("Testing UAV_ENVIRONMENT_7 Diagnostics")
    print("=" * 70)
    
    # Create environment with diagnostics enabled
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=6,
        max_orders=100,
        steps_per_hour=4,
        drone_max_capacity=10,
        reward_output_mode="zero",
        enable_random_events=False,  # Disable for deterministic test
        debug_diagnostics=True,  # Enable diagnostics
        debug_state_warnings=True,  # Enable detailed warnings
        num_candidates=20,
    )
    
    print("\nEnvironment created with debug_diagnostics=True")
    print(f"Grid size: {env.grid_size}")
    print(f"Num drones: {env.num_drones}")
    print(f"Max orders: {env.max_obs_orders}")
    
    # Reset environment
    obs, info = env.reset(seed=42)
    print("\nEnvironment reset. Starting episode...")
    
    # Run for a short number of steps
    max_steps = 200
    step_count = 0
    
    while step_count < max_steps:
        # Generate random action (simple heading for each drone)
        action = np.random.randn(env.num_drones, 3).astype(np.float32)
        
        # Step environment
        obs, reward, terminated, truncated, info = env.step(action)
        step_count += 1
        
        # Print progress every 64 steps
        if step_count % 64 == 0:
            print(f"\nStep {step_count}: Orders active={len(env.active_orders)}, completed={len(env.completed_orders)}")
        
        if terminated:
            print(f"\nEpisode terminated at step {step_count}")
            break
    
    print(f"\nTest completed after {step_count} steps")
    print("\n" + "=" * 70)
    print("Diagnostic counters (should be non-zero if working correctly):")
    print("=" * 70)
    for key, value in env.diagnostics.items():
        if key != 'order_status_snapshots':
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {len(value)} snapshots collected")
    
    return env

if __name__ == "__main__":
    try:
        env = test_diagnostics()
        print("\n✓ Diagnostic test completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Diagnostic test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
