# Mermaid Diagram Visual Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for validating that all Mermaid diagrams in the MkDocs documentation render correctly without syntax errors.

## Problem Statement

Mermaid diagrams can fail to render due to syntax errors, configuration issues, or plugin problems. When a diagram fails, MkDocs displays a visual error indicator:
- A bomb icon (dark brown sphere with lit fuse)
- Text: "Syntax error in text"
- Version: "mermaid version 10.9.5"

This testing strategy ensures all diagrams render correctly by visually inspecting every page.

## Testing Approach

### 1. Page Discovery

- Extract all pages from `mkdocs.yml` navigation structure
- Handle nested navigation (sections, subsections)
- Convert markdown file paths to URL paths
- Support both `.md` and `.ipynb` files

### 2. Test Execution

1. **Start MkDocs Server**
   - Launch `mkdocs serve` on `127.0.0.1:8001` (as configured in `mkdocs.yml`)
   - Wait for server to be ready
   - Verify server is responding

2. **Browser Automation**
   - Use Playwright for cross-browser testing
   - Navigate to each page sequentially
   - Wait for page load and Mermaid rendering
   - Capture page snapshots for debugging

3. **Visual Error Detection**
   - Check for presence of error indicator elements:
     - Bomb icon (visual element)
     - Text content: "Syntax error in text"
     - Text content: "mermaid version"
   - Verify absence of these elements indicates successful rendering

4. **Result Reporting**
   - Generate detailed test report
   - List pages with failed diagrams
   - Include screenshots of failures
   - Provide page URLs for easy access

## Implementation

### Test Script: `test_mermaid_diagrams.py`

Located in `tests/docs/`, this script:
- Parses `mkdocs.yml` to extract all pages
- Manages MkDocs server lifecycle
- Uses Playwright for browser automation
- Detects Mermaid rendering errors
- Generates comprehensive reports

### Test Configuration

- **Base URL**: `http://127.0.0.1:8001`
- **Timeout**: 30 seconds per page
- **Mermaid Render Wait**: 5 seconds after page load
- **Browser**: Chromium (headless mode)

## Error Detection Strategy

### Visual Indicators

1. **Bomb Icon Detection**
   - Look for SVG or image elements with bomb-like characteristics
   - Check for error container elements

2. **Text Content Detection**
   - Search page text for "Syntax error in text"
   - Search for "mermaid version" (indicates error state)
   - Verify these strings are NOT present on successful renders

3. **Mermaid Element Validation**
   - Verify presence of `.mermaid` class elements
   - Check that rendered SVG elements exist
   - Ensure no error messages in Mermaid containers

## Test Execution

### Manual Execution

```bash
# Install dependencies
pip install -r docs/requirements.txt
pip install playwright
playwright install chromium

# Run tests
make test-mermaid-diagrams
```

### CI/CD Integration

- Run as part of documentation build validation
- Fail build if any diagrams have rendering errors
- Generate artifacts: test report, screenshots

## Expected Outcomes

### Success Criteria

- All pages load successfully
- All Mermaid diagrams render without errors
- No error indicators present on any page
- Test completes within reasonable time (< 10 minutes for full site)

### Failure Handling

- Report specific pages with failures
- Include error details (which diagram failed)
- Provide actionable debugging information
- Generate screenshots for visual inspection

## Maintenance

### When to Run

- Before documentation releases
- After adding new Mermaid diagrams
- After updating MkDocs or Mermaid plugins
- As part of CI/CD pipeline

### Updating Tests

- Add new pages automatically via `mkdocs.yml` parsing
- Update error detection if Mermaid error format changes
- Adjust timeouts based on site size and performance

## Known Limitations

1. **Dynamic Content**: Pages with JavaScript-heavy content may need longer wait times
2. **Notebook Rendering**: Jupyter notebooks may require special handling
3. **Network Dependencies**: External CDN resources (Mermaid JS) must be accessible
4. **Browser Differences**: Testing primarily on Chromium; other browsers may differ

## Future Enhancements

- Multi-browser testing (Firefox, WebKit)
- Performance benchmarking
- Accessibility checks for rendered diagrams
- Automated diagram syntax validation before rendering
- Integration with Mermaid linting tools

