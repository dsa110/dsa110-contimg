# Development Guide

## Overview

The `postx` module uses a **composition-based architecture** that provides a clean, namespaced API. The central object is `ApertureArray`, which acts as a **coordinating facade** over specialized submodules, which are subclasses of the `AaBaseModule` class.

## Core Architecture

### ApertureArray class

`ApertureArray` is the main entry point that provides:

1. **Data Management**: Stores UVX visibility data, antenna positions, frequency/time arrays
2. **Workspace Management**: Maintains state for current indices (frequency, time, polarization) and temporary data
3. **Module Composition**: Attaches specialized submodules as namespaced attributes

```python
# Example usage
aa = ApertureArray(uvx)
aa.plotting.plot_antennas()      # Access plotting functionality
aa.coords.get_sun()              # Access coordinate utilities
aa.imaging.make_image()          # Access imaging algorithms
```

### Extending with AaBaseModule

`AaBaseModule` provides the infrastructure that enables the API pattern. It implements:

1. **Dynamic Method Binding**: The `_attach_funcs()` method binds standalone functions as instance methods
2. **Signature Rewriting**: Uses `makefun.with_signature` to hide the parent `ApertureArray` parameter from the public API
3. **Documentation Preservation**: Maintains original docstrings and metadata
4. **Help System**: Provides `help()` method that shows available functionality

## How It Works

Submodule functions follow a consistent pattern where the first parameter is always the parent `ApertureArray`:

```python
def plot_antennas(aa: ApertureArray, x: str = 'E', y: str = 'N', **kwargs):
    """Plot antenna locations in ENU coordinates."""
    # Function implementation using aa.xyz_enu, aa.ant_names, etc.
```

### Dynamic Method Attachment

The `_attach_funcs()` method of `AaBaseModel` transforms these standalone functions into instance methods:

```python
# In AaPlotter.__init__()
plotter_funcs = {
    'plot_corr_matrix': plot_corr_matrix,
    'plot_antennas': plot_antennas,
    'plot_uvdist_amp': plot_uvdist_amp
}
self._attach_funcs(plotter_funcs)
```

Within `_attach_funcs()`, a wrapper extracts the method signature and docstring and attaches it to the parent `AaBaseModule` instance:

```python
@wraps(func)
def wrapper(*args, __func=func, **kwargs):
    # Get the first parameter name from the function signature
    sig = signature(__func)
    first_param = list(sig.parameters.keys())[0]  # Usually 'aa'
    # Remove it from kwargs if present
    kwargs.pop(first_param, None)
    # Inject self.aa as the first argument
    return __func(self.aa, *args, **kwargs)
```

This creates a method that:
- **Publicly** appears as `plot_antennas(x='E', y='N')`
- **Internally** calls `plot_antennas(aa, x='E', y='N')`
- **Preserves** the original docstring and metadata

## Module Organization

### Current Submodules

Each submodule inherits from `AaBaseModule` and provides domain-specific functionality:

- **`aa.coords`** (`AaCoords`): Coordinate transformations, sun/zenith calculations
- **`aa.plotting`** (`AaPlotter`): Visualization of antennas, correlation matrices, UV coverage
- **`aa.imaging`** (`AaImager`): Post-correlation beamforming, HEALPix imaging
- **`aa.calibration`** (`AaCalibrator`): Self-holography, StefCal algorithms
- **`aa.simulation`** (`AaSimulator`): Sky model simulation, visibility generation
- **`aa.viewer`** (`AllSkyViewer`): All-sky image viewing, FITS export

### Submodule Structure

Each submodule follows this pattern:

```python
class AaPlotter(AaBaseModule):
    """A class for plotting utilities."""

    def __init__(self, aa: ApertureArray):
        self.aa = aa  # Reference to parent ApertureArray
        self.name = 'plotting'
        self._attach_funcs(plotter_funcs)  # Bind functions as methods
```

## Benefits of This Architecture

* Separation of Concerns
  - Each submodule handles one domain (plotting, coordinates, imaging, etc.)
  - Functions can be tested independently
  - Easy to add new functionality without modifying existing code
* Intuitive API
  - Natural namespacing: `aa.plotting.plot_antennas()`
  - Jupyter/IDE autocomplete works perfectly
  - Help system shows available methods: `aa.plotting.help()`
* Maintainability
  - Functions are standalone and reusable
  - No complex inheritance hierarchies
  - Easy to understand and modify
* Extensibility
  - Adding new submodules is straightforward
  - New functions can be added to existing submodules easily
  - The pattern is consistent across all modules

## Adding New Functionality

### Adding a New Function to an Existing Submodule

1. **Write the function** following the `func(aa, *args, **kwargs)` pattern
2. **Add it to the function dictionary** in the submodule's `__init__`
3. **Call `_attach_funcs()`** to bind it as a method

```python
def new_plot_function(aa: ApertureArray, param1: str, **kwargs):
    """New plotting function."""
    # Implementation using aa.xyz_enu, etc.
    pass

# In AaPlotter.__init__()
plotter_funcs['new_plot_function'] = new_plot_function
```

### Adding a New Submodule

1. **Create a new class** inheriting from `AaBaseModule`
2. **Implement the standard pattern** with `__init__()` and `_attach_funcs()`
3. **Attach it to ApertureArray** in `ApertureArray.__init__()`

```python
class AaNewModule(AaBaseModule):
    def __init__(self, aa: ApertureArray):
        self.aa = aa
        self.name = 'new_module'
        self._attach_funcs(new_module_funcs)

# In ApertureArray.__init__()
self.new_module = AaNewModule(self)
```

## Developer tips

1. **Follow the function signature pattern**: Always use `aa: ApertureArray` as the first parameter
2. **Write comprehensive docstrings**: They'll be preserved in the public API
3. **Use type hints**: They help with IDE support and documentation
4. **Test functions independently**: Since they're standalone, they can be unit tested easily
5. **Keep functions focused**: Each function should do one thing well
6. **Use the workspace**: For temporary data that needs to persist between calls
