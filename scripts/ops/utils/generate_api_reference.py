#!/opt/miniforge/envs/casa6/bin/python
"""
Generate API reference documentation from docstrings.

This script extracts docstrings from the codebase and generates
a comprehensive API reference document.
"""

import ast
import importlib
import inspect
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

def extract_docstring(node: ast.AST) -> str:
    """Extract docstring from AST node."""
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
        if (node.body and isinstance(node.body[0], ast.Expr) and
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
    return ""

def format_signature(func: callable) -> str:
    """Format function signature."""
    try:
        sig = inspect.signature(func)
        return str(sig)
    except (ValueError, TypeError):
        return "()"

def extract_module_info(module_name: str) -> Dict:
    """Extract class and function information from an imported module."""
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        return {"error": str(e)}
    
    info = {
        "classes": [],
        "functions": [],
        "module_doc": inspect.getdoc(module) or ""
    }
    
    # Extract classes
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module_name:
            methods = []
            for method_name, method_obj in inspect.getmembers(obj, predicate=inspect.ismethod):
                if not method_name.startswith("_"):
                    methods.append({
                        "name": method_name,
                        "docstring": inspect.getdoc(method_obj) or "",
                        "signature": format_signature(method_obj)
                    })
            for method_name, method_obj in inspect.getmembers(obj, predicate=inspect.isfunction):
                if not method_name.startswith("_"):
                    methods.append({
                        "name": method_name,
                        "docstring": inspect.getdoc(method_obj) or "",
                        "signature": format_signature(method_obj)
                    })
            
            info["classes"].append({
                "name": name,
                "docstring": inspect.getdoc(obj) or "",
                "methods": methods
            })
        
        elif inspect.isfunction(obj) and obj.__module__ == module_name:
            if not name.startswith("_"):
                info["functions"].append({
                    "name": name,
                    "docstring": inspect.getdoc(obj) or "",
                    "signature": format_signature(obj)
                })
    
    return info

def generate_api_reference(output_path: Path):
    """Generate API reference from docstrings."""
    src_path = REPO_ROOT / "backend" / "src" / "dsa110_contimg"
    
    # Modules to document
    modules_to_doc = [
        "pipeline.stages",
        "pipeline.stages_impl",
        "pipeline.orchestrator",
        "pipeline.config",
        "pipeline.context",
        "pipeline.workflows",
        "conversion.uvh5_to_ms",
        "conversion.streaming.streaming_converter",
        "calibration.calibration",
        "imaging.spw_imaging",
        "qa.base",
        "qa.fast_validation",
        "photometry.forced",
        "mosaic.streaming_mosaic",
        "catalog.crossmatch",
    ]
    
    output_lines = [
        "# Pipeline API Reference",
        "",
        "> **Generated:** This document is auto-generated from docstrings.",
        "> **Last Updated:** Run `scripts/generate_api_reference.py` to regenerate.",
        "",
        "## Table of Contents",
        ""
    ]
    
    # Collect all module info
    module_info = {}
    for module_name in modules_to_doc:
        try:
            info = extract_module_info(f"dsa110_contimg.{module_name}")
            if "error" not in info:
                module_info[module_name] = info
        except Exception as e:
            print(f"Warning: Could not import {module_name}: {e}", file=sys.stderr)
    
    # Generate TOC
    for module_name in modules_to_doc:
        if module_name in module_info:
            display_name = module_name.replace("_", " ").title()
            anchor = module_name.replace(".", "-").replace("_", "-")
            output_lines.append(f"- [{display_name}](#{anchor})")
    
    output_lines.extend(["", "---", ""])
    
    # Generate content
    for module_name in modules_to_doc:
        if module_name not in module_info:
            continue
        
        info = module_info[module_name]
        display_name = module_name.replace("_", " ").title()
        anchor = module_name.replace(".", "-").replace("_", "-")
        
        output_lines.extend([
            f"## {display_name}",
            "",
            f"**Module:** `{module_name}`",
            ""
        ])
        
        if info.get("module_doc"):
            output_lines.extend([
                "### Module Description",
                "",
                info["module_doc"],
                ""
            ])
        
        # Document classes
        if info.get("classes"):
            output_lines.append("### Classes")
            output_lines.append("")
            for cls in info["classes"]:
                output_lines.extend([
                    f"#### `{cls['name']}`",
                    ""
                ])
                if cls["docstring"]:
                    output_lines.extend([
                        cls["docstring"],
                        ""
                    ])
                
                # Document methods
                if cls["methods"]:
                    output_lines.append("**Methods:**")
                    output_lines.append("")
                    for method in cls["methods"]:
                        sig = method.get("signature", "()")
                        output_lines.extend([
                            f"- `{method['name']}{sig}`",
                        ])
                        if method["docstring"]:
                            # Extract first line of docstring
                            first_line = method["docstring"].split("\n")[0].strip()
                            if first_line:
                                output_lines.append(f"  - {first_line}")
                    output_lines.append("")
        
        # Document functions
        if info.get("functions"):
            output_lines.append("### Functions")
            output_lines.append("")
            for func in info["functions"]:
                sig = func.get("signature", "()")
                output_lines.extend([
                    f"#### `{func['name']}{sig}`",
                    ""
                ])
                if func["docstring"]:
                    output_lines.extend([
                        func["docstring"],
                        ""
                    ])
        
        output_lines.append("---")
        output_lines.append("")
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))
    
    print(f"Generated API reference: {output_path}")

if __name__ == "__main__":
    output_path = Path(__file__).parent.parent / "docs" / "reference" / "api_reference_generated.md"
    generate_api_reference(output_path)

