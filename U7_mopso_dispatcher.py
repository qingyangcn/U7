"""
U7 MOPSO Dispatcher: Assignment-only (no route planning).

This dispatcher uses MOPSO to assign READY orders to drones,
but does NOT generate planned_stops. PPO handles task selection and routing.

Key differences from U6:
- Only assigns orders to drones (READY -> ASSIGNED)
- Does not create planned_stops
- Respects capacity constraints
- Uses existing MOPSO logic for assignment optimization
"""
import math
import numpy as np
from typing import Dict, List, Tuple, Optional

# NOTE: This module depends on U6_mopso_dispatcher for the core MOPSO optimization logic.
# We reuse MOPSOPlanner's _run_mopso method to avoid code duplication while changing
# only the assignment application (no route planning in U7).
from U6_mopso_dispatcher import MOPSOPlanner

# Import OrderStatus from environment for proper enum usage
try:
    from UAV_ENVIRONMENT_7 import OrderStatus
except ImportError:
    # Fallback if import fails
    OrderStatus = None


class U7MOPSOAssigner:
    """
    Assignment-only MOPSO dispatcher for U7.

    Uses MOPSO to optimize order-to-drone assignment without
    generating route plans. PPO handles task selection.
    """

    def __init__(self,
                 n_particles: int = 30,
                 n_iterations: int = 10,
                 max_orders: int = 200,
                 max_orders_per_drone: int = 10,
                 seed: Optional[int] = None,
                 # Task 3: New parameters for assignment policy
                 prioritize_idle: bool = True,
                 allow_busy_fallback: bool = False,
                 **mopso_kwargs):
        """
        Initialize U7 MOPSO assigner.

        Args:
            n_particles: Number of PSO particles
            n_iterations: PSO iterations
            max_orders: Maximum orders to consider
            max_orders_per_drone: Maximum orders per drone (capacity constraint)
            seed: Random seed
            prioritize_idle: If True, use two-pass assignment (IDLE first, then busy)
            allow_busy_fallback: If True, allow assignment to busy drones in second pass
            **mopso_kwargs: Additional arguments for MOPSOPlanner
        """
        # Reuse the existing MOPSO planner but only use assignment logic
        self.planner = MOPSOPlanner(
            n_particles=n_particles,
            n_iterations=n_iterations,
            max_orders=max_orders,
            max_orders_per_drone=max_orders_per_drone,
            seed=seed,
            **mopso_kwargs
        )
        # Task 3: Assignment policy parameters
        self.prioritize_idle = prioritize_idle
        self.allow_busy_fallback = allow_busy_fallback

    def assign_orders(self, env,
                     ready_orders: Optional[List[dict]] = None,
                     drones: Optional[List[dict]] = None,
                     merchants: Optional[Dict] = None,
                     constraints: Optional[dict] = None,
                     objective_weights: Optional[np.ndarray] = None) -> Dict[int, List[int]]:
        """
        Assign READY orders to drones using MOPSO.

        Task 3: Implements two-pass assignment policy:
        - First pass: Assign only to IDLE drones with capacity
        - Second pass (optional): If enabled and many READY remain, allow busy drones

        Args:
            env: Environment instance
            ready_orders: List of ready order snapshots
            drones: List of drone snapshots
            merchants: Dict of merchant snapshots
            constraints: Constraint parameters
            objective_weights: Weights for solution selection

        Returns:
            Assignment dict: {drone_id: [order_ids]}
        """
        # Get snapshots if not provided
        if ready_orders is None:
            ready_orders = env.get_ready_orders_snapshot(limit=self.planner.max_orders)
        if drones is None:
            drones = env.get_drones_snapshot()
        if merchants is None:
            merchants = env.get_merchants_snapshot()
        if constraints is None:
            constraints = env.get_route_plan_constraints()
        if objective_weights is None:
            objective_weights = getattr(env, 'objective_weights', np.array([0.33, 0.33, 0.34]))

        # Task 3: First pass - prioritize IDLE drones
        if self.prioritize_idle:
            # Import DroneStatus to check status
            try:
                from UAV_ENVIRONMENT_7 import DroneStatus
            except ImportError:
                DroneStatus = None

            # First pass: IDLE drones only
            idle_drones = []
            for d in drones:
                current_load = d.get('current_load', 0)
                max_capacity = d.get('max_capacity', 10)
                if current_load >= max_capacity:
                    continue
                
                # Check if drone is IDLE
                status = d.get('status')
                if DroneStatus is not None:
                    is_idle = (status == DroneStatus.IDLE)
                else:
                    # Fallback: assume status 0 is IDLE
                    is_idle = (status.value == 0 if hasattr(status, 'value') else status == 0)
                
                if is_idle:
                    idle_drones.append(d)

            if idle_drones and ready_orders:
                # Limit orders to max_orders
                ready_orders_limited = ready_orders[:self.planner.max_orders]
                
                # Run MOPSO with IDLE drones only
                assignment = self.planner._run_mopso(
                    ready_orders_limited, idle_drones, merchants, constraints, objective_weights
                )
                
                # If we got good coverage or fallback is disabled, return
                if not self.allow_busy_fallback or not assignment:
                    return assignment
                
                # Count how many orders were assigned
                assigned_count = sum(len(orders) for orders in assignment.values())
                remaining_count = len(ready_orders_limited) - assigned_count
                
                # If less than 30% remain unassigned, skip busy fallback
                if remaining_count < len(ready_orders_limited) * 0.3:
                    return assignment
                
                # Otherwise, proceed to second pass with remaining orders
                assigned_order_ids = set()
                for order_list in assignment.values():
                    assigned_order_ids.update(order_list)
                
                remaining_orders = [o for o in ready_orders_limited 
                                  if o['order_id'] not in assigned_order_ids]
                
                # Second pass: allow busy drones
                busy_drones = []
                for d in drones:
                    current_load = d.get('current_load', 0)
                    max_capacity = d.get('max_capacity', 10)
                    if current_load >= max_capacity:
                        continue
                    
                    # Include non-IDLE drones with capacity
                    status = d.get('status')
                    if DroneStatus is not None:
                        is_idle = (status == DroneStatus.IDLE)
                    else:
                        is_idle = (status.value == 0 if hasattr(status, 'value') else status == 0)
                    
                    if not is_idle:
                        busy_drones.append(d)
                
                if busy_drones and remaining_orders:
                    # Run MOPSO for remaining orders with busy drones
                    busy_assignment = self.planner._run_mopso(
                        remaining_orders, busy_drones, merchants, constraints, objective_weights
                    )
                    
                    # Merge assignments
                    for drone_id, order_ids in busy_assignment.items():
                        if drone_id in assignment:
                            assignment[drone_id].extend(order_ids)
                        else:
                            assignment[drone_id] = order_ids
                
                return assignment
            
            # If no IDLE drones but fallback enabled, fall through to old logic
            if not self.allow_busy_fallback:
                return {}

        # Old logic: Include drones that have capacity, regardless of status
        # Used when prioritize_idle=False or as fallback
        available_drones = []
        for d in drones:
            current_load = d.get('current_load', 0)
            max_capacity = d.get('max_capacity', 10)
            if current_load < max_capacity:
                available_drones.append(d)

        if not available_drones or not ready_orders:
            return {}

        # Limit orders to max_orders
        ready_orders = ready_orders[:self.planner.max_orders]

        # Run MOPSO to get assignment
        assignment = self.planner._run_mopso(
            ready_orders, available_drones, merchants, constraints, objective_weights
        )

        return assignment


def apply_mopso_assignment(env, assigner: Optional[U7MOPSOAssigner] = None, **kwargs) -> Dict[int, int]:
    """
    Apply MOPSO assignment to environment (assignment only, no route planning).

    Task 3: This function only assigns READY orders to drones (READY -> ASSIGNED).
    It does NOT create planned_stops. PPO handles task selection and routing.

    The assignment follows the configured policy (see U7MOPSOAssigner parameters):
    - prioritize_idle=True (default): First assign to IDLE drones, optionally fallback to busy
    - allow_busy_fallback=False (default): Do not assign to busy drones at all

    Args:
        env: Environment instance
        assigner: U7MOPSOAssigner instance (created if None)
        **kwargs: Additional arguments for assigner (e.g., prioritize_idle, allow_busy_fallback)

    Returns:
        Dict mapping drone_id to count of newly assigned orders
    """
    if assigner is None:
        assigner = U7MOPSOAssigner(**kwargs)

    # Get assignment from MOPSO
    assignment = assigner.assign_orders(env)

    # Apply assignments to environment
    assignment_counts = {}
    total_assigned = 0

    for drone_id, order_ids in assignment.items():
        if not order_ids:
            continue

        drone = env.drones.get(drone_id)
        if not drone:
            continue

        # Check capacity
        current_load = drone.get('current_load', 0)
        max_capacity = drone.get('max_capacity', 10)
        available_capacity = max_capacity - current_load

        if available_capacity <= 0:
            continue

        # Assign orders up to capacity
        assigned_count = 0
        for order_id in order_ids[:available_capacity]:
            order = env.orders.get(order_id)
            if not order:
                continue

            # Only assign READY orders - use proper enum comparison if available
            if OrderStatus is not None:
                if order['status'] != OrderStatus.READY:
                    continue
            else:
                if order['status'].name != 'READY':
                    continue

            # Check if already assigned
            if order.get('assigned_drone') not in (None, -1):
                continue

            # Assign order using environment's internal method
            # Use _process_single_assignment if available, otherwise manual assignment
            if hasattr(env, '_process_single_assignment'):
                try:
                    env._process_single_assignment(drone_id, order_id, allow_busy=True)
                    assigned_count += 1
                except Exception as e:
                    # Fallback to manual assignment if _process_single_assignment fails
                    # This can happen if the environment state is inconsistent
                    import warnings
                    warnings.warn(f"Failed to use _process_single_assignment for order {order_id}: {e}. "
                                 f"Falling back to manual assignment.")
                    # Use imported OrderStatus if available, otherwise get from env
                    assigned_status = OrderStatus.ASSIGNED if OrderStatus else env.OrderStatus.ASSIGNED
                    env.state_manager.update_order_status(order_id, assigned_status)
                    order['assigned_drone'] = drone_id
                    drone['current_load'] += 1
                    assigned_count += 1
            else:
                # Manual assignment
                assigned_status = OrderStatus.ASSIGNED if OrderStatus else env.OrderStatus.ASSIGNED
                env.state_manager.update_order_status(order_id, assigned_status)
                order['assigned_drone'] = drone_id
                drone['current_load'] += 1
                assigned_count += 1

        if assigned_count > 0:
            assignment_counts[drone_id] = assigned_count
            total_assigned += assigned_count

    return assignment_counts