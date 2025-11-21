# QA Visualization Framework - Quick Start

## Where to Access Features

### Option 1: Via Main QA Module (Simplest)

```python
from dsa110_contimg.qa import FITSFile, CasaTable, ls, generate_qa_notebook
```

### Option 2: Direct from Visualization Module

```python
from dsa110_contimg.qa.visualization import (
    FITSFile,
    CasaTable,
    ls,
    generate_qa_notebook,
    browse_qa_outputs,
)
```

### Option 3: Enhanced QA Function

```python
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization
```

## Quick Examples

### Browse QA Directory

```python
from dsa110_contimg.qa import ls

qa_dir = ls("state/qa")
qa_dir.show()
```

### View FITS File

```python
from dsa110_contimg.qa import FITSFile, init_js9

init_js9()
fits = FITSFile("image.fits")
fits.show()
```

### Generate QA Notebook

```python
from dsa110_contimg.qa import generate_qa_notebook

notebook = generate_qa_notebook(
    ms_path="data.ms",
    qa_root="state/qa",
    output_path="qa_report.ipynb"
)
```

### Run QA with Auto-Notebook

```python
from dsa110_contimg.qa import run_ms_qa_with_visualization

result = run_ms_qa_with_visualization(
    ms_path="data.ms",
    qa_root="state/qa",
    generate_notebook=True
)
```

## Full Documentation

- **Usage Guide**: `docs/QA_VISUALIZATION_USAGE.md`
- **Access Guide**: `docs/QA_VISUALIZATION_ACCESS.md`
- **Implementation Status**: `docs/QA_VISUALIZATION_IMPLEMENTATION_STATUS.md`
