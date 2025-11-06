# Profiling Guide for Performance Optimization

This guide explains how to profile the DSA-110 continuum imaging pipeline to identify performance bottlenecks and optimization opportunities.

## Overview

Profiling helps identify:
- **Hot paths** (code that runs frequently)
- **Bottlenecks** (operations that take the most time)
- **Memory hotspots** (operations that use the most memory)
- **I/O bottlenecks** (disk or network operations)

## Tools

### 1. cProfile (Python Built-in)

**Purpose:** Statistical profiling of Python code

**Usage:**
```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()
result = your_function()
profiler.disable()

# Save results
profiler.dump_stats('profile_results.prof')

# Analyze results
stats = pstats.Stats('profile_results.prof')
stats.sort_stats('cumulative')  # Sort by cumulative time
stats.print_stats(20)  # Print top 20 functions
```

**Command Line:**
```bash
python -m cProfile -o profile_results.prof -m dsa110_contimg.calibration.cli calibrate --ms /path/to/ms
python -m pstats profile_results.prof
```

### 2. line_profiler

**Purpose:** Line-by-line profiling (shows which lines take the most time)

**Installation:**
```bash
pip install line_profiler
```

**Usage:**
```python
# Add @profile decorator to function you want to profile
@profile
def your_function():
    # ... code ...
    pass

# Run with kernprof
kernprof -l -v your_script.py
```

### 3. memory_profiler

**Purpose:** Memory usage profiling

**Installation:**
```bash
pip install memory_profiler
```

**Usage:**
```python
from memory_profiler import profile

@profile
def your_function():
    # ... code ...
    pass
```

**Command Line:**
```bash
python -m memory_profiler your_script.py
```

### 4. py-spy (External Profiler)

**Purpose:** Sampling profiler that works on running processes

**Installation:**
```bash
pip install py-spy
```

**Usage:**
```bash
# Attach to running process
py-spy record -o profile.svg --pid <PID>

# Profile a script
py-spy record -o profile.svg -- python your_script.py
```

## Profiling Workflow

### Step 1: Identify Hot Paths

1. **Run cProfile on main operation:**
```bash
python -m cProfile -o calibration.prof -m dsa110_contimg.calibration.cli calibrate --ms /path/to/ms
```

2. **Analyze results:**
```python
import pstats
stats = pstats.Stats('calibration.prof')
stats.sort_stats('cumulative')
stats.print_stats(30)  # Top 30 functions
```

3. **Look for:**
   - Functions with high `cumulative` time (total time including subcalls)
   - Functions with high `tottime` (time in function itself)
   - Functions called many times (`ncalls`)

### Step 2: Deep Dive into Hot Functions

1. **Identify function to profile:**
   - From Step 1, identify functions with high `tottime`

2. **Use line_profiler:**
```python
@profile
def hot_function():
    # ... code ...
    pass
```

3. **Run:**
```bash
kernprof -l -v your_script.py
```

### Step 3: Memory Profiling

1. **Profile memory usage:**
```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    # ... code ...
    pass
```

2. **Look for:**
   - Lines with high memory increment
   - Memory leaks (gradual increase)

### Step 4: Optimize

1. **Apply optimizations:**
   - Cache expensive operations
   - Batch I/O operations
   - Use vectorization
   - Reduce function call overhead

2. **Re-profile to verify:**
   - Compare before/after profiles
   - Measure improvement

## Example: Profiling Calibration

### Profile the calibration workflow:

```bash
# Profile calibration
python -m cProfile -o cal.prof -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --preset=standard

# Analyze
python -c "
import pstats
stats = pstats.Stats('cal.prof')
stats.sort_stats('cumulative')
stats.print_stats(20)
"
```

### Expected Hot Paths:

1. **CASA tool calls** (`gaincal`, `bandpass`, `setjy`)
2. **MS table reads** (`getcol`, `getcell`)
3. **MODEL_DATA calculation**
4. **File I/O** (reading/writing MS files)

### Optimization Opportunities:

1. **Cache MS metadata** (already implemented)
2. **Batch subband loading** (already implemented)
3. **Parallel processing** (already implemented)
4. **Reduce CASA tool calls** (combine operations)
5. **Optimize table reads** (use `getcol` instead of `getcell` in loops)

## Profiling Checklist

- [ ] Profile main operation (calibration, imaging, conversion)
- [ ] Identify top 10 functions by cumulative time
- [ ] Identify top 10 functions by total time
- [ ] Line-profile hot functions
- [ ] Memory profile memory-intensive operations
- [ ] Document findings
- [ ] Apply optimizations
- [ ] Re-profile to verify improvements

## Interpreting Results

### cProfile Output

```
ncalls  tottime  percall  cumtime  percall filename:lineno(function)
1000    5.234    0.005    10.567   0.011   module.py:123(function)
```

- **ncalls**: Number of calls
- **tottime**: Total time in function (excluding subcalls)
- **percall**: tottime / ncalls
- **cumtime**: Cumulative time (including subcalls)
- **percall**: cumtime / ncalls

### What to Look For

1. **High cumtime, low tottime**: Function calls expensive subfunctions
2. **High tottime**: Function itself is expensive
3. **High ncalls**: Function called frequently (may benefit from caching)
4. **High percall**: Each call is expensive

## Performance Targets

After optimization, aim for:

- **MS metadata reads**: < 1ms (cached)
- **Flag validation**: < 10ms (sampled, cached)
- **Subband loading**: < 5 minutes for 16 subbands (batched)
- **Calibration**: < 30 minutes for standard preset
- **Imaging**: < 60 minutes for standard field

## Tools Comparison

| Tool | Type | Overhead | Best For |
|------|------|----------|----------|
| cProfile | Statistical | Medium | Overall performance analysis |
| line_profiler | Line-by-line | High | Detailed function analysis |
| memory_profiler | Memory | High | Memory usage analysis |
| py-spy | Sampling | Low | Production profiling |

## Best Practices

1. **Profile representative workloads** - Use real data sizes
2. **Profile multiple times** - Account for variability
3. **Profile in production-like environment** - I/O characteristics matter
4. **Document findings** - Share results with team
5. **Track improvements** - Measure before/after

## Future Enhancements

- Automatic profiling integration
- Performance regression detection
- Continuous profiling in production
- Performance dashboard

