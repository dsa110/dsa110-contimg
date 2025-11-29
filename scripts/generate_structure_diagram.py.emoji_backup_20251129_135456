#!/usr/bin/env python3
"""
Generate a Mermaid flowchart diagram for any directory structure.

Usage:
    python generate_structure_diagram.py <directory_path> [output.svg]

Example:
    python generate_structure_diagram.py /data/dsa110-contimg/backend backend_structure.svg
    python generate_structure_diagram.py /data/dsa110-contimg/frontend frontend_structure.svg
"""

import os
import sys
import base64
import urllib.request
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional
import re


class DirectoryAnalyzer:
    """Analyze directory structure and generate Mermaid diagram."""
    
    # Common file patterns to highlight
    KEY_FILES = {
        'config': ['pyproject.toml', 'setup.py', 'package.json', 'tsconfig.json', 
                   'Makefile', 'requirements.txt', 'poetry.lock'],
        'docs': ['README.md', 'CHANGELOG.md', 'LICENSE'],
        'scripts': ['*.sh', '*.py'],
    }
    
    # Common directory patterns
    IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.pytest_cache', 
                   '.coverage', '.mypy_cache', 'dist', 'build', '.venv', 'venv',
                   '*.egg-info', '.idea', '.vscode', '.DS_Store'}
    
    def __init__(self, root_path: str, max_depth: int = 4, max_items_per_group: int = 15):
        self.root_path = Path(root_path).resolve()
        self.max_depth = max_depth
        self.max_items_per_group = max_items_per_group
        self.structure = defaultdict(list)
        self.python_packages = set()
        self.key_files = []
        self.subdirectories = defaultdict(list)
        
    def is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        name = path.name
        if name.startswith('.'):
            return name in self.IGNORE_DIRS or any(name.startswith(prefix) for prefix in ['.coverage', '.pytest'])
        return name in self.IGNORE_DIRS
    
    def analyze(self):
        """Analyze the directory structure."""
        if not self.root_path.exists():
            raise ValueError(f"Directory does not exist: {self.root_path}")
        
        root_name = self.root_path.name or str(self.root_path)
        
        # Walk the directory tree
        for root, dirs, files in os.walk(self.root_path):
            root_path = Path(root)
            rel_path = root_path.relative_to(self.root_path)
            depth = len(rel_path.parts)
            
            if depth > self.max_depth:
                dirs[:] = []  # Don't recurse deeper
                continue
            
            # Filter ignored directories
            dirs[:] = [d for d in dirs if not self.is_ignored(root_path / d)]
            
            # Check for Python packages
            if '__init__.py' in files:
                self.python_packages.add(rel_path)
            
            # Collect key files
            for file in files:
                if self.is_ignored(root_path / file):
                    continue
                file_path = rel_path / file
                if any(file.endswith(ext) for ext in ['.py', '.ts', '.tsx', '.js', '.jsx', '.md', '.sh']):
                    self.key_files.append(file_path)
            
            # Group subdirectories
            if depth == 1 and dirs:
                for d in dirs:
                    if not self.is_ignored(root_path / d):
                        self.subdirectories[rel_path].append(d)
        
        # Organize structure
        self._organize_structure()
    
    def _organize_structure(self):
        """Organize the discovered structure into logical groups."""
        # Group Python packages
        package_groups = defaultdict(list)
        for pkg_path in sorted(self.python_packages):
            parts = pkg_path.parts
            if len(parts) >= 2:
                # Group by parent directory (e.g., src/dsa110_contimg/api -> api)
                parent = parts[-2] if parts[-2] != 'src' else parts[-1]
                package_groups[parent].append(pkg_path)
            else:
                package_groups['root'].append(pkg_path)
        
        self.structure['python_packages'] = package_groups
        
        # Group key files by type
        file_groups = defaultdict(list)
        for file_path in self.key_files:
            ext = file_path.suffix
            if ext in ['.py']:
                file_groups['python'].append(file_path)
            elif ext in ['.ts', '.tsx']:
                file_groups['typescript'].append(file_path)
            elif ext in ['.js', '.jsx']:
                file_groups['javascript'].append(file_path)
            elif ext == '.md':
                file_groups['docs'].append(file_path)
            elif ext == '.sh':
                file_groups['scripts'].append(file_path)
        
        self.structure['files'] = file_groups
        
        # Group top-level directories
        top_level = []
        for item in sorted(self.root_path.iterdir()):
            if item.is_dir() and not self.is_ignored(item):
                top_level.append(item.name)
        
        self.structure['top_level'] = top_level
    
    def _sanitize_id(self, name: str) -> str:
        """Sanitize name for Mermaid node ID."""
        # Replace special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Remove leading numbers
        sanitized = re.sub(r'^\d+', '', sanitized)
        return sanitized or 'node'
    
    def _get_file_summary(self, file_path: Path) -> str:
        """Get a brief summary of files in a directory."""
        files = list(file_path.parent.glob(f"{file_path.stem}*"))
        if len(files) <= 3:
            return file_path.name
        return f"{file_path.name}<br/>(+{len(files)-1} related)"
    
    def generate_mermaid(self) -> str:
        """Generate Mermaid flowchart code."""
        root_name = self.root_path.name or 'root'
        root_id = self._sanitize_id(root_name)
        
        lines = [f'flowchart TB']
        lines.append(f'    subgraph {root_id}["{root_name}/"]')
        
        # Add top-level structure
        self._add_top_level_nodes(lines, root_id)
        
        # Add Python packages
        self._add_python_packages(lines, root_id)
        
        # Add other key directories
        self._add_other_directories(lines, root_id)
        
        lines.append('    end')
        
        # Add relationships
        self._add_relationships(lines)
        
        # Add styling
        self._add_styling(lines, root_id)
        
        return '\n'.join(lines)
    
    def _add_top_level_nodes(self, lines: List[str], root_id: str):
        """Add top-level configuration and key files."""
        config_files = []
        for file in self.key_files:
            if len(file.parts) == 1:
                name = file.name
                if any(name.endswith(ext) for ext in ['.toml', '.json', '.yaml', '.yml', 'Makefile', 'setup.py']):
                    config_files.append(name)
        
        if config_files:
            config_list = '<br/>'.join(config_files[:5])
            if len(config_files) > 5:
                config_list += f'<br/>(+{len(config_files)-5} more)'
            lines.append(f'        Config["Configuration<br/>{config_list}"]')
    
    def _add_python_packages(self, lines: List[str], root_id: str):
        """Add Python package structure."""
        package_groups = self.structure.get('python_packages', {})
        
        if not package_groups:
            return
        
        # Find the main package directory (usually 'src' or root)
        main_pkg_dir = None
        main_pkg_base = None
        for pkg_path in sorted(self.python_packages):
            if 'src' in pkg_path.parts:
                src_idx = pkg_path.parts.index('src')
                main_pkg_dir = 'src'
                if len(pkg_path.parts) > src_idx + 1:
                    main_pkg_base = pkg_path.parts[src_idx + 1]
                break
        
        if main_pkg_dir:
            lines.append(f'        subgraph Src["{main_pkg_dir}/{main_pkg_base or ""}/"]')
        
        # Organize packages: only show top-level modules (not nested subdirectories)
        top_level_modules = {}
        for pkg_path in sorted(self.python_packages):
            if main_pkg_base and main_pkg_base in pkg_path.parts:
                # Get the module name after the main package base
                parts = pkg_path.parts
                try:
                    base_idx = parts.index(main_pkg_base)
                    if len(parts) > base_idx + 1:
                        module_name = parts[base_idx + 1]
                        # Only include if it's a direct child (depth check)
                        if len(parts) == base_idx + 2:  # src/main_pkg/module
                            if module_name not in top_level_modules:
                                top_level_modules[module_name] = []
                            top_level_modules[module_name].append(pkg_path)
                except ValueError:
                    pass
            elif not main_pkg_base:
                # No main package base, use last part
                if len(pkg_path.parts) <= 2:  # Only include shallow packages
                    module_name = pkg_path.parts[-1]
                    if module_name not in top_level_modules:
                        top_level_modules[module_name] = []
                    top_level_modules[module_name].append(pkg_path)
        
        # Add each module as a node
        for module_name, packages in sorted(top_level_modules.items()):
            # Get key files in this module
            key_files = []
            for pkg in packages:
                pkg_full = self.root_path / pkg
                if pkg_full.exists():
                    py_files = list(pkg_full.glob('*.py'))
                    # Filter out __init__.py and __pycache__
                    py_files = [f for f in py_files if f.name != '__init__.py' and '__pycache__' not in str(f)]
                    if py_files:
                        key_files.extend([f.name for f in py_files[:3]])
            
            if key_files:
                file_list = '<br/>'.join(set(key_files[:3]))
                if len(set(key_files)) > 3:
                    file_list += f'<br/>(+{len(set(key_files))-3} more)'
                desc = f'{module_name}/<br/>{file_list}'
            else:
                desc = f'{module_name}/'
            
            node_id = self._sanitize_id(module_name)
            lines.append(f'            {node_id}["{desc}"]')
        
        if main_pkg_dir:
            lines.append('        end')
    
    def _add_other_directories(self, lines: List[str], root_id: str):
        """Add other important directories."""
        # Add tests directory
        test_dirs = [d for d in self.structure.get('top_level', []) 
                     if 'test' in d.lower()]
        if test_dirs:
            for test_dir in test_dirs[:3]:
                node_id = self._sanitize_id(test_dir)
                lines.append(f'        {node_id}["{test_dir}/<br/>Tests"]')
        
        # Add docs directory
        if 'docs' in self.structure.get('top_level', []):
            lines.append('        Docs["docs/<br/>Documentation"]')
        
        # Add scripts directory
        if 'scripts' in self.structure.get('top_level', []):
            lines.append('        Scripts["scripts/<br/>Utility Scripts"]')
    
    def _add_relationships(self, lines: List[str]):
        """Add relationships between modules."""
        # Simple heuristic: if modules are in a logical order, connect them
        package_groups = self.structure.get('python_packages', {})
        
        # Common pipeline relationships
        pipeline_order = ['conversion', 'calibration', 'imaging', 'photometry', 'catalog']
        organized = {}
        for group_name, packages in package_groups.items():
            for pkg in packages:
                module_name = pkg.parts[-1]
                organized[module_name] = self._sanitize_id(module_name)
        
        # Connect pipeline stages
        prev = None
        for stage in pipeline_order:
            if stage in organized:
                node_id = organized[stage]
                if prev:
                    lines.append(f'    {prev} --> {node_id}')
                prev = node_id
        
        # Connect API to database and other modules
        if 'api' in organized:
            api_id = organized['api']
            if 'database' in organized:
                lines.append(f'    {api_id} --> {organized["database"]}')
            if 'conversion' in organized:
                lines.append(f'    {api_id} --> {organized["conversion"]}')
        
        # Connect pipeline to stages
        if 'pipeline' in organized:
            pipeline_id = organized['pipeline']
            for stage in ['conversion', 'calibration', 'imaging']:
                if stage in organized:
                    lines.append(f'    {pipeline_id} --> {organized[stage]}')
        
        # Connect utils to other modules
        if 'utils' in organized:
            utils_id = organized['utils']
            for module in ['conversion', 'calibration', 'imaging']:
                if module in organized:
                    lines.append(f'    {utils_id} --> {organized[module]}')
    
    def _add_styling(self, lines: List[str], root_id: str):
        """Add color styling to nodes."""
        colors = {
            'api': '#ffeb3b',
            'conversion': '#4caf50',
            'calibration': '#ff9800',
            'imaging': '#9c27b0',
            'database': '#f44336',
            'catalog': '#00bcd4',
            'photometry': '#8bc34a',
            'pipeline': '#ff5722',
            'utils': '#607d8b',
        }
        
        lines.append('')
        lines.append(f'    style {root_id} fill:#e1f5ff')
        
        for module, color in colors.items():
            node_id = self._sanitize_id(module)
            lines.append(f'    style {node_id} fill:{color}')


def render_to_svg(mermaid_code: str, output_file: str) -> bool:
    """Render Mermaid diagram to SVG using mermaid.ink API."""
    # Base64 encode the Mermaid code
    mermaid_bytes = mermaid_code.encode('utf-8')
    encoded = base64.urlsafe_b64encode(mermaid_bytes).decode('utf-8').rstrip('=')
    
    # Use mermaid.ink API with base64
    url = f"https://mermaid.ink/svg/{encoded}"
    
    try:
        print(f"Rendering diagram to SVG...")
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            svg_content = response.read().decode('utf-8')
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        print(f":check: SVG saved to: {output_file}")
        return True
    except Exception as e:
        print(f":cross: Error rendering SVG: {e}", file=sys.stderr)
        # Save as Mermaid file as fallback
        mermaid_file = output_file.replace('.svg', '.mmd')
        with open(mermaid_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print(f"  Saved Mermaid source to: {mermaid_file}", file=sys.stderr)
        print(f"  You can convert it manually using: https://mermaid.live/", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python generate_structure_diagram.py <directory_path> [output.svg]", file=sys.stderr)
        print("\nExample:")
        print("  python generate_structure_diagram.py /data/dsa110-contimg/backend backend_structure.svg")
        print("  python generate_structure_diagram.py /data/dsa110-contimg/frontend frontend_structure.svg")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else f"{Path(directory_path).name}_structure.svg"
    
    try:
        # Analyze directory
        print(f"Analyzing directory: {directory_path}")
        analyzer = DirectoryAnalyzer(directory_path)
        analyzer.analyze()
        
        # Generate Mermaid code
        print("Generating Mermaid diagram...")
        mermaid_code = analyzer.generate_mermaid()
        
        # Optionally save Mermaid source
        mermaid_file = output_file.replace('.svg', '.mmd')
        with open(mermaid_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        print(f":check: Mermaid source saved to: {mermaid_file}")
        
        # Render to SVG
        success = render_to_svg(mermaid_code, output_file)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f":cross: Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
