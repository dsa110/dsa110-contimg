#!/opt/miniforge/envs/casa6/bin/python
"""
Dedicated tool to fix syntax errors, particularly indentation issues,
in Python files using AST parsing and systematic correction.
"""
import ast
import re
from pathlib import Path
from typing import List, Tuple


def find_syntax_errors(source: str, filepath: str) -> List[Tuple[int, str, str]]:
    """Find all syntax errors in source code."""
    errors = []
    lines = source.split('\n')

    # Try parsing multiple times, fixing one error at a time
    max_iterations = 50
    iteration = 0

    while iteration < max_iterations:
        try:
            ast.parse(source)
            break  # No errors found
        except SyntaxError as e:
            iteration += 1
            lineno = e.lineno or len(lines)
            msg = e.msg
            text = e.text.strip() if e.text else ""

            # Check if we've seen this error before (infinite loop)
            error_key = (lineno, msg)
            if any(err[0] == lineno and err[1] == msg for err in errors):
                errors.append((lineno, msg, text))
                break  # Avoid infinite loop

            errors.append((lineno, msg, text))

            # Try to fix common issues
            if lineno <= len(lines):
                line_idx = lineno - 1
                line = lines[line_idx]

                if "expected an indented block" in msg:
                    # Add a pass statement after the if/for/while/etc
                    # Find the opening statement
                    indent_level = len(line) - len(line.lstrip())
                    lines.insert(line_idx + 1, ' ' *
                                 (indent_level + 4) + 'pass')
                    source = '\n'.join(lines)
                    continue
                elif "unexpected indent" in msg:
                    # Remove extra indentation
                    # Try to match indentation of previous non-empty line
                    for prev_idx in range(line_idx - 1, max(-1, line_idx - 10), -1):
                        if prev_idx >= 0 and lines[prev_idx].strip():
                            prev_line = lines[prev_idx]
                            # Check if it's part of a block structure
                            if any(prev_line.strip().startswith(kw) for kw in ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally', 'with', 'def', 'class']):
                                # This line should be indented relative to prev
                                prev_indent = len(
                                    prev_line) - len(prev_line.lstrip())
                                # But if it's an else/elif/except, it should match prev indent
                                if line.strip().startswith(('else', 'elif', 'except', 'finally')):
                                    new_indent = prev_indent
                                else:
                                    new_indent = prev_indent + 4
                                lines[line_idx] = ' ' * \
                                    new_indent + line.lstrip()
                                source = '\n'.join(lines)
                                break
                    else:
                        # Default: reduce indentation by 4 spaces
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent >= 4:
                            lines[line_idx] = ' ' * \
                                (current_indent - 4) + line.lstrip()
                            source = '\n'.join(lines)
                    continue
                elif "invalid syntax" in msg:
                    # Check for common issues
                    if line.strip().startswith('else:') or line.strip().startswith('elif'):
                        # Check if there's a matching if/try
                        # Find previous if/try at same or higher level
                        line_indent = len(line) - len(line.lstrip())
                        for prev_idx in range(line_idx - 1, max(-1, line_idx - 20), -1):
                            if prev_idx >= 0:
                                prev_line = lines[prev_idx]
                                if prev_line.strip() and not prev_line.strip().startswith('#'):
                                    prev_indent = len(
                                        prev_line) - len(prev_line.lstrip())
                                    if prev_line.strip().startswith(('if ', 'try:', 'for ', 'while ')) and prev_indent <= line_indent:
                                        # Match indentation
                                        lines[line_idx] = ' ' * \
                                            prev_indent + line.lstrip()
                                        source = '\n'.join(lines)
                                        break
                    continue

            # If we can't auto-fix, break
            break

    return errors


def fix_indentation_issues(source: str) -> str:
    """Fix common indentation issues systematically."""
    lines = source.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        # Skip empty lines
        if not stripped:
            fixed_lines.append(line)
            continue

        # Check for common problematic patterns
        if stripped.startswith(('else:', 'elif ', 'except', 'finally:')):
            # These should match the indentation of their corresponding if/try
            # Find the matching if/try/for/while
            current_indent = len(line) - len(line.lstrip())

            # Look backwards for matching control structure
            for j in range(i - 1, max(-1, i - 30), -1):
                if j >= 0 and lines[j].strip() and not lines[j].strip().startswith('#'):
                    prev_line = lines[j]
                    prev_stripped = prev_line.lstrip()
                    prev_indent = len(prev_line) - len(prev_line.lstrip())

                    # Check if it's a matching control structure
                    if prev_stripped.startswith(('if ', 'try:', 'for ', 'while ')):
                        if prev_indent == current_indent:
                            # Correct indentation
                            fixed_lines.append(line)
                        else:
                            # Fix indentation to match
                            fixed_lines.append(' ' * prev_indent + stripped)
                        break
                    elif prev_stripped.startswith(('elif ', 'else:', 'except', 'finally:')):
                        # Continue searching
                        continue
            else:
                # No matching structure found, keep as is
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def fix_file(filepath: Path) -> bool:
    """Fix syntax errors in a file."""
    print(f"Fixing syntax errors in: {filepath}")

    with open(filepath, 'r') as f:
        original_source = f.read()

    source = original_source
    max_fixes = 20
    fixes_applied = 0

    for attempt in range(max_fixes):
        # Check for syntax errors
        try:
            ast.parse(source)
            print(f"✓ File parses successfully after {attempt} fix attempts!")
            if source != original_source:
                # Write fixed version
                with open(filepath, 'w') as f:
                    f.write(source)
                print(f"✓ Fixed file written: {filepath}")
            else:
                print(f"✓ No fixes needed")
            return True
        except SyntaxError as e:
            fixes_applied += 1
            lineno = e.lineno or 1
            msg = e.msg
            text = e.text.strip() if e.text else ""

            print(
                f"  Attempt {attempt + 1}: Syntax error at line {lineno}: {msg}")
            if text:
                print(f"    Line: {text}")

            lines = source.split('\n')
            if lineno > len(lines):
                print(
                    f"  Error: Line number {lineno} exceeds file length {len(lines)}")
                break

            line_idx = lineno - 1
            line = lines[line_idx]

            # Apply fixes based on error type
            if "expected an indented block" in msg:
                # Add pass statement
                indent = len(line) - len(line.lstrip())
                if line_idx + 1 < len(lines):
                    # Check if next line is already indented
                    next_line = lines[line_idx +
                                      1] if line_idx + 1 < len(lines) else ""
                    if next_line.strip() and len(next_line) - len(next_line.lstrip()) <= indent:
                        # Next line is not indented, add pass
                        lines.insert(line_idx + 1, ' ' * (indent + 4) + 'pass')
                        source = '\n'.join(lines)
                        continue
            elif "unexpected indent" in msg:
                # Fix indentation
                current_indent = len(line) - len(line.lstrip())

                # Find appropriate indentation level
                # Look for previous non-empty line
                for prev_idx in range(line_idx - 1, max(-1, line_idx - 20), -1):
                    if prev_idx >= 0:
                        prev_line = lines[prev_idx]
                        if prev_line.strip() and not prev_line.strip().startswith('#'):
                            prev_indent = len(prev_line) - \
                                len(prev_line.lstrip())
                            prev_stripped = prev_line.lstrip()

                            # Determine correct indentation
                            if stripped.startswith(('else:', 'elif ', 'except', 'finally:')):
                                # Should match indentation of corresponding if/try
                                if prev_stripped.startswith(('if ', 'try:', 'for ', 'while ')):
                                    new_indent = prev_indent
                                elif prev_stripped.startswith(('elif ', 'else:', 'except', 'finally:')):
                                    new_indent = prev_indent
                                else:
                                    new_indent = prev_indent
                            else:
                                # Should be indented relative to previous
                                if prev_stripped.endswith(':'):
                                    new_indent = prev_indent + 4
                                else:
                                    new_indent = prev_indent

                            if new_indent != current_indent:
                                lines[line_idx] = ' ' * new_indent + stripped
                                source = '\n'.join(lines)
                                break
                else:
                    # Default: reduce by 4 spaces if too indented
                    if current_indent >= 4:
                        lines[line_idx] = ' ' * (current_indent - 4) + stripped
                        source = '\n'.join(lines)
            elif "invalid syntax" in msg:
                stripped = line.lstrip()
                if stripped.startswith(('else:', 'elif ')):
                    # Find matching if/try
                    for prev_idx in range(line_idx - 1, max(-1, line_idx - 30), -1):
                        if prev_idx >= 0:
                            prev_line = lines[prev_idx]
                            if prev_line.strip() and not prev_line.strip().startswith('#'):
                                prev_indent = len(
                                    prev_line) - len(prev_line.lstrip())
                                prev_stripped = prev_line.lstrip()
                                if prev_stripped.startswith(('if ', 'try:', 'for ', 'while ')):
                                    # Match indentation
                                    lines[line_idx] = ' ' * \
                                        prev_indent + stripped
                                    source = '\n'.join(lines)
                                    break

    # Final check
    try:
        ast.parse(source)
        if source != original_source:
            with open(filepath, 'w') as f:
                f.write(source)
            print(f"✓ Fixed file written after {fixes_applied} fixes")
        return True
    except SyntaxError as e:
        print(
            f"✗ Could not fix all errors. Remaining error at line {e.lineno}: {e.msg}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fix_syntax_errors.py <file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    success = fix_file(filepath)
    sys.exit(0 if success else 1)
