# AOFlagger Strategy Files for DSA-110

## Overview

AOFlagger uses **Lua scripts** (called "strategies") to define how RFI flagging is performed. These strategies specify:
- Which algorithms to use (SumThreshold, morphological operations, etc.)
- Threshold values and sensitivity settings
- How many iterations to perform
- How to handle different polarizations

## Default Behavior

When you run AOFlagger without specifying a strategy, it attempts to auto-detect the telescope name from the Measurement Set and use a telescope-specific strategy. For DSA-110, AOFlagger will show:

```
** Measurement set specified the following telescope name: 'DSA_110'
** No good strategy is known for this telescope!
** A generic strategy will be used which might not be optimal.
```

This means it falls back to the generic strategy, which works but may not be optimized for DSA-110's specific RFI environment.

## Custom DSA-110 Strategy

A custom strategy (`dsa110-default.lua`) has been created in `docs/aoflagger/` that:

1. **Uses amplitude-based detection** - Most effective for continuum imaging
2. **Optimized for L-band** (~1.4 GHz) - DSA-110's operating frequency
3. **Handles short baselines** - Appropriate for DSA-110's 2.6 km max baseline
4. **Configurable thresholds** - Can be tuned based on site-specific RFI

## Using the Custom Strategy

### Option 1: Copy to Docker Container

```bash
# Copy strategy into container at runtime
docker run --rm \
  -v /scratch:/scratch -v /data:/data \
  -v /data/dsa110-contimg/docs/aoflagger:/strategies:ro \
  aoflagger:latest aoflagger \
  -strategy /strategies/dsa110-default.lua \
  /path/to/measurement_set.ms
```

### Option 2: Use via Pipeline CLI

```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /path/to/ms.ms \
  --mode rfi \
  --rfi-backend aoflagger \
  --aoflagger-strategy /data/dsa110-contimg/docs/aoflagger/dsa110-default.lua
```

### Option 3: Install in Container (Permanent)

To make the strategy available by default, you could:

1. Modify the Dockerfile to copy the strategy:
```dockerfile
COPY docs/aoflagger/dsa110-default.lua /usr/local/share/aoflagger/strategies/
```

2. Rebuild the image:
```bash
cd ~/proj/aoflagger
./build-docker.sh
```

3. Then AOFlagger will auto-detect DSA_110 and use the custom strategy!

## Strategy Parameters

Key parameters in `dsa110-default.lua` that can be tuned:

- **`base_threshold`** (default: 1.0)
  - Lower = more sensitive detection (flags more RFI, but risk of false positives)
  - Higher = less sensitive (flags less RFI, but risk of missing weak RFI)

- **`iteration_count`** (default: 3)
  - More iterations = more thorough but slower
  - 3 iterations is typically a good balance

- **`transient_threshold_factor`** (default: 1.0)
  - Lower = more aggressive transient RFI detection
  - Useful for satellite RFI (GPS, etc.)

- **`frequency_resize_factor`** (default: 1.0)
  - Higher = more smoothing in frequency direction
  - Useful for broadband RFI

## Example Strategies for Reference

AOFlagger includes telescope-specific strategies you can reference:
- `jvla-default.lua` - JVLA (similar to DSA-110: L-band, interferometer)
- `atca-l-band.lua` - ATCA L-band observations
- `generic-default.lua` - Generic strategy (what DSA-110 currently uses)

## Creating Your Own Strategy

To create a custom strategy:

1. Start with `docs/aoflagger/dsa110-default.lua` as a template
2. Adjust parameters based on your RFI environment
3. Test on a known-good calibrator observation
4. Compare flagging statistics with CASA `tfcrop+rflag` results
5. Iterate until you get optimal results

**For detailed parameter optimization methodology, see:**
- `docs/aoflagger/PARAMETER_OPTIMIZATION_GUIDE.md` - Systematic approach to finding optimal thresholds and parameters

## AOFlagger Strategy Documentation

For more details on AOFlagger Lua API and available functions:
- [AOFlagger Manual](https://aoflagger.readthedocs.io/en/latest/index.html)
- [Lua Strategies Section](https://aoflagger.readthedocs.io/en/latest/lua.html)
- [Functions Reference](https://aoflagger.readthedocs.io/en/latest/lua_functions.html)

## Integration with Pipeline

The custom strategy can be integrated into the pipeline by:

1. **Environment variable**: Set `AOFLAGGER_STRATEGY` environment variable
2. **Config file**: Add strategy path to pipeline configuration
3. **CLI argument**: Use `--aoflagger-strategy` flag (already implemented)

