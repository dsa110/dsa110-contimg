# Conda Environment Warning Suppression

## Overview

The `PYTHONWARNINGS` environment variable is baked into the casa6 conda environment, making warning suppression automatic whenever the environment is activated.

## Implementation

### Activation Script Location

```
/opt/miniforge/envs/casa6/etc/conda/activate.d/python_warnings.sh
```

This script runs automatically when the casa6 environment is activated via `conda activate casa6`.

### What It Does

The activation script sets:
```bash
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

This suppresses SWIG-generated deprecation warnings from CASA/casacore.

## Setup

### Automated Setup

Run the setup script:
```bash
./scripts/setup_casa6_warnings.sh
```

This will:
1. Check if casa6 environment exists
2. Create activation directory if needed
3. Add the activation script
4. Make it executable

### Manual Setup

If you need to set it up manually:

```bash
# Create activation directory
mkdir -p /opt/miniforge/envs/casa6/etc/conda/activate.d

# Create activation script
cat > /opt/miniforge/envs/casa6/etc/conda/activate.d/python_warnings.sh << 'EOF'
#!/bin/bash
export PYTHONWARNINGS="ignore::DeprecationWarning"
EOF

# Make executable
chmod +x /opt/miniforge/envs/casa6/etc/conda/activate.d/python_warnings.sh
```

## Usage

### Activating Environment

```bash
conda activate casa6
# PYTHONWARNINGS is now automatically set
python -c "from casatools import linearmosaic; print('✓ No warnings')"
```

### Verification

After activating casa6:
```bash
echo $PYTHONWARNINGS
# Should output: ignore::DeprecationWarning
```

### Testing

```bash
conda activate casa6
python -c "from casatools import linearmosaic; from casacore.images import image; print('✓ No warnings')"
```

## Benefits

- ✅ **Automatic**: Works whenever casa6 is activated
- ✅ **Persistent**: Survives system reboots
- ✅ **User-independent**: Works for all users of the environment
- ✅ **No shell profile needed**: Doesn't require modifying `.bashrc` or `.zshrc`
- ✅ **Environment-specific**: Only affects casa6 environment, not system Python

## Comparison

| Method | Scope | Persistence |
|--------|-------|-------------|
| **Conda activation script** | casa6 environment only | ✅ Survives reboots |
| Shell profile | All Python executions | ✅ Survives reboots |
| Command-line flag | Single command | ❌ One-time only |
| Script variable | Script execution | ❌ One-time only |

## Deactivation

When you deactivate the environment:
```bash
conda deactivate
# PYTHONWARNINGS is unset (or returns to previous value)
```

## Multiple Environments

If you have multiple conda environments that use CASA, you can add the same activation script to each:

```bash
# For another environment
mkdir -p /opt/miniforge/envs/other-env/etc/conda/activate.d
cp /opt/miniforge/envs/casa6/etc/conda/activate.d/python_warnings.sh \
   /opt/miniforge/envs/other-env/etc/conda/activate.d/
```

## Troubleshooting

### Script Not Running

Check if activation directory exists:
```bash
ls -la /opt/miniforge/envs/casa6/etc/conda/activate.d/
```

Check script permissions:
```bash
ls -l /opt/miniforge/envs/casa6/etc/conda/activate.d/python_warnings.sh
# Should be executable (-rwxr-xr-x)
```

### Warnings Still Appear

1. Verify environment is activated: `conda info --envs` (asterisk shows active)
2. Check variable is set: `echo $PYTHONWARNINGS`
3. Verify script exists and is executable
4. Try reactivating: `conda deactivate && conda activate casa6`

## Notes

- The activation script runs **every time** the environment is activated
- It sets the variable for that shell session only
- If you set `PYTHONWARNINGS` manually, it will override the activation script value
- The script is bash-compatible and works with zsh, fish, etc. (via conda's activation system)

