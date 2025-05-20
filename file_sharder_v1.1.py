#!/usr/bin/env python3
"""
Python File Sharder v1.1
------------------------
Tool for breaking down large Python files into smaller, manageable shards 
for easier analysis by AI assistants.

Enhanced with detailed function metadata in the index.json output.
"""

import ast
import os
import re
import sys
import subprocess
import textwrap
import datetime
import json
from collections import defaultdict
from typing import List, Dict, Tuple, Set, Optional, Union, Any

# Initialize variables for rich library components
RICH_AVAILABLE = False
console = None

# Try to import rich library components
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False

def check_and_install_requirements():
    """Check and install required packages if needed."""
    global RICH_AVAILABLE, console
    
    required_packages = []
    if not RICH_AVAILABLE:
        required_packages.append('rich')
    
    if required_packages:
        print(f"The following required packages are missing: {', '.join(required_packages)}")
        install = input("Do you want to install them now? (y/n): ").lower() == 'y'
        
        if install:
            print("Installing packages...")
            try:
                for package in required_packages:
                    print(f"Installing {package}...")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                        print(f"Successfully installed {package}")
                    except subprocess.CalledProcessError as e:
                        print(f"Error installing {package}: {e}")
                        print("\nTrying alternate installation methods...")
                        
                        # Try with --user flag for pip
                        try:
                            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
                            print(f"Successfully installed {package} with --user flag")
                        except subprocess.CalledProcessError:
                            print("Installation with pip failed.")
                            print("Please install manually with:")
                            print(f"  pip install --user {package}")
                            print("or")
                            print(f"  sudo apt install python3-{package}")
                            return False
                
                # Try importing rich again after installation
                try:
                    from rich.console import Console
                    from rich.panel import Panel
                    from rich.table import Table
                    from rich.prompt import Prompt, Confirm
                    from rich.markdown import Markdown
                    from rich.syntax import Syntax
                    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
                    RICH_AVAILABLE = True
                    console = Console()
                    print("Rich library successfully imported.")
                except ImportError:
                    print("Failed to import Rich library after installation.")
                    RICH_AVAILABLE = False
            except Exception as e:
                print(f"Error during installation: {e}")
                return False
        else:
            print("Required packages not installed. Continuing with basic text interface.")
            return False
    return True

# Helper functions for file parsing and analysis
def _extract_decorator_name(decorator: ast.expr) -> str:
    """Extract the name of a decorator."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
        return decorator.func.id
    elif isinstance(decorator, ast.Attribute):
        return f"{_extract_attribute_name(decorator)}"
    return "unknown_decorator"

def _extract_attribute_name(attr: ast.Attribute) -> str:
    """Extract the full name of an attribute."""
    if isinstance(attr.value, ast.Name):
        return f"{attr.value.id}.{attr.attr}"
    elif isinstance(attr.value, ast.Attribute):
        return f"{_extract_attribute_name(attr.value)}.{attr.attr}"
    return f"?.{attr.attr}"

def _sanitize_filename(name: str) -> str:
    """Convert a string to a valid filename."""
    # Replace non-alphanumeric with underscores
    return re.sub(r'[^\w]', '_', name)

def _extract_parameters_from_source(source_code: str) -> List[Dict[str, str]]:
    """Extract parameter information from function source code."""
    # Find the function definition line with parameters
    lines = source_code.split('\n')
    def_line = ""
    for line in lines:
        if re.match(r'\s*def\s+\w+\s*\(', line):
            def_line = line
            # Check if the parameter list continues to next lines
            param_end_idx = -1
            if def_line.count('(') > def_line.count(')'):
                current_idx = lines.index(line)
                next_lines = lines[current_idx+1:]
                param_end_idx = current_idx  # Start with the current line
                
                for i, next_line in enumerate(next_lines):
                    def_line += " " + next_line.strip()
                    param_end_idx = current_idx + i + 1
                    if def_line.count('(') <= def_line.count(')'):
                        break
            break
    
    if not def_line:
        return []
    
    # Extract parameter text from the definition
    param_text = re.search(r'\(\s*(.*?)\s*\)', def_line)
    if not param_text:
        return []
    
    param_text = param_text.group(1)
    if not param_text:
        return []
    
    # Parse each parameter
    parameters = []
    # Split by commas, but be careful about nested types like List[str, int]
    param_items = []
    bracket_level = 0
    current_param = ""
    
    for char in param_text:
        if char == ',' and bracket_level == 0:
            param_items.append(current_param.strip())
            current_param = ""
        else:
            current_param += char
            if char == '[':
                bracket_level += 1
            elif char == ']':
                bracket_level -= 1
    
    if current_param:  # Add the last parameter
        param_items.append(current_param.strip())
    
    for item in param_items:
        if not item or item == 'self':
            continue
            
        # Extract name and type annotation if present
        param_dict = {}
        type_match = re.match(r'(\w+)\s*:\s*([\w\[\],\s\.\'"]+)', item)
        if type_match:
            param_dict["name"] = type_match.group(1)
            param_dict["type"] = type_match.group(2).strip()
        else:
            # No type annotation, just the name (possibly with default value)
            name_match = re.match(r'(\w+)(?:\s*=\s*.*)?', item)
            if name_match:
                param_dict["name"] = name_match.group(1)
                param_dict["type"] = ""
        
        if param_dict:
            parameters.append(param_dict)
    
    return parameters

def _extract_return_type_from_source(source_code: str) -> str:
    """Extract return type information from function source code."""
    # Check for return type annotation
    lines = source_code.split('\n')
    for line in lines:
        if "->" in line and re.match(r'\s*def\s+\w+\s*\(', line):
            # Extract return type
            return_match = re.search(r'->\s*([\w\[\],\s\.\'"]+)(?:\s*:)?', line)
            if return_match:
                return return_match.group(1).strip()
    
    return ""

# Core logic functions
def parse_python_file(file_path: str) -> Tuple[ast.Module, str]:
    """Parse a Python file and return the AST and source code."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        return ast.parse(source), source
    except SyntaxError as e:
        print(f"Error parsing {file_path}: {e}")
        raise
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        raise

def extract_imports_and_globals(tree: ast.Module, source: str) -> str:
    """Extract all imports and global variables to include in each shard."""
    imports_and_globals = []
    line_numbers = []
    
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) or (
            isinstance(node, ast.Assign) and all(
                isinstance(target, ast.Name) for target in node.targets
            )
        ) or isinstance(node, (ast.AnnAssign, ast.ClassDef, ast.TypeAlias)):
            # Check if it's a constant or type definition
            is_constant = False
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        is_constant = True
                        break
            
            # Only include constants and type definitions in imports_and_globals
            if (isinstance(node, (ast.Import, ast.ImportFrom)) or 
                is_constant or 
                isinstance(node, (ast.AnnAssign, ast.TypeAlias))):
                line_numbers.append((node.lineno, getattr(node, 'end_lineno', node.lineno)))
    
    if not line_numbers:
        return ""
    
    # Sort by line number
    line_numbers.sort()
    
    # Extract lines from source
    source_lines = source.splitlines()
    for start, end in line_numbers:
        # Adjust for 0-indexed lines in list vs 1-indexed in AST
        imports_and_globals.extend(source_lines[start-1:end])
        imports_and_globals.append("")  # Add blank line
    
    return "\n".join(imports_and_globals)

def extract_all_code_elements(tree: ast.Module, source: str) -> Dict[str, List[Dict]]:
    """Extract all code elements (functions, classes, etc.) with metadata."""
    elements = {
        'functions': [],
        'classes': [],
        'methods': [],
        'constants': [],
        'module_code': []
    }
    
    source_lines = source.splitlines()
    processed_line_ranges = set()
    
    # Extract top-level functions
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
            processed_line_ranges.add((start_line, end_line))
            
            # Extract function source
            function_source = '\n'.join(source_lines[start_line:end_line])
            
            # Extract parameter and return info
            parameters = _extract_parameters_from_source(function_source)
            return_type = _extract_return_type_from_source(function_source)
            
            elements['functions'].append({
                'name': node.name,
                'source': function_source,
                'docstring': ast.get_docstring(node) or "",
                'decorators': [_extract_decorator_name(d) for d in node.decorator_list],
                'parameters': parameters,
                'return_type': return_type,
                'lineno': node.lineno
            })
    
    # Extract classes and their methods
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
            processed_line_ranges.add((start_line, end_line))
            
            class_methods = []
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_start = item.lineno - 1
                    method_end = item.end_lineno if hasattr(item, 'end_lineno') else method_start
                    
                    # Extract method source
                    method_source = '\n'.join(source_lines[method_start:method_end])
                    
                    # Extract parameter and return info
                    parameters = _extract_parameters_from_source(method_source)
                    return_type = _extract_return_type_from_source(method_source)
                    
                    method_info = {
                        'name': f"{node.name}.{item.name}",
                        'method_name': item.name,
                        'class_name': node.name,
                        'source': method_source,
                        'docstring': ast.get_docstring(item) or "",
                        'decorators': [_extract_decorator_name(d) for d in item.decorator_list],
                        'parameters': parameters,
                        'return_type': return_type,
                        'lineno': item.lineno
                    }
                    class_methods.append(method_info)
                    elements['methods'].append(method_info)
            
            elements['classes'].append({
                'name': node.name,
                'source': '\n'.join(source_lines[start_line:end_line]),
                'docstring': ast.get_docstring(node) or "",
                'methods': class_methods,
                'decorators': [_extract_decorator_name(d) for d in node.decorator_list],
                'lineno': node.lineno
            })
    
    # Extract constants (uppercase variable assignments)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                    processed_line_ranges.add((start_line, end_line))
                    
                    elements['constants'].append({
                        'name': target.id,
                        'source': '\n'.join(source_lines[start_line:end_line]),
                        'lineno': node.lineno
                    })
    
    # Collect module-level code not part of functions or classes
    for i, line in enumerate(source_lines):
        if all(not (start <= i <= end) for start, end in processed_line_ranges) and line.strip():
            elements['module_code'].append({
                'source': line,
                'lineno': i + 1
            })
    
    return elements

def cluster_by_type(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """Group code elements by their type."""
    clusters = {}
    
    # Group functions, potentially splitting into multiple clusters
    if elements['functions']:
        functions = elements['functions']
        if len(functions) <= max_elements_per_shard:
            clusters['functions'] = functions
        else:
            # Split into multiple clusters
            for i in range(0, len(functions), max_elements_per_shard):
                chunk = functions[i:i + max_elements_per_shard]
                clusters[f'functions_{i//max_elements_per_shard + 1}'] = chunk
    
    # Group classes, potentially splitting into multiple clusters
    if elements['classes']:
        classes = elements['classes']
        if len(classes) <= max_elements_per_shard:
            clusters['classes'] = classes
        else:
            # Split into multiple clusters
            for i in range(0, len(classes), max_elements_per_shard):
                chunk = classes[i:i + max_elements_per_shard]
                clusters[f'classes_{i//max_elements_per_shard + 1}'] = chunk
    
    # Group methods if there are many of them
    if elements['methods']:
        methods = elements['methods']
        if len(methods) <= max_elements_per_shard:
            clusters['methods'] = methods
        else:
            # Group methods by their class
            class_methods = defaultdict(list)
            for method in methods:
                class_name = method.get('class_name', 'unknown')
                class_methods[f'methods_{class_name}'].append(method)
            
            # Split large class method groups if needed
            for class_name, methods_list in class_methods.items():
                if len(methods_list) <= max_elements_per_shard:
                    clusters[class_name] = methods_list
                else:
                    for i in range(0, len(methods_list), max_elements_per_shard):
                        chunk = methods_list[i:i + max_elements_per_shard]
                        clusters[f'{class_name}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Group constants if any
    if elements['constants']:
        clusters['constants'] = elements['constants']
    
    # Module-level code
    if elements['module_code']:
        clusters['module_code'] = elements['module_code']
    
    return clusters

def cluster_by_name_prefix(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """Group code elements by common prefixes/patterns in their names."""
    clusters = {}
    
    # Process functions
    if elements['functions']:
        func_prefixes = defaultdict(list)
        for func in elements['functions']:
            name = func['name']
            # Try different prefix patterns
            if match := re.match(r'^([a-z]+_)', name):
                prefix = match.group(1)
            elif match := re.match(r'^([a-z]+[A-Z][a-z]*)', name):
                prefix = match.group(1)
            elif len(name) >= 3:
                prefix = name[:3]
            else:
                prefix = 'other'
            
            func_prefixes[f'func_{prefix}'].append(func)
        
        # Split large clusters if needed
        for prefix, funcs in func_prefixes.items():
            if len(funcs) <= max_elements_per_shard:
                clusters[prefix] = funcs
            else:
                for i in range(0, len(funcs), max_elements_per_shard):
                    chunk = funcs[i:i + max_elements_per_shard]
                    clusters[f'{prefix}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Process methods similarly to functions
    if elements['methods']:
        method_prefixes = defaultdict(list)
        for method in elements['methods']:
            name = method['method_name']  # Use just the method name without class prefix
            
            # Try different prefix patterns
            if match := re.match(r'^([a-z]+_)', name):
                prefix = match.group(1)
            elif match := re.match(r'^([a-z]+[A-Z][a-z]*)', name):
                prefix = match.group(1)
            elif len(name) >= 3:
                prefix = name[:3]
            else:
                prefix = 'other'
            
            # Include class name in the group to avoid mixing methods from different classes
            class_name = method.get('class_name', '')
            group_key = f'method_{class_name}_{prefix}'
            method_prefixes[group_key].append(method)
        
        # Split large clusters if needed
        for prefix, methods in method_prefixes.items():
            if len(methods) <= max_elements_per_shard:
                clusters[prefix] = methods
            else:
                for i in range(0, len(methods), max_elements_per_shard):
                    chunk = methods[i:i + max_elements_per_shard]
                    clusters[f'{prefix}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Process classes
    if elements['classes']:
        class_prefixes = defaultdict(list)
        for cls in elements['classes']:
            name = cls['name']
            # Try to find a meaningful prefix
            if match := re.match(r'^([A-Z][a-z]+)', name):
                prefix = match.group(1)
            elif len(name) >= 3:
                prefix = name[:3]
            else:
                prefix = 'other'
            
            class_prefixes[f'class_{prefix}'].append(cls)
        
        # Split large clusters if needed
        for prefix, classes in class_prefixes.items():
            if len(classes) <= max_elements_per_shard:
                clusters[prefix] = classes
            else:
                for i in range(0, len(classes), max_elements_per_shard):
                    chunk = classes[i:i + max_elements_per_shard]
                    clusters[f'{prefix}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Add constants
    if elements['constants']:
        clusters['constants'] = elements['constants']
    
    # Add module code
    if elements['module_code']:
        clusters['module_code'] = elements['module_code']
    
    return clusters

def cluster_by_docstring(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """Group code elements based on similarity in their docstrings."""
    clusters = {}
    
    # Keywords to look for in docstrings
    common_keywords = [
        'create', 'update', 'delete', 'get', 'list', 'find', 'search',
        'validate', 'process', 'handle', 'calculate', 'compute', 'generate',
        'parse', 'format', 'convert', 'transform', 'check', 'verify',
        'api', 'helper', 'utility', 'core', 'main', 'initialize',
        'settings', 'config', 'database', 'model', 'view', 'controller',
        'error', 'exception', 'event', 'callback', 'hook'
    ]
    
    # Process functions
    if elements['functions']:
        func_themes = defaultdict(list)
        for func in elements['functions']:
            docstring = func['docstring'].lower()
            found_keywords = []
            
            for keyword in common_keywords:
                if keyword in docstring:
                    found_keywords.append(keyword)
            
            if found_keywords:
                theme = found_keywords[0]  # Use the first keyword found
                func_themes[f'func_{theme}'].append(func)
            else:
                func_themes['func_other'].append(func)
        
        # Split large clusters if needed
        for theme, funcs in func_themes.items():
            if len(funcs) <= max_elements_per_shard:
                clusters[theme] = funcs
            else:
                for i in range(0, len(funcs), max_elements_per_shard):
                    chunk = funcs[i:i + max_elements_per_shard]
                    clusters[f'{theme}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Process methods similarly
    if elements['methods']:
        method_themes = defaultdict(list)
        for method in elements['methods']:
            docstring = method['docstring'].lower()
            found_keywords = []
            class_name = method.get('class_name', '')
            
            for keyword in common_keywords:
                if keyword in docstring:
                    found_keywords.append(keyword)
            
            if found_keywords:
                theme = found_keywords[0]  # Use the first keyword found
                method_themes[f'method_{class_name}_{theme}'].append(method)
            else:
                method_themes[f'method_{class_name}_other'].append(method)
        
        # Split large clusters if needed
        for theme, methods in method_themes.items():
            if len(methods) <= max_elements_per_shard:
                clusters[theme] = methods
            else:
                for i in range(0, len(methods), max_elements_per_shard):
                    chunk = methods[i:i + max_elements_per_shard]
                    clusters[f'{theme}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Process classes
    if elements['classes']:
        class_themes = defaultdict(list)
        for cls in elements['classes']:
            docstring = cls['docstring'].lower()
            found_keywords = []
            
            for keyword in common_keywords:
                if keyword in docstring:
                    found_keywords.append(keyword)
            
            if found_keywords:
                theme = found_keywords[0]  # Use the first keyword found
                class_themes[f'class_{theme}'].append(cls)
            else:
                class_themes['class_other'].append(cls)
        
        # Split large clusters if needed
        for theme, classes in class_themes.items():
            if len(classes) <= max_elements_per_shard:
                clusters[theme] = classes
            else:
                for i in range(0, len(classes), max_elements_per_shard):
                    chunk = classes[i:i + max_elements_per_shard]
                    clusters[f'{theme}_{i//max_elements_per_shard + 1}'] = chunk
    
    # Add constants
    if elements['constants']:
        clusters['constants'] = elements['constants']
    
    # Add module code
    if elements['module_code']:
        clusters['module_code'] = elements['module_code']
    
    return clusters

def cluster_evenly(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """Distribute code elements evenly across shards, handling large classes by breaking up their methods."""
    clusters = {}
    
    # Check if we have a single large class dominating the file
    if len(elements['classes']) == 1 and len(elements['methods']) > max_elements_per_shard:
        # Extract the class and its methods
        the_class = elements['classes'][0]
        methods = elements['methods']
        
        # Create a shard for the class definition (without methods)
        class_def = the_class.copy()
        # Strip out the method implementations to create a skeleton class
        class_source_lines = class_def['source'].splitlines()
        class_header_lines = []
        indent_level = None
        
        # Extract just the class definition and any class-level attributes
        for line in class_source_lines:
            if re.match(r'\s*def\s+', line):
                # Stop when we hit the first method definition
                if indent_level is None:
                    # Determine the indentation level from the first method
                    indent_match = re.match(r'(\s*)', line)
                    if indent_match:
                        indent_level = len(indent_match.group(1))
                break
            class_header_lines.append(line)
        
        # Add pass statement if the class would be empty
        if indent_level is not None and all(not line.strip() for line in class_header_lines[1:]):
            class_header_lines.append(" " * indent_level + "pass")
        
        # Join the header lines to form the class skeleton
        class_def['source'] = "\n".join(class_header_lines)
        
        # Add the class skeleton to the first shard
        clusters['class_definition'] = [class_def]
        
        # Group methods by prefix or logical groups
        method_groups = defaultdict(list)
        for method in methods:
            # Extract method name without class prefix
            method_name = method['method_name']
            
            # Try to identify logical grouping by name prefix
            if match := re.match(r'^([a-z]+_)', method_name):
                prefix = match.group(1)
            elif match := re.match(r'^([a-z]+[A-Z][a-z]*)', method_name):
                prefix = match.group(1)
            elif len(method_name) >= 3:
                prefix = method_name[:3]
            else:
                prefix = 'other'
            
            method_groups[prefix].append(method)
        
        # If we have very small groups, merge them
        merged_groups = defaultdict(list)
        current_group = []
        current_size = 0
        group_index = 1
        
        # Sort prefixes to ensure deterministic order
        for prefix in sorted(method_groups.keys()):
            methods_in_group = method_groups[prefix]
            if current_size + len(methods_in_group) <= max_elements_per_shard:
                current_group.extend(methods_in_group)
                current_size += len(methods_in_group)
            else:
                if current_group:
                    merged_groups[f'methods_{group_index}'] = current_group
                    group_index += 1
                
                # Check if this group needs to be split across multiple shards
                if len(methods_in_group) > max_elements_per_shard:
                    for i in range(0, len(methods_in_group), max_elements_per_shard):
                        chunk = methods_in_group[i:i + max_elements_per_shard]
                        merged_groups[f'methods_{group_index}'] = chunk
                        group_index += 1
                else:
                    current_group = methods_in_group
                    current_size = len(methods_in_group)
        
        # Add the last group if not empty
        if current_group:
            merged_groups[f'methods_{group_index}'] = current_group
        
        # Add method groups to clusters
        for group_name, methods_list in merged_groups.items():
            clusters[group_name] = methods_list
    else:
        # Original logic for when we don't have a dominant class
        combined = []
        combined.extend(elements['functions'])
        combined.extend(elements['classes'])
        
        # Sort by line number for deterministic grouping
        combined.sort(key=lambda x: x['lineno'])
        
        # Split into even chunks
        for i in range(0, len(combined), max_elements_per_shard):
            chunk = combined[i:i + max_elements_per_shard]
            clusters[f'chunk_{i//max_elements_per_shard + 1}'] = chunk
    
    # Add constants separately
    if elements['constants']:
        clusters['constants'] = elements['constants']
    
    # Add module code separately
    if elements['module_code']:
        clusters['module_code'] = elements['module_code']
    
    return clusters

def create_shards(
    elements: Dict[str, List[Dict]], 
    imports_and_globals: str,
    strategy: str,
    max_elements_per_shard: int,
    output_dir: str,
    module_name: str
) -> int:
    """Create shards using the chosen strategy. Returns the number of shards created."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Use the selected clustering strategy
    if strategy == "by_type":
        clusters = cluster_by_type(elements, max_elements_per_shard)
        strategy_name = "element types"
    elif strategy == "name_prefix":
        clusters = cluster_by_name_prefix(elements, max_elements_per_shard)
        strategy_name = "name patterns"
    elif strategy == "docstring":
        clusters = cluster_by_docstring(elements, max_elements_per_shard)
        strategy_name = "docstring themes"
    else:  # even distribution
        clusters = cluster_evenly(elements, max_elements_per_shard)
        strategy_name = "even distribution"
    
    # Process clusters
    for i, (cluster_name, elements_list) in enumerate(clusters.items()):
        _write_shard(cluster_name, elements_list, imports_and_globals, output_dir, i+1, module_name)
    
    # Create an index file
    _create_element_index(clusters, output_dir)
    
    # Create a README with instructions
    _create_readme(output_dir, len(clusters), strategy_name, module_name)
    
    return len(clusters)

def _write_shard(
    cluster_name: str, 
    elements_list: List[Dict], 
    imports_and_globals: str, 
    output_dir: str, 
    shard_index: int,
    module_name: str
) -> None:
    """Write a single shard file."""
    # Create shard file name
    safe_name = _sanitize_filename(cluster_name)
    file_name = f"shard_{shard_index:03d}_{safe_name}.py"
    file_path = os.path.join(output_dir, file_name)
    
    # Write shard
    with open(file_path, 'w', encoding='utf-8') as f:
        # Add header with shard information
        f.write(f"# Shard {shard_index} - {cluster_name}\n")
        f.write(f"# From module: {module_name}\n")
        f.write(f"# Contains {len(elements_list)} elements\n\n")
        
        # Add imports and globals
        f.write(imports_and_globals + "\n\n")
        
        # For method shards, include a comment indicating methods belong to a class
        methods_in_shard = any(element.get('class_name') for element in elements_list if 'class_name' in element)
        class_names = set(element.get('class_name') for element in elements_list if 'class_name' in element)
        
        if methods_in_shard and 'methods' in cluster_name:
            f.write(f"# These methods belong to the {', '.join(class_names)} class(es)\n")
            f.write("# The full class definition can be found in the class_definition shard\n\n")
        
        # Add code elements sorted by line number
        if cluster_name == 'module_code':
            # For module-level code, maintain the original line ordering
            for element in sorted(elements_list, key=lambda x: x['lineno']):
                f.write(element['source'] + "\n")
        else:
            # For functions, classes, etc.
            for element in sorted(elements_list, key=lambda x: x['lineno']):
                f.write(element['source'] + "\n\n")

def _create_element_index(clusters, output_dir):
    """Create an enhanced index mapping element names to their metadata."""
    index = {}
    
    for i, (cluster_name, elements_list) in enumerate(clusters.items()):
        file_name = f"shard_{i+1:03d}_{_sanitize_filename(cluster_name)}.py"
        
        for element in elements_list:
            if 'name' in element:
                # Create detailed entry structure
                entry = {
                    "shard": file_name,
                }
                
                # Extract parameters if available
                if 'parameters' in element and element['parameters']:
                    entry["parameters"] = element['parameters']
                
                # Extract return type if available
                if 'return_type' in element and element['return_type']:
                    entry["return_type"] = element['return_type']
                
                # Add entry to index
                index[element['name']] = entry
    
    # Write index file
    with open(os.path.join(output_dir, "index.json"), 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, sort_keys=True)
    
    return index

def _create_readme(output_dir: str, num_shards: int, strategy: str, module_name: str) -> None:
    """Create a README file with instructions for using the shards."""
    with open(os.path.join(output_dir, "README.md"), 'w', encoding='utf-8') as f:
        f.write(f"# Python Shards - {module_name}\n\n")
        f.write(f"This directory contains {num_shards} shards of Python code from `{module_name}` grouped by {strategy}.\n\n")
        f.write("## How to use with AI assistants\n\n")
        f.write("1. Start by introducing the project to the AI\n")
        f.write("2. Upload shards in logical groups\n")
        f.write("3. Use the index.json to find specific elements\n")
        f.write("4. Ask the AI to analyze specific shards for detailed explanations\n\n")
        f.write("## Tips for effective code analysis\n\n")
        f.write("- Ask for an overall description of the code structure and purpose\n")
        f.write("- Request explanations of specific functions or classes\n")
        f.write("- Have the AI identify connections between different components\n")
        f.write("- Request diagrams for complex relationships or workflows\n")
        f.write("- Ask for usage examples\n")
        f.write("- Request code reviews to identify potential bugs or improvements\n")
        f.write("- For complex multi-step operations, ask the AI to explain the flow\n")

# Improved rich-based user interface
def display_rich_interface():
    """Display a rich-based interface for the file sharding tool."""
    if not RICH_AVAILABLE or not console:
        return False
        
    # Display welcome screen
    console.print("\n")
    console.print(Panel(
        "This tool helps you break down large Python files into manageable shards\n"
        "for easier analysis by AI assistants and other code analysis tools.\n\n"
        "Features:\n"
        "• Multiple sharding strategies\n"
        "• Smart detection of functions, classes, and methods\n"
        "• Customizable shard sizes\n"
        "• Enhanced index with parameter and return type information\n"
        "• Maintains imports and dependencies\n",
        title="Python File Sharding Tool v1.1",
        border_style="blue",
        width=80
    ))
    console.print("\n")
    
    # Get user inputs
    file_path = ""
    while not file_path:
        file_path = Prompt.ask("Enter the path to your Python file")
        # Expand home directory if path starts with ~
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path) or not file_path.endswith('.py'):
            console.print(f"[red]Error:[/] '{file_path}' is not a valid Python file. Please try again.")
            file_path = ""
    
    output_dir = Prompt.ask("Enter the target directory for shards", default="shards")
    # Expand home directory if path starts with ~
    output_dir = os.path.expanduser(output_dir)
    
    # Parse and analyze the Python file
    console.print(f"\nAnalyzing [cyan]{file_path}[/]...")
    
    try:
        tree, source = parse_python_file(file_path)
        imports_and_globals = extract_imports_and_globals(tree, source)
        elements = extract_all_code_elements(tree, source)
        
        # Display file analysis
        element_counts = {k: len(v) for k, v in elements.items()}
        
        console.print("\n[bold blue]File Analysis:[/]")
        
        table = Table(title="Code Elements", show_header=True, header_style="bold cyan")
        table.add_column("Element Type", style="dim")
        table.add_column("Count", justify="right")
        
        table.add_row("Functions", str(element_counts['functions']))
        table.add_row("Classes", str(element_counts['classes']))
        table.add_row("Methods", str(element_counts['methods']))
        table.add_row("Constants", str(element_counts['constants']))
        table.add_row("Module code blocks", str(len(elements['module_code'])))
        
        console.print(table)
        
        # Check if we have any code elements
        total_elements = len(elements['functions']) + len(elements['classes'])
        if total_elements == 0:
            console.print("[yellow]No functions or classes found in the file.[/]")
            console.print("The file may contain only module-level code or data.")
            
            if len(elements['module_code']) > 0:
                console.print(f"Found {len(elements['module_code'])} lines of module-level code.")
                console.print("Creating a single shard for this file...")
                
                # Create a timestamped subfolder
                source_filename = os.path.basename(file_path)
                module_name = os.path.splitext(source_filename)[0]  # Remove .py extension
                current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                output_dir = os.path.join(output_dir, f"{module_name}-Sharded-{current_time}")
                
                os.makedirs(output_dir, exist_ok=True)
                with open(os.path.join(output_dir, f"shard_001_{_sanitize_filename(module_name)}.py"), 'w') as f:
                    f.write(f"# Module: {module_name}\n\n")
                    f.write(source)
                
                console.print(f"[green]Created single shard in {os.path.abspath(output_dir)}[/]")
                return True
            else:
                console.print("[yellow]The file appears to be empty or contains only comments.[/]")
                return False
        
        # Get sharding strategy
        console.print("\n[bold blue]Sharding Strategies:[/]")
        
        strategies_table = Table(show_header=False, box=None)
        strategies_table.add_column("Number", style="cyan", justify="right")
        strategies_table.add_column("Strategy", style="bold")
        strategies_table.add_column("Description")
        
        strategies_table.add_row("1", "Group by type", "Organize by functions, classes, etc.")
        strategies_table.add_row("2", "Group by name prefixes", "Group by common name patterns")
        strategies_table.add_row("3", "Group by docstring", "Group by semantic similarity")
        strategies_table.add_row("4", "Even distribution", "Distribute elements evenly")
        
        console.print(strategies_table)
        
        strategy = Prompt.ask("\nChoose a strategy", choices=["1", "2", "3", "4"], default="4")
        strategy_map = {
            "1": "by_type",
            "2": "name_prefix",
            "3": "docstring",
            "4": "even"
        }
        selected_strategy = strategy_map[strategy]
        
        # Suggest appropriate shard size based on file contents
        suggested_size = min(25, max(5, total_elements // 4))
        
        console.print(f"\nSuggested elements per shard: [cyan]{suggested_size}[/]")
        console.print("For effective LLM analysis, aim for 5-30 elements per shard.")
        
        max_per_shard = Prompt.ask("Enter maximum elements per shard", default=str(suggested_size))
        max_per_shard = int(max_per_shard)
        
        # Create a timestamped subfolder
        source_filename = os.path.basename(file_path)
        module_name = os.path.splitext(source_filename)[0]  # Remove .py extension
        current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        final_output_dir = os.path.join(output_dir, f"{module_name}-Sharded-{current_time}")
        
        # Create shards
        with console.status(f"Creating shards in [cyan]{final_output_dir}[/]...", spinner="dots"):
            num_shards = create_shards(
                elements,
                imports_and_globals,
                selected_strategy,
                max_per_shard,
                final_output_dir,
                module_name
            )
            
            strategy_name = {
                "by_type": "element types",
                "name_prefix": "name patterns",
                "docstring": "docstring themes",
                "even": "even distribution"
            }[selected_strategy]
        
        # Display completion message
        console.print("\n[bold green]Sharding complete![/]")
        
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Property", style="bold blue")
        summary_table.add_column("Value", style="cyan")
        
        summary_table.add_row("Module", module_name)
        summary_table.add_row("Output directory", os.path.abspath(final_output_dir))
        summary_table.add_row("Strategy", strategy_name)
        summary_table.add_row("Number of shards", str(num_shards))
        
        console.print(Panel(summary_table, title="Summary", border_style="green"))
        console.print("\n[italic]Your Python file has been successfully sharded with enhanced metadata! You can now use these shards with your favorite AI assistant.[/]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error during sharding:[/] {e}")
        return False

# Command line interface for systems without Rich
def command_line_interface():
    """Run the command line interface for systems without Rich."""
    print("\n=== Python File Sharding Tool v1.1 ===\n")
    print("This tool helps you break down large Python files into manageable shards.")
    print("Enhanced with detailed metadata in the index.json output.\n")
    
    # Get user inputs
    while True:
        file_path = input("Enter the path to your Python file: ")
        # Expand home directory if path starts with ~
        file_path = os.path.expanduser(file_path)
        if os.path.isfile(file_path) and file_path.endswith('.py'):
            break
        print(f"Error: '{file_path}' is not a valid Python file. Please try again.")
    
    # Get target directory
    target_dir = input("Enter the target directory for shards (default: 'shards'): ")
    # Expand home directory if path starts with ~
    if target_dir:
        target_dir = os.path.expanduser(target_dir)
    else:
        target_dir = "shards"
    
    # Parse and analyze the Python file
    print(f"\nAnalyzing {file_path}...")
    try:
        tree, source = parse_python_file(file_path)
        imports_and_globals = extract_imports_and_globals(tree, source)
        elements = extract_all_code_elements(tree, source)
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return
    
    # Display file analysis
    element_counts = {k: len(v) for k, v in elements.items()}
    print("\nFound elements in the file:")
    print(f"  Functions: {element_counts['functions']}")
    print(f"  Classes: {element_counts['classes']}")
    print(f"  Methods (inside classes): {element_counts['methods']}")
    print(f"  Constants: {element_counts['constants']}")
    print(f"  Module-level code blocks: {len(elements['module_code'])}")
    
    # Check if we have any code elements
    total_elements = len(elements['functions']) + len(elements['classes'])
    if total_elements == 0:
        print("No functions or classes found in the file.")
        print("The file may contain only module-level code or data.")
        
        if len(elements['module_code']) > 0:
            print(f"Found {len(elements['module_code'])} lines of module-level code.")
            print("Creating a single shard for this file...")
            
            # Create a timestamped subfolder
            source_filename = os.path.basename(file_path)
            module_name = os.path.splitext(source_filename)[0]  # Remove .py extension
            current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            output_dir = os.path.join(target_dir, f"{module_name}-Sharded-{current_time}")
            
            os.makedirs(output_dir, exist_ok=True)
            with open(os.path.join(output_dir, f"shard_001_{_sanitize_filename(module_name)}.py"), 'w') as f:
                f.write(f"# Module: {module_name}\n\n")
                f.write(source)
            
            print(f"Created single shard in {os.path.abspath(output_dir)}")
            return
        else:
            print("The file appears to be empty or contains only comments.")
            return
    
    # Get sharding strategy
    print("\nSharding Strategies:")
    print("1. Group by type (functions, classes, etc.)")
    print("2. Group by name prefixes/patterns")
    print("3. Group by docstring/comments similarity")
    print("4. Simple even distribution")
    
    while True:
        try:
            strategy = int(input("\nChoose a strategy (1-4): "))
            if 1 <= strategy <= 4:
                break
            print("Please enter a number between 1 and 4.")
        except ValueError:
            print("Please enter a valid number.")
    
    strategy_map = {
        1: "by_type",
        2: "name_prefix",
        3: "docstring",
        4: "even"
    }
    
    # Suggest appropriate shard size based on file contents
    suggested_size = min(25, max(5, total_elements // 4))
    
    print(f"\nSuggested elements per shard: {suggested_size}")
    print("For effective LLM analysis, aim for 5-30 elements per shard.")
    
    # Get maximum elements per shard
    while True:
        try:
            max_per_shard = int(input(f"Enter maximum elements per shard: "))
            if max_per_shard < 1:
                print("Maximum must be at least 1.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Create a timestamped subfolder
    source_filename = os.path.basename(file_path)
    module_name = os.path.splitext(source_filename)[0]  # Remove .py extension
    current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join(target_dir, f"{module_name}-Sharded-{current_time}")
    
    # Create shards
    try:
        strategy_name = {
            "by_type": "element types",
            "name_prefix": "name patterns",
            "docstring": "docstring themes",
            "even": "even distribution"
        }[strategy_map[strategy]]
        
        print(f"\nUsing {strategy_name} strategy:")
        print(f"\nCreating shards in {output_dir}...")
        
        num_shards = create_shards(
            elements,
            imports_and_globals,
            strategy_map[strategy],
            max_per_shard,
            output_dir,
            module_name
        )
        
        print("\nSharding complete!")
        print(f"Output directory: {os.path.abspath(output_dir)}")
        print(f"Python module: {module_name}")
        print(f"Strategy used: {strategy_name}")
        print(f"Number of shards: {num_shards}")
        print(f"\nIndex includes enhanced metadata with parameter and return type information.")
    except Exception as e:
        print(f"Error during sharding: {e}")

def main():
    """Main function to start the application."""
    # Check and install requirements
    check_and_install_requirements()
    
    # Try rich interface first, fall back to command line if needed
    if RICH_AVAILABLE:
        if not display_rich_interface():
            command_line_interface()
    else:
        command_line_interface()

if __name__ == "__main__":
    main()
