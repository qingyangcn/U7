# U8 PPO Training: Task Selection Only

## Overview

This version (U8) simplifies the PPO training by removing speed control from the action space. PPO now only performs task selection (choosing which order to handle next), while speed is controlled by a fixed multiplier.

## Changes from U7

### Action Space
- **U7**: `Box(shape=(num_drones, 2))` - task selection + speed control
- **U8**: `Box(shape=(num_drones,))` - task selection only

### Speed Control
- **U7**: Speed multiplier controlled by action component `action[d, 1]` mapped to [0.5, 1.5]
- **U8**: Fixed speed multiplier = 1.0 (constant `FIXED_SPEED_MULTIPLIER`)

### Movement
- **U7**: Heading guidance with configurable alpha blend between PPO and target
- **U8**: Direct navigation to target (simplified)

## Benefits

1. **Simpler Learning**: Reduced action space dimensionality from 2D to 1D per drone
2. **Decoupled Tasks**: Task selection and speed control are no longer coupled
3. **Faster Training**: Smaller action space may lead to faster convergence
4. **Easier Tuning**: Speed can be adjusted via constant without retraining

## Configuration

The fixed speed multiplier is defined in `UAV_ENVIRONMENT_8.py`:

```python
# ===== Fixed speed multiplier (U8: no longer controlled by PPO) =====
FIXED_SPEED_MULTIPLIER = 1.0  # Fixed speed multiplier for all drones
```

To change the speed behavior, simply modify this constant and restart training.

## Usage

```bash
# Basic training
python U8_train.py --total-steps 200000 --seed 42

# With custom parameters
python U8_train.py \
  --num-drones 50 \
  --obs-max-orders 400 \
  --candidate-k 20 \
  --fallback-policy cargo_first \
  --total-steps 500000
```

## Testing

The changes have been validated with:

1. **Unit Tests**: Action space shape, action processing, speed multiplier
2. **Smoke Test**: 20 steps to verify basic functionality
3. **One-Day Simulation**: 192 steps (full day), 380 orders completed

All tests passed successfully.

## Acceptance Criteria

- [x] PPO controls only task selection (1D action space)
- [x] No references to `action[d, 1]` in training loop/wrappers
- [x] Environment uses fixed speed (1.0 multiplier)
- [x] Behavior remains stable (orders completed, no crashes)
- [x] One-day simulation completes successfully

## Files Modified

- `UAV_ENVIRONMENT_8.py`: Action space, action processing, drone movement
- `U8_train.py`: Wrapper, fallback policy, docstrings
- `.gitignore`: Added to exclude build artifacts

## Security

CodeQL security scan completed with **0 alerts**.
