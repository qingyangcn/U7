# U7

## U7 Drone Delivery Environment

This repository contains the U7 environment for multi-objective drone delivery optimization with task selection and assignment.

## Key Features

### Legacy Fallback Control

The environment includes a `enable_legacy_fallback` flag to control legacy fallback behavior:

- **Default**: `True` - Legacy fallback is **enabled** by default for backward compatibility with existing training scripts
- **When enabled**: Drones can execute assigned orders using legacy pickup/delivery paths (required for MOPSO+PPO workflows)
- **When disabled**: Only useful for route-plan mode where `planned_stops` are explicitly set

**Important**: The default is `True` because MOPSO assignment + PPO task selection workflows rely on legacy execution paths. Only disable if using explicit route planning with `planned_stops`.

#### Usage

```python
# Standard MOPSO+PPO workflow (default, recommended)
env = ThreeObjectiveDroneDeliveryEnv(
    enable_legacy_fallback=True,  # Default - required for assignment+task-selection
)

# Route-plan mode only (experimental)
env = ThreeObjectiveDroneDeliveryEnv(
    enable_legacy_fallback=False,  # Only for explicit route planning
    debug_state_warnings=True,      # Show when legacy would have triggered
)
```

#### Diagnostics

When legacy fallback is disabled:
- The environment tracks how many times legacy fallback would have been triggered
- This count is available in:
  - `info['legacy_blocked_count']` in each step
  - End-of-day statistics
  - Episode info dict

With `debug_state_warnings=True`, you'll see detailed logs when legacy paths are blocked:
```
[Legacy Blocked] Drone 5 arrival at FLYING_TO_MERCHANT - serving_order_id=None, total_blocked=1
```

**Note**: High `legacy_blocked_count` with poor performance indicates you should keep `enable_legacy_fallback=True`.

### Baseline Heuristics

The `baseline_heuristics.py` script provides clean comparison baselines for evaluating RL policies:

#### Available Policies

1. **random-random**: Random assignment + random action selection
2. **random-cargo**: Random assignment + cargo-first action (prioritize delivery)
3. **greedy-cargo**: Greedy assignment (nearest drone) + cargo-first action
4. **edf-cargo**: EDF assignment (earliest deadline first) + cargo-first action

#### Usage

```bash
# Run a specific policy
python baseline_heuristics.py --policy greedy-cargo --episodes 10 --seed 42

# Run all policies
python baseline_heuristics.py --policy all --episodes 5

# Help
python baseline_heuristics.py --help
```

#### Output Metrics

For each policy, the script reports:
- **Completion rate**: Orders completed / Orders generated
- **On-time rate**: On-time deliveries / Orders completed
- **Average completed orders**: Mean and std dev across episodes
- **Legacy blocked count**: Number of times legacy fallback was blocked (should be 0 with clean policies)

Example output:
```
============================================================
Running baseline: greedy-cargo
Episodes: 5, Seed: 42
============================================================

Episode 1/5: completion_rate=0.856, on_time_rate=0.723, completed=234, generated=273, legacy_blocked=0
Episode 2/5: completion_rate=0.841, on_time_rate=0.701, completed=227, generated=270, legacy_blocked=0
...

============================================================
Summary for greedy-cargo:
  Completion rate: 0.849 ± 0.012
  On-time rate:    0.712 ± 0.015
  Avg completed:   230.2 ± 4.3
============================================================
```

## Training

See existing training scripts:
- `U7_train.py`: PPO training with MOPSO assignment
- `U7_eval_ppo.py`: Evaluation of trained PPO policies

## Environment Parameters

Key parameters for the `ThreeObjectiveDroneDeliveryEnv`:

- `grid_size`: Grid size (default: 16)
- `num_drones`: Number of drones (default: 6)
- `max_orders`: Maximum observable orders (default: 100)
- `enable_legacy_fallback`: Enable legacy fallback behavior (default: False)
- `debug_state_warnings`: Enable detailed state consistency warnings (default: False)
- `enable_random_events`: Enable random events like weather changes (default: True)
- `num_candidates`: Number of candidate orders for task selection (default: 20)
- `delivery_sla_steps`: Delivery SLA in steps (default: 3)
- `timeout_factor`: Deadline multiplier (default: 4.0)
