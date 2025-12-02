#!/opt/miniforge/envs/casa6/bin/python
"""
Generate TypeScript types from Pydantic models.
This script reads Pydantic models and generates corresponding TypeScript interfaces.
"""
import inspect
import re
import sys
from pathlib import Path
from typing import Union, get_args, get_origin, get_type_hints

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

try:
    from dsa110_contimg.api.models import *
    from dsa110_contimg.api.visualization_routes import (CasaTableInfo,
                                                         DirectoryEntry,
                                                         DirectoryListing,
                                                         FITSInfo)
except ImportError as e:
    print(f"Error importing models: {e}", file=sys.stderr)
    sys.exit(1)


def python_type_to_ts(python_type, optional=False):
    """Convert Python type to TypeScript type."""
    if python_type is None or python_type == type(None):
        return "null"

    # Handle string representation of types (from Pydantic)
    if isinstance(python_type, str):
        if python_type == "datetime" or "datetime" in python_type.lower():
            return "string"
        if python_type in ["str", "string"]:
            return "string"
        if python_type in ["int", "float", "number"]:
            return "number"
        if python_type == "bool":
            return "boolean"
        return "any"

    origin = get_origin(python_type)
    args = get_args(python_type)

    # Handle Optional/Union types
    if origin is type(None) or (origin is not None and type(None) in args):
        optional = True
        # Get the non-None type
        non_none_args = [a for a in args if a is not type(None)]
        if non_none_args:
            python_type = (
                non_none_args[0] if len(non_none_args) == 1 else Union[tuple(non_none_args)]
            )
        origin = get_origin(python_type)
        args = get_args(python_type)

    # Handle Union types (excluding None)
    if origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) > 1:
            ts_types = [python_type_to_ts(t, False) for t in non_none_args]
            result = " | ".join(ts_types)
            return f"{result}?" if optional else result

    # Handle List types
    if origin is list or (hasattr(python_type, "__origin__") and python_type.__origin__ is list):
        if args:
            inner_type = python_type_to_ts(args[0], False)
            return f"{inner_type}[]"
        return "any[]"

    # Handle Dict types
    if origin is dict:
        return "Record<string, any>"

    # Handle datetime types
    if hasattr(python_type, "__name__"):
        if "datetime" in python_type.__name__.lower() or "date" in python_type.__name__.lower():
            return "string"

    # Handle basic types
    type_map = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        dict: "Record<string, any>",
        list: "any[]",
    }

    if python_type in type_map:
        result = type_map[python_type]
        return f"{result}?" if optional else result

    # Handle custom types (Pydantic models)
    if hasattr(python_type, "__name__"):
        result = python_type.__name__
        return f"{result}?" if optional else result

    return "any"


def generate_interface(model_class):
    """Generate TypeScript interface from Pydantic model."""
    class_name = model_class.__name__

    # Get fields from Pydantic model (Pydantic v2)
    if hasattr(model_class, "model_fields"):
        fields = model_class.model_fields
        is_pydantic_v2 = True
    elif hasattr(model_class, "__fields__"):
        fields = model_class.__fields__
        is_pydantic_v2 = False
    else:
        return None

    lines = [f"export interface {class_name} {{"]

    for field_name, field_info in fields.items():
        # Get field type
        if is_pydantic_v2:
            # Pydantic v2
            field_type = field_info.annotation
            # Check if optional (Pydantic v2)
            is_optional = not field_info.is_required()
            # Handle default values
            if hasattr(field_info, "default") and field_info.default is not ...:
                is_optional = True
        else:
            # Pydantic v1
            field_type = field_info.type_
            is_optional = field_info.required is False

        # Handle string annotations (forward references)
        if isinstance(field_type, str):
            # Try to resolve the type
            if field_type in globals():
                field_type = globals()[field_type]

        ts_type = python_type_to_ts(field_type, is_optional)

        # Add optional marker if needed
        if is_optional and not ts_type.endswith("?"):
            optional_marker = "?"
        else:
            optional_marker = ""

        lines.append(f"  {field_name}{optional_marker}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)


def main():
    """Generate TypeScript types for all Pydantic models."""
    # Get all Pydantic models from the module
    models = []
    for name, obj in inspect.getmembers(sys.modules["dsa110_contimg.api.models"]):
        if inspect.isclass(obj) and hasattr(obj, "__module__") and "pydantic" in str(obj.__bases__):
            if "BaseModel" in str(obj.__bases__):
                models.append(obj)

    # Also get models from visualization_routes
    try:
        for name, obj in inspect.getmembers(sys.modules["dsa110_contimg.api.visualization_routes"]):
            if (
                inspect.isclass(obj)
                and hasattr(obj, "__module__")
                and "BaseModel" in str(obj.__bases__)
            ):
                models.append(obj)
    except:
        pass

    # Generate interfaces
    output = []
    output.append("// Auto-generated TypeScript types from Pydantic models")
    output.append(
        "// DO NOT EDIT MANUALLY - This file is generated by scripts/generate_typescript_types.py\n"
    )

    for model in sorted(set(models), key=lambda x: x.__name__):
        interface = generate_interface(model)
        if interface:
            output.append(interface)
            output.append("")

    print("\n".join(output))


if __name__ == "__main__":
    main()
