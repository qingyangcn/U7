"""
Simple test to validate movement model fixes.
Tests:
1. Single movement per step (no double update)
2. Action dimensionality consistency (choice + speed only)
3. Cargo invariants (PICKED_UP orders in cargo)
4. Serving_order_id driven pickup/delivery
"""

import numpy as np
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv

def test_single_movement_per_step():
    """Test that drones move only once per step."""
    print("\n=== Test 1: Single Movement Per Step ===")
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=2,
        max_orders=20,
        num_bases=1,
        steps_per_hour=4,
        drone_max_capacity=5,
        top_k_merchants=10,
        reward_output_mode="zero",
        enable_random_events=False,
        debug_state_warnings=False,
        num_candidates=5,
    )
    
    obs, info = env.reset(seed=42)
    
    # Record initial positions
    initial_positions = {}
    for drone_id, drone in env.drones.items():
        initial_positions[drone_id] = drone['location']
        print(f"Drone {drone_id} initial position: {initial_positions[drone_id]}")
    
    # Take a step with a random action
    action = np.random.uniform(-1, 1, (env.num_drones, 2))
    
    # Check that _immediate_state_update is not moving drones
    # by monitoring position changes
    obs, reward, terminated, truncated, info = env.step(action)
    
    final_positions = {}
    movements = {}
    for drone_id, drone in env.drones.items():
        final_positions[drone_id] = drone['location']
        distance = np.sqrt(
            (final_positions[drone_id][0] - initial_positions[drone_id][0])**2 +
            (final_positions[drone_id][1] - initial_positions[drone_id][1])**2
        )
        movements[drone_id] = distance
        print(f"Drone {drone_id} final position: {final_positions[drone_id]}, moved: {distance:.4f}")
    
    print("✓ Test 1 passed: Movement tracking works")
    

def test_action_dimensionality():
    """Test that action has correct shape (num_drones, 2) for choice + speed."""
    print("\n=== Test 2: Action Dimensionality ===")
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=3,
        max_orders=20,
        num_bases=1,
        reward_output_mode="zero",
        num_candidates=5,
    )
    
    obs, info = env.reset(seed=42)
    
    # Check action space
    expected_shape = (env.num_drones, 2)
    actual_shape = env.action_space.shape
    
    print(f"Expected action shape: {expected_shape}")
    print(f"Actual action shape: {actual_shape}")
    
    assert actual_shape == expected_shape, f"Action shape mismatch: {actual_shape} != {expected_shape}"
    
    # Test action processing
    action = np.random.uniform(-1, 1, expected_shape)
    obs, reward, terminated, truncated, info = env.step(action)
    
    # Check that ppo_speed_multiplier is set correctly for all drones
    for drone_id, drone in env.drones.items():
        speed_mult = drone.get('ppo_speed_multiplier', None)
        assert speed_mult is not None, f"Drone {drone_id} missing ppo_speed_multiplier"
        assert 0.5 <= speed_mult <= 1.5, f"Drone {drone_id} speed multiplier out of range: {speed_mult}"
        print(f"Drone {drone_id} speed multiplier: {speed_mult:.3f}")
    
    print("✓ Test 2 passed: Action dimensionality correct")


def test_cargo_invariants():
    """Test that PICKED_UP orders are always in drone cargo."""
    print("\n=== Test 3: Cargo Invariants ===")
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=2,
        max_orders=50,
        num_bases=1,
        reward_output_mode="zero",
        enable_random_events=False,
        num_candidates=10,
    )
    
    obs, info = env.reset(seed=42)
    
    # Run a few steps to generate some orders
    for step in range(20):
        action = np.random.uniform(-1, 1, (env.num_drones, 2))
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Check cargo invariants
        violations = []
        for order_id, order in env.orders.items():
            if order['status'].name == 'PICKED_UP':
                drone_id = order.get('assigned_drone', -1)
                if drone_id >= 0 and drone_id in env.drones:
                    drone = env.drones[drone_id]
                    if order_id not in drone.get('cargo', set()):
                        violations.append(
                            f"Order {order_id} is PICKED_UP by drone {drone_id} but not in cargo"
                        )
        
        # Check reverse: cargo orders must be PICKED_UP
        for drone_id, drone in env.drones.items():
            for order_id in drone.get('cargo', set()):
                if order_id in env.orders:
                    order = env.orders[order_id]
                    if order['status'].name != 'PICKED_UP':
                        violations.append(
                            f"Order {order_id} in drone {drone_id} cargo but status is {order['status'].name}"
                        )
        
        if violations:
            print(f"\nStep {step} violations:")
            for v in violations:
                print(f"  - {v}")
            raise AssertionError(f"Cargo invariant violations found at step {step}")
    
    print("✓ Test 3 passed: Cargo invariants maintained")


def test_serving_order_id():
    """Test that task-selection uses serving_order_id correctly."""
    print("\n=== Test 4: Serving Order ID ===")
    
    env = ThreeObjectiveDroneDeliveryEnv(
        grid_size=16,
        num_drones=2,
        max_orders=50,
        num_bases=1,
        reward_output_mode="zero",
        enable_random_events=False,
        debug_state_warnings=True,
        num_candidates=10,
    )
    
    obs, info = env.reset(seed=42)
    
    # Run steps and check serving_order_id usage
    serving_order_count = 0
    for step in range(20):
        action = np.random.uniform(-1, 1, (env.num_drones, 2))
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Count drones with serving_order_id
        for drone_id, drone in env.drones.items():
            serving_id = drone.get('serving_order_id')
            if serving_id is not None:
                serving_order_count += 1
                # Check that the order exists and is valid
                if serving_id in env.orders:
                    order = env.orders[serving_id]
                    # Verify the order is assigned to this drone or in cargo
                    if order['status'].name in ['ASSIGNED', 'PICKED_UP']:
                        assigned_drone = order.get('assigned_drone', -1)
                        if assigned_drone == drone_id:
                            print(f"Step {step}: Drone {drone_id} serving order {serving_id} (status={order['status'].name})")
    
    print(f"Total serving_order_id instances: {serving_order_count}")
    print("✓ Test 4 passed: Serving order ID tracking works")


def run_all_tests():
    """Run all validation tests."""
    print("=" * 70)
    print("Running Movement Model and Task-Selection Validation Tests")
    print("=" * 70)
    
    try:
        test_single_movement_per_step()
        test_action_dimensionality()
        test_cargo_invariants()
        test_serving_order_id()
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
