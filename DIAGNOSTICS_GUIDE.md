# Quick Start Guide - Diagnostics

## Running the Diagnostics

### Simple Test
```bash
python3 test_diagnostics.py
```

This runs a short 64-step episode with diagnostics enabled and prints a summary.

### In Your Own Code

```python
from UAV_ENVIRONMENT_7 import ThreeObjectiveDroneDeliveryEnv

env = ThreeObjectiveDroneDeliveryEnv(
    debug_diagnostics=True,      # Enable diagnostic tracking
    debug_state_warnings=True,   # Print detailed warnings
    # ... other parameters ...
)

obs, info = env.reset(seed=42)

# Run episode
for step in range(max_steps):
    action = your_policy(obs)
    obs, reward, terminated, truncated, info = env.step(action)
    
    if terminated:
        # Diagnostics are automatically printed at episode end
        break
```

### What Gets Tracked

1. **Movement Paths** - Counts how many times each movement update method is called
2. **Arrival Handlers** - Tracks which task assignment mode is used
3. **State Repairs** - Counts auto-pickup, auto-complete, and reset operations
4. **Order Preparation** - Shows which READY transition path is used
5. **Order Status** - Snapshots every 64 steps showing order counts by status

### Expected Output

At the end of each episode, you'll see:
```
======================================================================
DIAGNOSTIC SUMMARY - Episode Ended
======================================================================

[1] Movement/Position Update Paths:
  - Immediate position updates:    64
  - Event-based position updates:  64
  ⚠️  ISSUE: Both immediate and event-based movement paths active!
     This can cause drones to move twice per step...

[2] Arrival Handler Branch Usage:
  - Route-plan mode arrivals:      0
  - Task-selection mode arrivals:  0
  - Legacy mode arrivals:          0

[3] State Synchronization Repairs:
  - Auto ASSIGNED->PICKED_UP:      0
  - Force-complete orders:         0
  - Reset-to-READY orders:         0
  ...

[4] Order Preparation/READY Transition Paths:
  - Immediate prep transitions:    421
  - Event-based prep transitions:  0

[5] Order Status Snapshot Summary:
  - Snapshots collected: 1
  - First snapshot (step 64): {'READY': 62, 'CANCELLED': 359, ...}
  ...
```

### Interpreting Results

**⚠️ Warnings indicate real problems:**
- "Both immediate and event-based movement paths active" → Drones moving twice per step
- "Multiple arrival handler modes used" → Conflicting task assignment logic
- "State repairs performed" → Auto-pickup/complete making evaluation unreliable
- "No READY orders observed" → Orders not transitioning correctly

### Disabling Diagnostics

For production or if you don't need diagnostics:
```python
env = ThreeObjectiveDroneDeliveryEnv(
    debug_diagnostics=False,  # Default is False
    # ... other parameters ...
)
```

This has zero overhead - no counters, no snapshots, no summary.

## For More Details

See **LOGIC_ISSUES_AUDIT.md** for:
- Complete description of each issue
- Line number references
- Recommended fixes
- Code examples
