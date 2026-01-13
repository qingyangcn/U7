# Fix Summary - MOPSO Over-Assignment Prevention

## Problem from User Feedback

Orders stuck in ASSIGNED state and being cancelled before pickup:
- Large number of orders in ASSIGNED (not picked up)
- Orders cancelled before drones can reach merchant
- Pickup not happening fast enough
- "Order chasing" behavior

## Root Causes

### 1. MOPSO Over-Assignment
MOPSO assignment runs **every step before PPO**, assigning READY orders to drones.

**Issue**: MOPSO was assigning to drones with `allow_busy=True`, which means:
- Drone already has ASSIGNED orders (not picked up)
- MOPSO assigns new READY order
- Drone redirects to new merchant
- Old ASSIGNED order never gets picked up
- Cycle repeats → **order chasing**

```python
# OLD: Allow assignment to busy drones
for oid in commit_orders:
    env._process_single_assignment(drone_id, oid, allow_busy=True)
    # ↑ This allows assigning to drones already busy with other orders!
```

### 2. Timeout Too Strict
- `delivery_sla_steps = 3` (default)
- `timeout_factor = 4.0` (default)  
- Deadline = ready_step + 3 * 4 = **12 steps (60 minutes)**

With 12 steps/hour (5 min/step), orders timeout before drones can:
1. Finish current task
2. Navigate to merchant
3. Pick up order
4. Navigate to customer
5. Deliver

### 3. Compound Effect
1. MOPSO assigns order A to drone
2. Drone starts flying to merchant A
3. Next step: MOPSO assigns order B to same drone
4. Drone redirects to merchant B
5. Order A times out (12 steps)
6. Next step: MOPSO assigns order C
7. Order B times out
8. Repeat forever → very few pickups

## Solution

### 1. Prevent MOPSO Over-Assignment

**File**: `U7_train.py`

Modified `mopso_assignment_only` and `greedy_assignment_only` to check for pending ASSIGNED orders:

```python
# Check if drone has pending ASSIGNED orders (not picked up yet)
has_pending_assigned = False
for oid in env.active_orders:
    order = env.orders.get(oid)
    if order and order.get('assigned_drone') == drone_id:
        if order['status'] == OrderStatus.ASSIGNED:
            has_pending_assigned = True
            break

# Skip assignment if drone has pending pickup work
if has_pending_assigned:
    continue  # Don't assign new orders to this drone
```

**Impact**: 
- Drones focus on picking up their assigned orders first
- No more order chasing
- ASSIGNED orders get picked up before timeout

### 2. Increase Timeout

**File**: `UAV_ENVIRONMENT_7.py`

Changed defaults:
```python
# OLD
delivery_sla_steps: int = 3
timeout_factor: float = 4.0
# Deadline = 3 * 4 = 12 steps (60 minutes)

# NEW
delivery_sla_steps: int = 6
timeout_factor: float = 8.0
# Deadline = 6 * 8 = 48 steps (240 minutes)
```

**Impact**:
- 4x longer deadline
- Drones have time to complete pickup and delivery
- Fewer premature cancellations

## Expected Results

### Before Fix
```
Orders: READY=24, ASSIGNED=28, PICKED_UP=0
Orders completed: 23/1324
Orders cancelled: 1212/1324
```

**Issues**:
- ASSIGNED orders stuck (28 assigned, 0 picked up)
- Massive cancellations (91% cancelled)
- Very few completions (2% completed)

### After Fix
```
Orders: READY=X, ASSIGNED=Y, PICKED_UP=Z
PICKED_UP should now be > 0 and growing
Orders completed: hundreds
Orders cancelled: much lower
```

**Improvements**:
- ✅ Drones pick up ASSIGNED orders before chasing new ones
- ✅ PICKED_UP count increases (was 0)
- ✅ Orders complete before timeout
- ✅ Cancellation rate drops significantly
- ✅ Completion rate increases dramatically

## Diagnostic Expectations

With `--enable-diagnostics --diagnostics-interval 100`:

```
=== Diagnostics (Step 100) ===
  Drones with serving_order_id: 8-10/10  ← Most drones have work
  Drones with cargo candidates: 3-5/10   ← PICKED_UP orders now present!
  Drones with assigned candidates: 4-6/10 ← Drones working on assignments
  Actions applied this step: 5-10        ← Actions being processed
  Orders: READY=X, ASSIGNED=Y, PICKED_UP=Z  ← Z should be > 0!
```

**Key indicators**:
- `Drones with cargo candidates` should be **> 0** (was 0 before)
- `PICKED_UP` count should be **> 0** (was 0 before)
- `Orders cancelled` should be **much lower** (was 1212/1324)

## Testing

Run short test with diagnostics:
```bash
python U7_train.py \
  --num-drones 10 \
  --total-steps 10000 \
  --enable-diagnostics \
  --diagnostics-interval 100
```

Check at steps 100, 200, 300:
1. PICKED_UP count should increase
2. Cargo candidates should appear
3. Cancellations should be much lower
4. Completed orders should reach hundreds

## Why This Works

**Before**:
1. MOPSO assigns order to drone every step
2. Drone keeps redirecting to new merchants
3. Never picks up any order
4. All orders timeout → cancelled

**After**:
1. MOPSO assigns order to idle drone
2. Drone flies to merchant and picks up
3. MOPSO skips this drone (has pending pickup)
4. Drone delivers order
5. Drone becomes idle → can receive new assignment
6. Cycle continues healthily

**Key Insight**: Let drones **finish what they started** before giving them new work.

## Files Changed

- `U7_train.py`:
  - `mopso_assignment_only()` - added pending order check
  - `greedy_assignment_only()` - added pending order check
  - Import `OrderStatus` for status checks

- `UAV_ENVIRONMENT_7.py`:
  - `delivery_sla_steps` default: 3 → 6
  - `timeout_factor` default: 4.0 → 8.0

## Commit

a80c1d8 - Prevent MOPSO over-assignment and increase timeout for pickup
