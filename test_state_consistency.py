#!/usr/bin/env python3
"""
Simple test script to validate state consistency improvements in U7 task-selection mode.
"""
import numpy as np
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv

def test_basic_environment():
    """Test basic environment creation and reset."""
    print("=" * 60)
    print("Testing U7 Environment - State Consistency")
    print("=" * 60)
    
    # Create environment with debug enabled
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=6,
        max_orders=100,
        steps_per_hour=4,
        drone_max_capacity=10,
        reward_output_mode="zero",
        enable_random_events=False,  # Disable for deterministic testing
        debug_state_warnings=True,   # Enable detailed warnings
        num_candidates=20,
    )
    
    print("\n1. Testing environment reset...")
    obs, info = env.reset(seed=42)
    
    # Verify drones have serving_order_id initialized
    for drone_id, drone in env.drones.items():
        assert 'serving_order_id' in drone, f"Drone {drone_id} missing serving_order_id"
        assert drone['serving_order_id'] is None, f"Drone {drone_id} serving_order_id should be None initially"
        assert 'cargo' in drone, f"Drone {drone_id} missing cargo"
        assert isinstance(drone['cargo'], set), f"Drone {drone_id} cargo should be a set"
    
    print("✓ All drones have serving_order_id and cargo initialized")
    
    print("\n2. Running initial consistency check...")
    issues = env.state_manager.get_state_consistency_check()
    print(f"Initial consistency issues: {len(issues)}")
    if issues:
        for issue in issues[:5]:  # Show first 5
            print(f"  - {issue}")
    
    print("\n3. Running 128 steps with random actions...")
    consistency_counts = []
    
    for step in range(128):
        # Random action for task selection
        action = np.random.uniform(-1, 1, (env.num_drones, 2))
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Check consistency every 16 steps
        if step % 16 == 0:
            issues = env.state_manager.get_state_consistency_check()
            consistency_counts.append(len(issues))
            
            # Categorize issues
            categories = {'Route': 0, 'TaskSel': 0, 'Legacy': 0, 'Other': 0}
            for issue in issues:
                if '[Route]' in issue:
                    categories['Route'] += 1
                elif '[TaskSel]' in issue:
                    categories['TaskSel'] += 1
                elif '[Legacy]' in issue:
                    categories['Legacy'] += 1
                else:
                    categories['Other'] += 1
            
            category_str = ", ".join([f"{k}={v}" for k, v in categories.items() if v > 0])
            print(f"[Step {step:3d}] Issues: {len(issues):3d} ({category_str if category_str else 'none'})")
        
        if terminated or truncated:
            print(f"\nEpisode ended at step {step}")
            break
    
    print("\n4. Summary:")
    print(f"   Average consistency issues: {np.mean(consistency_counts):.1f}")
    print(f"   Max consistency issues: {int(np.max(consistency_counts))}")
    print(f"   Min consistency issues: {int(np.min(consistency_counts))}")
    
    # Get final stats
    final_info = env._get_info()
    print(f"\n5. Episode Statistics:")
    print(f"   Orders completed: {env.daily_stats['orders_completed']}")
    print(f"   Orders cancelled: {env.daily_stats['orders_cancelled']}")
    print(f"   On-time deliveries: {env.daily_stats['on_time_deliveries']}")
    if env.daily_stats['orders_completed'] > 0:
        on_time_rate = env.daily_stats['on_time_deliveries'] / env.daily_stats['orders_completed']
        print(f"   On-time rate: {on_time_rate:.2%}")
    
    env.close()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    return consistency_counts

def test_cargo_invariants():
    """Test cargo invariants specifically."""
    print("\n" + "=" * 60)
    print("Testing Cargo Invariants")
    print("=" * 60)
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=6,
        max_orders=100,
        steps_per_hour=4,
        drone_max_capacity=10,
        reward_output_mode="zero",
        enable_random_events=False,
        debug_state_warnings=True,
        num_candidates=20,
    )
    
    obs, info = env.reset(seed=123)
    
    print("\nRunning 64 steps to generate orders and activity...")
    for step in range(64):
        action = np.random.uniform(-1, 1, (env.num_drones, 2))
        obs, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            break
    
    print("\nChecking cargo invariants...")
    invariant_violations = 0
    
    # Check invariant 1: PICKED_UP orders must be in cargo
    for order_id, order in env.orders.items():
        if order['status'].name == 'PICKED_UP':
            drone_id = order.get('assigned_drone', -1)
            if drone_id >= 0 and drone_id in env.drones:
                drone = env.drones[drone_id]
                if order_id not in drone.get('cargo', set()):
                    print(f"  ✗ VIOLATION: Order {order_id} PICKED_UP but not in drone {drone_id} cargo")
                    invariant_violations += 1
    
    # Check invariant 2: Cargo orders must be PICKED_UP
    for drone_id, drone in env.drones.items():
        cargo = drone.get('cargo', set())
        for order_id in cargo:
            if order_id in env.orders:
                order = env.orders[order_id]
                if order['status'].name != 'PICKED_UP':
                    print(f"  ✗ VIOLATION: Order {order_id} in drone {drone_id} cargo but status is {order['status'].name}")
                    invariant_violations += 1
                if order.get('assigned_drone') != drone_id:
                    print(f"  ✗ VIOLATION: Order {order_id} in drone {drone_id} cargo but assigned to drone {order.get('assigned_drone')}")
                    invariant_violations += 1
    
    if invariant_violations == 0:
        print("  ✓ All cargo invariants satisfied!")
    else:
        print(f"\n  Total violations: {invariant_violations}")
    
    env.close()
    
    print("=" * 60)
    
    return invariant_violations == 0

if __name__ == "__main__":
    # Run basic test
    consistency_counts = test_basic_environment()
    
    # Run cargo invariants test
    cargo_ok = test_cargo_invariants()
    
    # Summary
    print("\n" + "=" * 60)
    print("OVERALL RESULTS")
    print("=" * 60)
    
    avg_issues = np.mean(consistency_counts)
    max_issues = np.max(consistency_counts)
    
    print(f"Average consistency issues: {avg_issues:.1f}")
    print(f"Maximum consistency issues: {int(max_issues)}")
    print(f"Cargo invariants: {'✓ PASS' if cargo_ok else '✗ FAIL'}")
    
    # Success criteria
    if avg_issues < 5 and max_issues < 15 and cargo_ok:
        print("\n✓ SUCCESS: State consistency significantly improved!")
    elif avg_issues < 15:
        print("\n⚠ PARTIAL: Some improvement, but more work needed")
    else:
        print("\n✗ NEEDS WORK: Consistency issues still high")
    
    print("=" * 60)
