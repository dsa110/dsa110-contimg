# JS9 Integration for QA Visualization

JS9 is a JavaScript library for viewing FITS files in web browsers. This module
provides integration for JS9 in Jupyter notebooks.

## Setup

### Option 1: Use CDN (Recommended for Development)

JS9 will automatically fall back to CDN if local files are not found. No setup
required!

### Option 2: Bundle JS9 Files Locally

1. Download JS9 from: https://github.com/ericmandel/js9
2. Copy JS9 files to `src/dsa110_contimg/qa/visualization/js9/static/js9/`:
   - `js9.js` (or `js9.min.js`)
   - `js9.css`
   - `js9Helper.js` (optional)
   - Other JS9 support files as needed

3. The directory structure should be:
   ```
   js9/static/js9/
   ├── js9.js
   ├── js9.css
   └── js9Helper.js (optional)
   ```

## Usage

```python
from dsa110_contimg.qa.visualization import FITSFile, init_js9

# Initialize JS9 (optional - will auto-init when needed)
init_js9()

# Load and display a FITS file
fits = FITSFile("image.fits")
fits.show()
```

## Notes

- JS9 requires files to be served via HTTP for local files
- In Jupyter notebooks, files are typically served automatically
- For production, ensure FITS files are accessible via HTTP URLs
- CDN fallback is available if local files are not found
