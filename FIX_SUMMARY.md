# PPO+MOPSO Training Collapse Fix - Summary

## Problem Statement

When running PPO+MOPSO training with `enable_legacy_fallback=False` and `fallback_policy=cargo_first`, daily results collapse:
- Completed only 33/1324 orders
- Cancelled 1201 orders
- On-time deliveries: 1
- "Legacy fallback blocked" printed 391 times

## Root Causes Identified

1. **Candidate Mapping Too Restrictive**: The `_build_candidate_list_for_drone` function only included orders already ASSIGNED to the drone or in its cargo. PPO could not select from the broader pool of READY orders.

2. **No Assignment Mechanism in PPO Actions**: When PPO selected a candidate, if it was a READY order, the environment didn't assign it - it only worked with already-ASSIGNED orders.

3. **Insufficient Diagnostics**: Limited visibility into what was happening during training made debugging difficult.

## Fixes Implemented

### A) Expanded Candidate Mapping

**File**: `UAV_ENVIRONMENT_7.py`

The `_build_candidate_list_for_drone` function now includes three categories of candidates:

1. **PICKED_UP orders** (in drone cargo) - highest priority
2. **ASSIGNED orders** (assigned to this drone but not picked up)
3. **READY orders** (available for assignment) - NEW!

This ensures drones always have valid candidates to choose from when there is work available.

### B) PPO Can Assign READY Orders

**File**: `UAV_ENVIRONMENT_7.py`, `_process_action` method

When PPO selects a READY order as a candidate, the environment now:
1. Assigns the order to the drone using `_process_single_assignment`
2. Sets the appropriate target location (merchant for pickup)
3. Updates drone status to FLYING_TO_MERCHANT

This allows PPO to directly participate in order assignment, not just order execution.

### C) Added Comprehensive Diagnostics

**Environment Diagnostics** (`UAV_ENVIRONMENT_7.py`):
- `enable_diagnostics`: Enable detailed diagnostics (default: False)
- `diagnostics_interval`: Print diagnostics every N steps (default: 100)
- Tracks:
  - Drones with serving_order_id
  - Drones at decision points
  - Drones with valid candidates (total, cargo, assigned)
  - Actions applied per step
  - Legacy blocked count and reasons

**Wrapper Diagnostics** (`U7_train.py`):
- Tracks PPO invalid choices
- Fallback usage statistics
- No valid candidate count
- Cargo-first policy application rate

### D) Enhanced Legacy Fallback Tracking

**File**: `UAV_ENVIRONMENT_7.py`

Now tracks reasons for legacy fallback blocking:
- `has_serving_order_id`
- `has_planned_stops`
- `status_IDLE`, `status_FLYING_TO_MERCHANT`, etc.

This helps diagnose why legacy fallback is being blocked and whether it's appropriate.

## Usage

### Training with Fix (Legacy Disabled)

```bash
python U7_train.py \
  --num-drones 50 \
  --obs-max-orders 400 \
  --total-steps 200000 \
  --fallback-policy cargo_first \
  --enable-diagnostics \
  --diagnostics-interval 100 \
  --debug-stats-interval 100
```

Key flags:
- `--enable-legacy-fallback`: Disabled by default (for testing PPO+MOPSO without legacy)
- `--enable-diagnostics`: Enable environment diagnostics
- `--diagnostics-interval N`: Print environment diagnostics every N steps
- `--debug-stats-interval N`: Print wrapper stats every N steps
- `--fallback-policy`: Choose `cargo_first`, `first_valid`, or `none`

### Training with Legacy Enabled (Backward Compatible)

```bash
python U7_train.py \
  --num-drones 50 \
  --obs-max-orders 400 \
  --total-steps 200000 \
  --enable-legacy-fallback \
  --fallback-policy cargo_first
```

## Expected Results

With the fix:

1. **Hundreds of completed orders** (not tens) - PPO can now select from READY orders
2. **Near-zero legacy blocked count** - PPO handles most situations, legacy fallback rarely needed
3. **Clear diagnostics** showing:
   - Most drones have valid candidates
   - Actions being applied at decision points
   - Fallback policy working when needed

## Backward Compatibility

- Legacy fallback flag preserved (`enable_legacy_fallback`)
- Diagnostics disabled by default
- Existing code continues to work
- Default behavior changed: legacy fallback now OFF by default for testing PPO+MOPSO

## Files Modified

1. `UAV_ENVIRONMENT_7.py`:
   - Added `enable_diagnostics`, `diagnostics_interval` parameters
   - Expanded `_build_candidate_list_for_drone` to include READY orders
   - Modified `_process_action` to handle READY order assignment
   - Added `_print_diagnostics` method
   - Enhanced legacy blocking tracking with reasons

2. `U7_train.py`:
   - Added `--enable-legacy-fallback` flag
   - Added `--enable-diagnostics` flag
   - Added `--diagnostics-interval` flag
   - Enhanced wrapper statistics tracking
   - Improved debug stats output

## Testing

1. **Unit Tests**: Run `test_fix.py` to verify:
   - Candidate mapping includes READY orders
   - Diagnostics flags work correctly
   - PPO can assign READY orders

2. **Integration Test**: Run short training:
   ```bash
   python U7_train.py --total-steps 10000 --enable-diagnostics --diagnostics-interval 50
   ```

3. **Full Training**: Run full training and check:
   - Completed orders > 200
   - Legacy blocked count < 10
   - Diagnostics show healthy operation

## Next Steps

1. Run full training with diagnostics enabled
2. Analyze diagnostics output to verify the fix
3. Compare results with/without legacy fallback
4. Fine-tune parameters based on results
5. Run code review and security scans
