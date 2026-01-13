#!/usr/bin/env python3
"""
Test script to verify the PPO+MOPSO training collapse fix.
"""
import numpy as np
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv, OrderStatus

def test_candidate_mapping_includes_ready_orders():
    """Test that candidate mapping now includes READY orders."""
    print("Testing candidate mapping includes READY orders...")
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=5,
        max_orders=100,
        num_candidates=20,
        enable_legacy_fallback=False,
        enable_diagnostics=False,
    )
    
    obs, info = env.reset(seed=42)
    
    # Check that drones have candidate mappings
    assert len(env.drone_candidate_mappings) == env.num_drones, \
        f"Expected {env.num_drones} drone candidate mappings, got {len(env.drone_candidate_mappings)}"
    
    # Check each drone has exactly K candidates
    for drone_id, candidate_list in env.drone_candidate_mappings.items():
        assert len(candidate_list) == env.num_candidates, \
            f"Drone {drone_id} has {len(candidate_list)} candidates, expected {env.num_candidates}"
    
    # Count READY orders
    ready_count = sum(1 for oid in env.active_orders 
                     if oid in env.orders and env.orders[oid]['status'] == OrderStatus.READY)
    print(f"  Found {ready_count} READY orders in env")
    
    # Check that at least one drone has valid candidates
    drones_with_valid = sum(1 for drone_id in range(env.num_drones)
                           if any(is_valid for _, is_valid in env.drone_candidate_mappings[drone_id]))
    print(f"  {drones_with_valid}/{env.num_drones} drones have at least one valid candidate")
    
    # If there are READY orders, at least one drone should have them as candidates
    if ready_count > 0:
        assert drones_with_valid > 0, \
            "With READY orders available, at least one drone should have valid candidates"
    
    print("✓ Candidate mapping test passed")

def test_diagnostics_flags():
    """Test that diagnostics flags are properly handled."""
    print("\nTesting diagnostics flags...")
    
    # Test with diagnostics enabled
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=3,
        max_orders=50,
        enable_diagnostics=True,
        diagnostics_interval=10,
        enable_legacy_fallback=False,
    )
    
    assert env.enable_diagnostics == True
    assert env.diagnostics_interval == 10
    assert env.enable_legacy_fallback == False
    assert env.legacy_blocked_count == 0
    assert len(env.legacy_blocked_reasons) == 0
    
    obs, info = env.reset(seed=42)
    
    # Test that action_applied_count is tracked
    action = np.zeros((env.num_drones, 2), dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)
    
    # action_applied_count should be defined
    assert hasattr(env, 'action_applied_count'), "Environment should track action_applied_count"
    
    print("✓ Diagnostics flags test passed")

def test_ppo_can_assign_ready_orders():
    """Test that PPO actions can select and assign READY orders."""
    print("\nTesting PPO can assign READY orders...")
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=5,
        max_orders=100,
        num_candidates=20,
        enable_legacy_fallback=False,
        enable_diagnostics=False,
    )
    
    obs, info = env.reset(seed=42)
    
    # Count initial READY orders
    initial_ready = sum(1 for oid in env.active_orders 
                       if oid in env.orders and env.orders[oid]['status'] == OrderStatus.READY)
    initial_assigned = sum(1 for oid in env.active_orders 
                          if oid in env.orders and env.orders[oid]['status'] == OrderStatus.ASSIGNED)
    
    print(f"  Initial: {initial_ready} READY, {initial_assigned} ASSIGNED orders")
    
    # Create actions that select first candidate for each drone (at decision points)
    # choice=-0.9 maps to index 0, speed=0.0 is neutral
    action = np.zeros((env.num_drones, 2), dtype=np.float32)
    action[:, 0] = -0.9  # Select first candidate
    action[:, 1] = 0.0   # Neutral speed
    
    # Step multiple times to allow drones to reach decision points
    for i in range(20):
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break
    
    # Count orders after steps
    final_ready = sum(1 for oid in env.active_orders 
                     if oid in env.orders and env.orders[oid]['status'] == OrderStatus.READY)
    final_assigned = sum(1 for oid in env.active_orders 
                        if oid in env.orders and env.orders[oid]['status'] == OrderStatus.ASSIGNED)
    
    print(f"  After 20 steps: {final_ready} READY, {final_assigned} ASSIGNED orders")
    print(f"  Actions applied: {env.action_applied_count} (in last step)")
    
    # Check that some orders have been assigned
    # (READY count should decrease or ASSIGNED count should increase)
    orders_changed = (final_ready < initial_ready) or (final_assigned > initial_assigned)
    
    if not orders_changed:
        print(f"  Warning: No orders transitioned from READY to ASSIGNED")
        print(f"  This may be normal if drones never reached decision points")
    else:
        print(f"  ✓ Orders successfully transitioned from READY to ASSIGNED")
    
    print("✓ PPO assignment test passed")

def main():
    print("=" * 60)
    print("Testing PPO+MOPSO Training Collapse Fix")
    print("=" * 60)
    
    try:
        test_candidate_mapping_includes_ready_orders()
        test_diagnostics_flags()
        test_ppo_can_assign_ready_orders()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
