#!/usr/bin/env python3
"""
Multi-Language File Sharder v2.0
=================================

A tool for breaking down large source code files into smaller, manageable shards
for easier analysis by AI language models like Claude, ChatGPT, and others.

Supported Languages:
-------------------
* Python (.py) - Full AST-based parsing
* C++ (.cpp, .cxx, .cc, .hpp, .h) - Regex-based parsing with C++ syntax awareness

Purpose:
--------
Large source files can be difficult for AI assistants to process effectively due to
context window limitations. This tool intelligently breaks down source files
into smaller "shards" based on logical groupings, while maintaining the relationships
between components and preserving imports/dependencies.

Features:
---------
* Multi-language support with language-specific parsers
* Multiple sharding strategies (by type, name pattern, docstring, or even distribution)
* Smart detection of functions, classes, and methods
* Preservation of imports and global variables across all shards
* Enhanced index with detailed function metadata (parameters, return types)
* Automatic file type detection
* Language-specific output directories and naming
* User-friendly interface with Rich library support (when available)

Output Structure:
----------------
For each processed file, creates:
* Language-specific directory: "{filename}_{lang}_shards_{timestamp}/"
* Multiple source files (shards) with portions of the original code
* Enhanced index: "{filename}_{lang}_index_{timestamp}.json"
* README.md with usage instructions

Usage:
------
1. Run the script: `python multi_language_sharder.py`
2. Follow the interactive prompts to:
   - Specify the source file to shard
   - Select an output directory
   - Choose a sharding strategy
   - Set the maximum elements per shard

The script automatically detects file type and applies appropriate parsing.

Using with AI Assistants (CRITICAL):
------------------------------------
When using the sharded files with AI assistants:

1. Upload the language-specific index file first to give the AI an overview
2. CRITICAL: Explicitly instruct the AI that "this index is complete and
   contains ALL existing elements in this specific source file" to prevent
   hallucination of non-existent functions or classes
3. Instruct the AI to use the index to request specific shards by filename
   if there is any need to drill down
4. Upload relevant shards as needed for detailed analysis

Requirements:
------------
* Python 3.9+
* Rich library (optional, will be installed if user agrees)

Author: Enhanced for multi-language support
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
from abc import ABC, abstractmethod
from pathlib import Path

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

# Language detection and file type mappings
SUPPORTED_LANGUAGES = {
    'python': {
        'extensions': ['.py'],
        'name': 'Python',
        'comment_style': '#'
    },
    'cpp': {
        'extensions': ['.cpp', '.cxx', '.cc', '.hpp', '.h'],
        'name': 'C++',
        'comment_style': '//'
    }
}


def check_and_install_requirements():
    """
    Check and install required packages if needed.

    Detects if the Rich library is available, and if not, offers to install it.
    Rich provides enhanced terminal output with colors, tables, and progress bars.

    Returns:
        bool: True if all requirements are satisfied, False otherwise
    """
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


def detect_language(file_path: str) -> Optional[str]:
    """
    Detect the programming language based on file extension.

    Args:
        file_path (str): Path to the source file

    Returns:
        Optional[str]: Language identifier if supported, None otherwise
    """
    file_ext = Path(file_path).suffix.lower()

    for lang_id, lang_info in SUPPORTED_LANGUAGES.items():
        if file_ext in lang_info['extensions']:
            return lang_id

    return None


def get_supported_extensions() -> List[str]:
    """
    Get a list of all supported file extensions.

    Returns:
        List[str]: List of supported file extensions
    """
    extensions = []
    for lang_info in SUPPORTED_LANGUAGES.values():
        extensions.extend(lang_info['extensions'])
    return sorted(extensions)


# Abstract base class for language parsers
class LanguageParser(ABC):
    """
    Abstract base class for language-specific parsers.

    Each supported language should implement this interface to provide
    consistent parsing capabilities across different source code languages.
    """

    def __init__(self, language_id: str):
        """
        Initialize the parser with language information.

        Args:
            language_id (str): Identifier for the programming language
        """
        self.language_id = language_id
        self.language_info = SUPPORTED_LANGUAGES[language_id]

    @abstractmethod
    def parse_file(self, file_path: str) -> Tuple[Any, str]:
        """
        Parse a source file and return parsed representation and source code.

        Args:
            file_path (str): Path to the source file

        Returns:
            Tuple[Any, str]: Parsed representation and source code
        """
        pass

    @abstractmethod
    def extract_imports_and_globals(self, parsed_content: Any, source: str) -> str:
        """
        Extract imports and global definitions for inclusion in each shard.

        Args:
            parsed_content (Any): Parsed representation of the source
            source (str): Original source code

        Returns:
            str: String containing imports and global definitions
        """
        pass

    @abstractmethod
    def extract_code_elements(self, parsed_content: Any, source: str) -> Dict[str, List[Dict]]:
        """
        Extract all code elements (functions, classes, etc.) with metadata.

        Args:
            parsed_content (Any): Parsed representation of the source
            source (str): Original source code

        Returns:
            Dict[str, List[Dict]]: Dictionary mapping element types to lists of elements
        """
        pass


class PythonParser(LanguageParser):
    """
    Python-specific parser using AST (Abstract Syntax Tree) analysis.

    Provides comprehensive parsing of Python source code including functions,
    classes, methods, and detailed metadata extraction.
    """

    def parse_file(self, file_path: str) -> Tuple[ast.Module, str]:
        """
        Parse a Python file using AST and return the tree and source code.

        Args:
            file_path (str): Path to the Python file

        Returns:
            Tuple[ast.Module, str]: AST tree and source code

        Raises:
            SyntaxError: If the file contains syntax errors
            Exception: For other errors reading the file
        """
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

    def extract_imports_and_globals(self, tree: ast.Module, source: str) -> str:
        """
        Extract all imports and global variables to include in each shard.

        This ensures each shard has the necessary imports and global constants
        to function properly when analyzed in isolation.

        Args:
            tree (ast.Module): The AST of the Python file
            source (str): The source code of the Python file

        Returns:
            str: A string containing all imports and global variable definitions
        """
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
            imports_and_globals.extend(source_lines[start - 1:end])
            imports_and_globals.append("")  # Add blank line

        return "\n".join(imports_and_globals)

    def extract_code_elements(self, tree: ast.Module, source: str) -> Dict[str, List[Dict]]:
        """
        Extract all code elements (functions, classes, etc.) with metadata.

        Analyzes the Python AST to identify and categorize different code elements
        along with their metadata (docstrings, decorators, parameters, etc.).

        Args:
            tree (ast.Module): The AST of the Python file
            source (str): The source code of the Python file

        Returns:
            Dict[str, List[Dict]]: A dictionary mapping element types to lists of elements
        """
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
                parameters = self._extract_parameters_from_source(function_source)
                return_type = self._extract_return_type_from_source(function_source)

                elements['functions'].append({
                    'name': node.name,
                    'source': function_source,
                    'docstring': ast.get_docstring(node) or "",
                    'decorators': [self._extract_decorator_name(d) for d in node.decorator_list],
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
                        parameters = self._extract_parameters_from_source(method_source)
                        return_type = self._extract_return_type_from_source(method_source)

                        method_info = {
                            'name': f"{node.name}.{item.name}",
                            'method_name': item.name,
                            'class_name': node.name,
                            'source': method_source,
                            'docstring': ast.get_docstring(item) or "",
                            'decorators': [self._extract_decorator_name(d) for d in item.decorator_list],
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
                    'decorators': [self._extract_decorator_name(d) for d in node.decorator_list],
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

    def _extract_decorator_name(self, decorator: ast.expr) -> str:
        """
        Extract the name of a decorator from its AST node.

        Args:
            decorator (ast.expr): The AST node representing the decorator

        Returns:
            str: The name of the decorator as a string
        """
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._extract_attribute_name(decorator)}"
        return "unknown_decorator"

    def _extract_attribute_name(self, attr: ast.Attribute) -> str:
        """
        Extract the full name of an attribute (e.g., module.submodule.function).

        Args:
            attr (ast.Attribute): The AST attribute node

        Returns:
            str: The fully qualified attribute name
        """
        if isinstance(attr.value, ast.Name):
            return f"{attr.value.id}.{attr.attr}"
        elif isinstance(attr.value, ast.Attribute):
            return f"{self._extract_attribute_name(attr.value)}.{attr.attr}"
        return f"?.{attr.attr}"

    def _extract_parameters_from_source(self, source_code: str) -> List[Dict[str, str]]:
        """
        Extract parameter information from function source code.

        Parses the function signature to extract parameter names and their
        type annotations if available.

        Args:
            source_code (str): The function's source code

        Returns:
            List[Dict[str, str]]: A list of parameter dictionaries with 'name' and 'type' keys
        """
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
                    next_lines = lines[current_idx + 1:]
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

    def _extract_return_type_from_source(self, source_code: str) -> str:
        """
        Extract return type information from function source code.

        Looks for the return type annotation in the function signature.

        Args:
            source_code (str): The function's source code

        Returns:
            str: The return type annotation or empty string if none found
        """
        # Check for return type annotation
        lines = source_code.split('\n')
        for line in lines:
            if "->" in line and re.match(r'\s*def\s+\w+\s*\(', line):
                # Extract return type
                return_match = re.search(r'->\s*([\w\[\],\s\.\'"]+)(?:\s*:)?', line)
                if return_match:
                    return return_match.group(1).strip()

        return ""


class CppParser(LanguageParser):
    """
    C++ parser using regex-based analysis.

    Provides parsing of C++ source code including functions, classes, methods,
    namespaces, and templates with detailed metadata extraction suitable for
    AI assistant analysis.
    """

    def parse_file(self, file_path: str) -> Tuple[str, str]:
        """
        Parse a C++ file and return the content.

        For C++, we return the source twice since we're using regex-based parsing
        rather than building an AST.

        Args:
            file_path (str): Path to the C++ file

        Returns:
            Tuple[str, str]: Source content (returned twice for API consistency)

        Raises:
            Exception: For errors reading the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            return source, source
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            raise

    def extract_imports_and_globals(self, source: str, _: str) -> str:
        """
        Extract includes, defines, and global declarations.

        Args:
            source (str): The C++ source code
            _ (str): Unused parameter for API consistency

        Returns:
            str: String containing includes and global definitions
        """
        includes_and_globals = []
        lines = source.splitlines()

        for line in lines:
            stripped = line.strip()
            # Include directives
            if stripped.startswith('#include'):
                includes_and_globals.append(line)
            # Preprocessor defines
            elif stripped.startswith('#define'):
                includes_and_globals.append(line)
            # Using declarations
            elif stripped.startswith('using '):
                includes_and_globals.append(line)
            # Forward declarations (simple heuristic)
            elif (stripped.startswith('class ') and stripped.endswith(';')) or \
                    (stripped.startswith('struct ') and stripped.endswith(';')):
                includes_and_globals.append(line)
            # Typedef declarations
            elif stripped.startswith('typedef '):
                includes_and_globals.append(line)
            # Global constants (simple heuristic)
            elif re.match(r'^\s*(const|static|extern)\s+', line):
                includes_and_globals.append(line)

        if includes_and_globals:
            includes_and_globals.append("")  # Add blank line

        return "\n".join(includes_and_globals)

    def extract_code_elements(self, source: str, _: str) -> Dict[str, List[Dict]]:
        """
        Extract C++ code elements using regex patterns.

        Args:
            source (str): The C++ source code
            _ (str): Unused parameter for API consistency

        Returns:
            Dict[str, List[Dict]]: Dictionary mapping element types to lists of elements
        """
        elements = {
            'functions': [],
            'classes': [],
            'methods': [],
            'constants': [],
            'namespaces': [],
            'templates': [],
            'module_code': []
        }

        lines = source.splitlines()
        processed_lines = set()

        # Extract namespaces
        namespace_pattern = r'^\s*namespace\s+(\w+)\s*\{'
        for i, line in enumerate(lines):
            if match := re.match(namespace_pattern, line):
                namespace_name = match.group(1)
                # Find the end of the namespace (simplified)
                start_line = i
                brace_count = 1
                end_line = i

                for j in range(i + 1, len(lines)):
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    if brace_count == 0:
                        end_line = j
                        break

                namespace_source = '\n'.join(lines[start_line:end_line + 1])
                elements['namespaces'].append({
                    'name': namespace_name,
                    'source': namespace_source,
                    'lineno': i + 1
                })

                for k in range(start_line, end_line + 1):
                    processed_lines.add(k)

        # Extract classes
        class_pattern = r'^\s*(class|struct)\s+(\w+)(?:\s*:\s*[^{]*)?(?:\s*\{)?'
        for i, line in enumerate(lines):
            if i in processed_lines:
                continue

            if match := re.match(class_pattern, line):
                class_type = match.group(1)
                class_name = match.group(2)

                # Find the complete class definition
                start_line = i
                if '{' in line:
                    brace_count = line.count('{') - line.count('}')
                    end_line = i

                    for j in range(i + 1, len(lines)):
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count == 0:
                            end_line = j
                            break
                else:
                    # Look for opening brace on next lines
                    end_line = i
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if '{' in lines[j]:
                            brace_count = lines[j].count('{') - lines[j].count('}')
                            for k in range(j + 1, len(lines)):
                                brace_count += lines[k].count('{') - lines[k].count('}')
                                if brace_count == 0:
                                    end_line = k
                                    break
                            break

                class_source = '\n'.join(lines[start_line:end_line + 1])

                # Extract methods from this class
                class_methods = self._extract_class_methods(class_source, class_name, start_line)

                elements['classes'].append({
                    'name': class_name,
                    'type': class_type,
                    'source': class_source,
                    'methods': class_methods,
                    'lineno': i + 1
                })

                # Add methods to the methods list
                elements['methods'].extend(class_methods)

                for k in range(start_line, end_line + 1):
                    processed_lines.add(k)

        # Extract standalone functions
        function_pattern = r'^\s*(?:(?:static|inline|virtual|explicit|constexpr)\s+)*(?:\w+(?:\s*\*|\s*&)?(?:\s*::\s*\w+)*\s+)+(\w+)\s*\([^)]*\)(?:\s*const)?(?:\s*override)?(?:\s*final)?(?:\s*noexcept)?(?:\s*\{|;)'
        for i, line in enumerate(lines):
            if i in processed_lines:
                continue

            if match := re.match(function_pattern, line):
                func_name = match.group(1)

                # Skip obvious non-functions
                if func_name in ['if', 'for', 'while', 'switch', 'catch']:
                    continue

                start_line = i
                end_line = i

                # If function has body (contains {)
                if '{' in line:
                    brace_count = line.count('{') - line.count('}')

                    for j in range(i + 1, len(lines)):
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count == 0:
                            end_line = j
                            break
                else:
                    # Function declaration only (ends with ;)
                    if ';' in line:
                        end_line = i
                    else:
                        # Look for ; on next few lines
                        for j in range(i + 1, min(i + 3, len(lines))):
                            if ';' in lines[j]:
                                end_line = j
                                break

                func_source = '\n'.join(lines[start_line:end_line + 1])

                # Extract function metadata
                parameters = self._extract_cpp_parameters(func_source)
                return_type = self._extract_cpp_return_type(func_source)

                elements['functions'].append({
                    'name': func_name,
                    'source': func_source,
                    'parameters': parameters,
                    'return_type': return_type,
                    'lineno': i + 1
                })

                for k in range(start_line, end_line + 1):
                    processed_lines.add(k)

        # Extract templates
        template_pattern = r'^\s*template\s*<[^>]*>\s*'
        for i, line in enumerate(lines):
            if i in processed_lines:
                continue

            if re.match(template_pattern, line):
                # Find the templated declaration (next non-empty line typically)
                start_line = i
                end_line = i

                # Look for the actual template definition
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith('//'):
                        # Found the templated item, now find its end
                        if '{' in lines[j]:
                            brace_count = lines[j].count('{') - lines[j].count('}')
                            end_line = j

                            for k in range(j + 1, len(lines)):
                                brace_count += lines[k].count('{') - lines[k].count('}')
                                if brace_count == 0:
                                    end_line = k
                                    break
                        elif ';' in lines[j]:
                            end_line = j
                        break

                template_source = '\n'.join(lines[start_line:end_line + 1])

                # Extract template name (simplified)
                template_name = "template"
                if 'class ' in template_source or 'struct ' in template_source:
                    class_match = re.search(r'(?:class|struct)\s+(\w+)', template_source)
                    if class_match:
                        template_name = f"template<{class_match.group(1)}>"
                elif 'function' in template_source or '(' in template_source:
                    func_match = re.search(r'(\w+)\s*\(', template_source)
                    if func_match:
                        template_name = f"template<{func_match.group(1)}>"

                elements['templates'].append({
                    'name': template_name,
                    'source': template_source,
                    'lineno': i + 1
                })

                for k in range(start_line, end_line + 1):
                    processed_lines.add(k)

        # Extract constants and global variables
        const_pattern = r'^\s*(?:const|static|extern)\s+.*?(\w+)(?:\s*=.*?)?;'
        for i, line in enumerate(lines):
            if i in processed_lines:
                continue

            if match := re.match(const_pattern, line):
                const_name = match.group(1)
                elements['constants'].append({
                    'name': const_name,
                    'source': line,
                    'lineno': i + 1
                })
                processed_lines.add(i)

        # Collect remaining lines as module code
        for i, line in enumerate(lines):
            if i not in processed_lines and line.strip() and not line.strip().startswith('//'):
                elements['module_code'].append({
                    'source': line,
                    'lineno': i + 1
                })

        return elements

    def _extract_class_methods(self, class_source: str, class_name: str, class_start_line: int) -> List[Dict]:
        """
        Extract methods from a C++ class definition.

        Args:
            class_source (str): The complete class source code
            class_name (str): Name of the class
            class_start_line (int): Starting line number of the class

        Returns:
            List[Dict]: List of method information dictionaries
        """
        methods = []
        lines = class_source.splitlines()

        # Look for method definitions within the class
        method_pattern = r'^\s*(?:(?:public|private|protected):\s*)?(?:(?:static|virtual|inline|explicit|constexpr)\s+)*(?:\w+(?:\s*\*|\s*&)?(?:\s*::\s*\w+)*\s+)*(\w+)\s*\([^)]*\)(?:\s*const)?(?:\s*override)?(?:\s*final)?(?:\s*noexcept)?(?:\s*\{|;)'

        for i, line in enumerate(lines):
            if match := re.match(method_pattern, line):
                method_name = match.group(1)

                # Skip constructors, destructors, and obvious non-methods
                if method_name == class_name or method_name == f"~{class_name}" or \
                        method_name in ['if', 'for', 'while', 'switch', 'catch']:
                    continue

                start_line = i
                end_line = i

                # Find method body if it exists
                if '{' in line:
                    brace_count = line.count('{') - line.count('}')

                    for j in range(i + 1, len(lines)):
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count == 0:
                            end_line = j
                            break

                method_source = '\n'.join(lines[start_line:end_line + 1])

                # Extract method metadata
                parameters = self._extract_cpp_parameters(method_source)
                return_type = self._extract_cpp_return_type(method_source)

                methods.append({
                    'name': f"{class_name}::{method_name}",
                    'method_name': method_name,
                    'class_name': class_name,
                    'source': method_source,
                    'parameters': parameters,
                    'return_type': return_type,
                    'lineno': class_start_line + i + 1
                })

        return methods

    def _extract_cpp_parameters(self, source_code: str) -> List[Dict[str, str]]:
        """
        Extract parameter information from C++ function source code.

        Args:
            source_code (str): The function's source code

        Returns:
            List[Dict[str, str]]: List of parameter dictionaries with 'name' and 'type' keys
        """
        parameters = []

        # Find the parameter list
        param_match = re.search(r'\(([^)]*)\)', source_code)
        if not param_match:
            return parameters

        param_text = param_match.group(1).strip()
        if not param_text:
            return parameters

        # Split parameters by comma, being careful about template parameters
        param_items = []
        bracket_level = 0
        current_param = ""

        for char in param_text:
            if char == ',' and bracket_level == 0:
                param_items.append(current_param.strip())
                current_param = ""
            else:
                current_param += char
                if char in '<(':
                    bracket_level += 1
                elif char in '>)':
                    bracket_level -= 1

        if current_param:
            param_items.append(current_param.strip())

        # Parse each parameter
        for param in param_items:
            if not param:
                continue

            # Remove default values - FIXED LINE
            param = re.sub(r'\s*=\s*[^,]*$', '', param)

            # Extract type and name
            # Simple heuristic: last word is typically the parameter name
            words = param.split()
            if len(words) >= 2:
                param_name = words[-1]
                # Remove * and & from name if present
                param_name = param_name.lstrip('*&')
                param_type = ' '.join(words[:-1])

                parameters.append({
                    'name': param_name,
                    'type': param_type
                })
            elif len(words) == 1:
                # Just a type, no name (like in declarations)
                parameters.append({
                    'name': '',
                    'type': words[0]
                })

        return parameters

    def _extract_cpp_return_type(self, source_code: str) -> str:
        """
        Extract return type information from C++ function source code.

        Args:
            source_code (str): The function's source code

        Returns:
            str: The return type or empty string if not found
        """
        # Look for the function signature
        lines = source_code.splitlines()
        for line in lines:
            # Skip preprocessor directives and comments
            if line.strip().startswith('#') or line.strip().startswith('//'):
                continue

            # Look for function signature pattern
            func_match = re.match(r'^\s*(?:(?:static|inline|virtual|explicit|constexpr)\s+)*(.*?)\s+(\w+)\s*\(', line)
            if func_match:
                return_type = func_match.group(1).strip()
                # Clean up common prefixes that aren't part of return type
                return_type = re.sub(r'^(?:public|private|protected)\s*:\s*', '', return_type)
                return return_type

        return ""


def _sanitize_filename(name: str) -> str:
    """
    Convert a string to a valid filename by replacing non-alphanumeric characters.

    Args:
        name (str): The string to sanitize

    Returns:
        str: A sanitized string safe to use as a filename
    """
    # Replace non-alphanumeric with underscores
    return re.sub(r'[^\w]', '_', name)


def get_parser(language_id: str) -> LanguageParser:
    """
    Get the appropriate parser for a given language.

    Args:
        language_id (str): The language identifier

    Returns:
        LanguageParser: The parser instance for the language

    Raises:
        ValueError: If the language is not supported
    """
    if language_id == 'python':
        return PythonParser(language_id)
    elif language_id == 'cpp':
        return CppParser(language_id)
    else:
        raise ValueError(f"Unsupported language: {language_id}")


# Clustering functions (language-agnostic)
def cluster_by_type(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """
    Group code elements by their type (functions, classes, methods, etc.).

    Args:
        elements (Dict[str, List[Dict]]): The extracted code elements
        max_elements_per_shard (int): Maximum number of elements per shard

    Returns:
        Dict[str, List[Dict]]: Clusters of elements grouped by type
    """
    clusters = {}

    # Group each element type, potentially splitting into multiple clusters
    for element_type, element_list in elements.items():
        if not element_list:
            continue

        if len(element_list) <= max_elements_per_shard:
            clusters[element_type] = element_list
        else:
            # Split into multiple clusters
            for i in range(0, len(element_list), max_elements_per_shard):
                chunk = element_list[i:i + max_elements_per_shard]
                clusters[f'{element_type}_{i // max_elements_per_shard + 1}'] = chunk

    return clusters


def cluster_by_name_prefix(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """
    Group code elements by common prefixes/patterns in their names.

    Args:
        elements (Dict[str, List[Dict]]): The extracted code elements
        max_elements_per_shard (int): Maximum number of elements per shard

    Returns:
        Dict[str, List[Dict]]: Clusters of elements grouped by name prefixes
    """
    clusters = {}

    # Process functions
    if elements.get('functions'):
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
                    clusters[f'{prefix}_{i // max_elements_per_shard + 1}'] = chunk

    # Process methods similarly to functions
    if elements.get('methods'):
        method_prefixes = defaultdict(list)
        for method in elements['methods']:
            name = method.get('method_name', method['name'])

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
                    clusters[f'{prefix}_{i // max_elements_per_shard + 1}'] = chunk

    # Process classes
    if elements.get('classes'):
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
                    clusters[f'{prefix}_{i // max_elements_per_shard + 1}'] = chunk

    # Add other element types
    for element_type in ['constants', 'namespaces', 'templates', 'module_code']:
        if elements.get(element_type):
            clusters[element_type] = elements[element_type]

    return clusters


def cluster_by_docstring(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """
    Group code elements based on similarity in their docstrings/comments.

    Args:
        elements (Dict[str, List[Dict]]): The extracted code elements
        max_elements_per_shard (int): Maximum number of elements per shard

    Returns:
        Dict[str, List[Dict]]: Clusters of elements grouped by docstring themes
    """
    clusters = {}

    # Keywords to look for in docstrings/comments
    common_keywords = [
        'create', 'update', 'delete', 'get', 'list', 'find', 'search',
        'validate', 'process', 'handle', 'calculate', 'compute', 'generate',
        'parse', 'format', 'convert', 'transform', 'check', 'verify',
        'api', 'helper', 'utility', 'core', 'main', 'initialize',
        'settings', 'config', 'database', 'model', 'view', 'controller',
        'error', 'exception', 'event', 'callback', 'hook', 'send'
    ]

    # Process functions
    if elements.get('functions'):
        func_themes = defaultdict(list)
        for func in elements['functions']:
            docstring = func.get('docstring', '').lower()
            # For C++, also check the source for comments
            source_comments = re.findall(r'//.*?$|/\*.*?\*/', func.get('source', ''), re.MULTILINE | re.DOTALL)
            comment_text = ' '.join(source_comments).lower()

            text_to_search = docstring + ' ' + comment_text
            found_keywords = []

            for keyword in common_keywords:
                if keyword in text_to_search:
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
                    clusters[f'{theme}_{i // max_elements_per_shard + 1}'] = chunk

    # Process methods similarly
    if elements.get('methods'):
        method_themes = defaultdict(list)
        for method in elements['methods']:
            docstring = method.get('docstring', '').lower()
            source_comments = re.findall(r'//.*?$|/\*.*?\*/', method.get('source', ''), re.MULTILINE | re.DOTALL)
            comment_text = ' '.join(source_comments).lower()
            class_name = method.get('class_name', '')

            text_to_search = docstring + ' ' + comment_text
            found_keywords = []

            for keyword in common_keywords:
                if keyword in text_to_search:
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
                    clusters[f'{theme}_{i // max_elements_per_shard + 1}'] = chunk

    # Process classes
    if elements.get('classes'):
        class_themes = defaultdict(list)
        for cls in elements['classes']:
            docstring = cls.get('docstring', '').lower()
            source_comments = re.findall(r'//.*?$|/\*.*?\*/', cls.get('source', ''), re.MULTILINE | re.DOTALL)
            comment_text = ' '.join(source_comments).lower()

            text_to_search = docstring + ' ' + comment_text
            found_keywords = []

            for keyword in common_keywords:
                if keyword in text_to_search:
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
                    clusters[f'{theme}_{i // max_elements_per_shard + 1}'] = chunk

    # Add other element types
    for element_type in ['constants', 'namespaces', 'templates', 'module_code']:
        if elements.get(element_type):
            clusters[element_type] = elements[element_type]

    return clusters


def cluster_evenly(elements: Dict[str, List[Dict]], max_elements_per_shard: int) -> Dict[str, List[Dict]]:
    """
    Distribute code elements evenly across shards.

    Handle large classes by breaking up their methods into separate shards.

    Args:
        elements (Dict[str, List[Dict]]): The extracted code elements
        max_elements_per_shard (int): Maximum number of elements per shard

    Returns:
        Dict[str, List[Dict]]: Clusters of elements distributed evenly
    """
    clusters = {}

    # Check if we have a single large class dominating the file
    if len(elements.get('classes', [])) == 1 and len(elements.get('methods', [])) > max_elements_per_shard:
        # Extract the class and its methods
        the_class = elements['classes'][0]
        methods = elements['methods']

        # Create a shard for the class definition (without methods)
        class_def = the_class.copy()
        # For C++, we'll include the full class for now since method extraction is more complex
        clusters['class_definition'] = [class_def]

        # Group methods by prefix or logical groups
        method_groups = defaultdict(list)
        for method in methods:
            # Extract method name without class prefix
            method_name = method.get('method_name', method['name'])

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
        combined.extend(elements.get('functions', []))
        combined.extend(elements.get('classes', []))
        combined.extend(elements.get('namespaces', []))
        combined.extend(elements.get('templates', []))

        # Sort by line number for deterministic grouping
        combined.sort(key=lambda x: x.get('lineno', 0))

        # Split into even chunks
        for i in range(0, len(combined), max_elements_per_shard):
            chunk = combined[i:i + max_elements_per_shard]
            clusters[f'chunk_{i // max_elements_per_shard + 1}'] = chunk

    # Add other element types separately
    for element_type in ['constants', 'module_code']:
        if elements.get(element_type):
            clusters[element_type] = elements[element_type]

    return clusters


def create_shards(
        elements: Dict[str, List[Dict]],
        imports_and_globals: str,
        strategy: str,
        max_elements_per_shard: int,
        output_dir: str,
        source_filename: str,
        language_id: str
) -> int:
    """
    Create shards using the chosen strategy.

    Args:
        elements (Dict[str, List[Dict]]): The extracted code elements
        imports_and_globals (str): Global imports and constants to include in each shard
        strategy (str): Sharding strategy to use ("by_type", "name_prefix", "docstring", "even")
        max_elements_per_shard (int): Maximum number of elements per shard
        output_dir (str): Output directory for the shards
        source_filename (str): Name of the source file being sharded
        language_id (str): Programming language identifier

    Returns:
        int: The number of shards created
    """
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

    # Get file extension for the language
    lang_info = SUPPORTED_LANGUAGES[language_id]
    file_extension = lang_info['extensions'][0]  # Use the first extension as default

    # Process clusters
    for i, (cluster_name, elements_list) in enumerate(clusters.items()):
        _write_shard(cluster_name, elements_list, imports_and_globals, output_dir,
                     i + 1, source_filename, language_id, file_extension)

    # Create an index file
    _create_element_index(clusters, output_dir, source_filename, language_id)

    # Create a README with instructions
    _create_readme(output_dir, len(clusters), strategy_name, source_filename, language_id)

    return len(clusters)


def _write_shard(
        cluster_name: str,
        elements_list: List[Dict],
        imports_and_globals: str,
        output_dir: str,
        shard_index: int,
        source_filename: str,
        language_id: str,
        file_extension: str
) -> None:
    """
    Write a single shard file.

    Args:
        cluster_name (str): Name of the cluster
        elements_list (List[Dict]): List of code elements in this shard
        imports_and_globals (str): Global imports and constants to include
        output_dir (str): Output directory
        shard_index (int): Index of this shard
        source_filename (str): Name of the original source file
        language_id (str): Programming language identifier
        file_extension (str): File extension for the language
    """
    # Create shard file name with language and source info
    safe_name = _sanitize_filename(cluster_name)
    base_name = Path(source_filename).stem
    file_name = f"{base_name}_{language_id}_shard_{shard_index:03d}_{safe_name}{file_extension}"
    file_path = os.path.join(output_dir, file_name)

    # Get comment style for the language
    comment_style = SUPPORTED_LANGUAGES[language_id]['comment_style']

    # Write shard
    with open(file_path, 'w', encoding='utf-8') as f:
        # Add header with shard information
        f.write(f"{comment_style} Shard {shard_index} - {cluster_name}\n")
        f.write(f"{comment_style} From {SUPPORTED_LANGUAGES[language_id]['name']} file: {source_filename}\n")
        f.write(f"{comment_style} Contains {len(elements_list)} elements\n\n")

        # Add imports and globals
        if imports_and_globals.strip():
            f.write(imports_and_globals + "\n\n")

        # For method shards, include a comment indicating methods belong to a class
        methods_in_shard = any(element.get('class_name') for element in elements_list if 'class_name' in element)
        class_names = set(element.get('class_name') for element in elements_list if 'class_name' in element)

        if methods_in_shard and 'methods' in cluster_name:
            f.write(f"{comment_style} These methods belong to the {', '.join(class_names)} class(es)\n")
            f.write(f"{comment_style} The full class definition can be found in the class_definition shard\n\n")

        # Add code elements sorted by line number
        if cluster_name == 'module_code':
            # For module-level code, maintain the original line ordering
            for element in sorted(elements_list, key=lambda x: x.get('lineno', 0)):
                f.write(element['source'] + "\n")
        else:
            # For functions, classes, etc.
            for element in sorted(elements_list, key=lambda x: x.get('lineno', 0)):
                f.write(element['source'] + "\n\n")


def _create_element_index(clusters: Dict, output_dir: str, source_filename: str, language_id: str) -> Dict:
    """
    Create an enhanced index mapping element names to their metadata.

    This index is crucial for AI assistants to understand the structure
    of the codebase without hallucinating non-existent elements.

    Args:
        clusters (Dict): Clusters of code elements
        output_dir (str): Output directory for the index
        source_filename (str): Name of the original source file
        language_id (str): Programming language identifier

    Returns:
        Dict: The created index
    """
    index = {}
    base_name = Path(source_filename).stem

    for i, (cluster_name, elements_list) in enumerate(clusters.items()):
        safe_name = _sanitize_filename(cluster_name)
        file_extension = SUPPORTED_LANGUAGES[language_id]['extensions'][0]
        file_name = f"{base_name}_{language_id}_shard_{i + 1:03d}_{safe_name}{file_extension}"

        for element in elements_list:
            if 'name' in element:
                # Create detailed entry structure
                entry = {
                    "shard": file_name,
                    "language": language_id,
                    "element_type": cluster_name.split('_')[0] if '_' in cluster_name else cluster_name
                }

                # Extract parameters if available
                if 'parameters' in element and element['parameters']:
                    entry["parameters"] = element['parameters']

                # Extract return type if available
                if 'return_type' in element and element['return_type']:
                    entry["return_type"] = element['return_type']

                # Add C++-specific metadata
                if language_id == 'cpp':
                    if 'type' in element:  # For classes (class vs struct)
                        entry["cpp_type"] = element['type']

                # Add entry to index
                index[element['name']] = entry

    # Create index file name with language and source info
    index_filename = f"{base_name}_{language_id}_index_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    # Write index file
    with open(os.path.join(output_dir, index_filename), 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, sort_keys=True)

    return index


def _create_readme(output_dir: str, num_shards: int, strategy: str, source_filename: str, language_id: str) -> None:
    """
    Create a README file with instructions for using the shards with AI assistants.

    Args:
        output_dir (str): Output directory
        num_shards (int): Number of shards created
        strategy (str): Sharding strategy used
        source_filename (str): Name of the original source file
        language_id (str): Programming language identifier
    """
    base_name = Path(source_filename).stem
    lang_name = SUPPORTED_LANGUAGES[language_id]['name']

    with open(os.path.join(output_dir, "README.md"), 'w', encoding='utf-8') as f:
        f.write(f"# {lang_name} Shards - {source_filename}\n\n")
        f.write(
            f"This directory contains {num_shards} shards of {lang_name} code from `{source_filename}` grouped by {strategy}.\n\n")

        f.write("## How to use with AI assistants\n\n")
        f.write("1. **Upload the index.json file first**\n")
        f.write(
            f"   - The index contains a complete map of all functions, classes, and methods from {source_filename}\n")
        f.write(
            "   - IMPORTANT: Tell the AI that \"this index is complete and contains ALL existing elements in this specific source file\"\n")
        f.write("   - This prevents the AI from hallucinating non-existent functions or classes\n\n")

        f.write("2. **Upload shards in logical groups**\n")
        f.write("   - Start with the most relevant shards for your questions\n")
        f.write("   - Not all shards need to be uploaded at once\n\n")

        f.write("3. **Reference the index to find specific elements**\n")
        f.write("   - Use the index to locate which shard contains a function you want to examine\n")
        f.write("   - The index includes parameter and return type information\n\n")

        f.write("4. **Ask the AI to analyze specific shards**\n")
        f.write("   - Request explanations of functions, classes, or their relationships\n")
        f.write("   - The AI can help you understand the code structure\n\n")

        if language_id == 'cpp':
            f.write("## C++-specific tips\n\n")
            f.write(
                "- Header files (.h/.hpp) contain declarations; implementation files (.cpp/.cc) contain definitions\n")
            f.write("- Template instantiations may appear in multiple files\n")
            f.write("- Namespace usage affects how symbols are resolved\n")
            f.write("- Forward declarations create dependencies between files\n\n")

        f.write("## Tips for effective code analysis\n\n")
        f.write("- Ask for an overall description of the code structure and purpose\n")
        f.write("- Request explanations of specific functions or classes\n")
        f.write("- Have the AI identify connections between different components\n")
        f.write("- Request diagrams for complex relationships or workflows\n")
        f.write("- Ask for usage examples\n")
        f.write("- Request code reviews to identify potential bugs or improvements\n")
        f.write("- For complex multi-step operations, ask the AI to explain the flow\n\n")

        f.write("## Preventing AI hallucination\n\n")
        f.write("To prevent the AI from inventing non-existent code elements:\n\n")
        f.write("1. **Always upload the index.json file first**\n")
        f.write(
            "2. **Explicitly instruct the AI that \"this index is complete and contains ALL existing code elements from this specific file\"**\n")
        f.write("3. **If the AI mentions a function not in the index, remind it to check the index**\n")
        f.write("4. **Ask the AI to verify claims against the available code**\n")


# Improved rich-based user interface
def display_rich_interface():
    """
    Display a rich-based interface for the multi-language file sharding tool.

    Provides a user-friendly, colorful interface for the user to interact with
    the sharding process when the Rich library is available.

    Returns:
        bool: True if the sharding process was successful, False otherwise
    """
    if not RICH_AVAILABLE or not console:
        return False

    # Display welcome screen
    console.print("\n")
    console.print(Panel(
        "This tool helps you break down large source code files into manageable shards\n"
        "for easier analysis by AI assistants and other code analysis tools.\n\n"
        f"Supported languages: {', '.join(lang_info['name'] for lang_info in SUPPORTED_LANGUAGES.values())}\n"
        f"Supported file types: {', '.join(get_supported_extensions())}\n\n"
        "Features:\n"
        "• Automatic language detection\n"
        "• Multiple sharding strategies\n"
        "• Smart detection of functions, classes, and methods\n"
        "• Language-specific parsing and metadata extraction\n"
        "• Enhanced index with parameter and return type information\n"
        "• Maintains imports and dependencies\n",
        title="Multi-Language File Sharding Tool v2.0",
        border_style="blue",
        width=80
    ))
    console.print("\n")

    # Get user inputs
    file_path = ""
    while not file_path:
        file_path = Prompt.ask("Enter the path to your source code file")
        # Expand home directory if path starts with ~
        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            console.print(f"[red]Error:[/] '{file_path}' is not a valid file. Please try again.")
            file_path = ""
            continue

        # Check if file type is supported
        language_id = detect_language(file_path)
        if not language_id:
            console.print(
                f"[red]Error:[/] File type not supported. Supported extensions: {', '.join(get_supported_extensions())}")
            file_path = ""
            continue

    output_dir = Prompt.ask("Enter the target directory for shards", default="shards")
    # Expand home directory if path starts with ~
    output_dir = os.path.expanduser(output_dir)

    # Display detected language
    lang_name = SUPPORTED_LANGUAGES[language_id]['name']
    console.print(f"\n[green]Detected language:[/] {lang_name}")

    # Parse and analyze the source file
    console.print(f"\nAnalyzing [cyan]{file_path}[/]...")

    try:
        parser = get_parser(language_id)
        parsed_content, source = parser.parse_file(file_path)
        imports_and_globals = parser.extract_imports_and_globals(parsed_content, source)
        elements = parser.extract_code_elements(parsed_content, source)

        # Display file analysis
        element_counts = {k: len(v) for k, v in elements.items() if v}

        console.print(f"\n[bold blue]{lang_name} File Analysis:[/]")

        table = Table(title="Code Elements", show_header=True, header_style="bold cyan")
        table.add_column("Element Type", style="dim")
        table.add_column("Count", justify="right")

        for element_type, count in element_counts.items():
            if count > 0:
                # Capitalize and format element type name
                display_name = element_type.replace('_', ' ').title()
                table.add_row(display_name, str(count))

        console.print(table)

        # Check if we have any code elements
        total_elements = sum(
            len(elements[key]) for key in ['functions', 'classes', 'namespaces', 'templates'] if key in elements)
        if total_elements == 0:
            console.print(f"[yellow]No major code elements found in the file.[/]")
            console.print("The file may contain only module-level code or data.")

            if len(elements.get('module_code', [])) > 0:
                console.print(f"Found {len(elements['module_code'])} lines of module-level code.")
                console.print("Creating a single shard for this file...")

                # Create a timestamped subfolder
                source_filename = os.path.basename(file_path)
                base_name = Path(source_filename).stem
                current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                final_output_dir = os.path.join(output_dir, f"{base_name}_{language_id}_shards_{current_time}")

                os.makedirs(final_output_dir, exist_ok=True)
                file_extension = SUPPORTED_LANGUAGES[language_id]['extensions'][0]
                with open(
                        os.path.join(final_output_dir, f"{base_name}_{language_id}_shard_001_complete{file_extension}"),
                        'w') as f:
                    f.write(f"// Complete {lang_name} file: {source_filename}\n\n")
                    f.write(source)

                console.print(f"[green]Created single shard in {os.path.abspath(final_output_dir)}[/]")
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
        strategies_table.add_row("3", "Group by comments/docs", "Group by semantic similarity")
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
        base_name = Path(source_filename).stem
        current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        final_output_dir = os.path.join(output_dir, f"{base_name}_{language_id}_shards_{current_time}")

        # Create shards
        with console.status(f"Creating shards in [cyan]{final_output_dir}[/]...", spinner="dots"):
            num_shards = create_shards(
                elements,
                imports_and_globals,
                selected_strategy,
                max_per_shard,
                final_output_dir,
                source_filename,
                language_id
            )

            strategy_name = {
                "by_type": "element types",
                "name_prefix": "name patterns",
                "docstring": "comment themes",
                "even": "even distribution"
            }[selected_strategy]

        # Display completion message
        console.print("\n[bold green]Sharding complete![/]")

        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Property", style="bold blue")
        summary_table.add_column("Value", style="cyan")

        summary_table.add_row("Language", lang_name)
        summary_table.add_row("Source file", source_filename)
        summary_table.add_row("Output directory", os.path.abspath(final_output_dir))
        summary_table.add_row("Strategy", strategy_name)
        summary_table.add_row("Number of shards", str(num_shards))

        console.print(Panel(summary_table, title="Summary", border_style="green"))
        console.print(f"\n[italic]Your {lang_name} file has been successfully sharded with enhanced metadata![/]")

        # Add specific instructions about preventing hallucination
        console.print(Panel(
            "[bold]IMPORTANT: Using with AI Assistants[/]\n\n"
            "1. Upload the language-specific index.json file first\n"
            "2. Tell the AI: [green]\"This index is complete and contains ALL existing elements from this specific source file\"[/]\n"
            "3. This prevents the AI from hallucinating non-existent functions or classes\n"
            "4. Then upload specific shards as needed for detailed analysis\n"
            "5. When working with multiple files, keep indices separate to maintain accuracy",
            title="Preventing AI Hallucination",
            border_style="red",
            width=80
        ))

        return True

    except Exception as e:
        console.print(f"[red]Error during sharding:[/] {e}")
        return False


# Command line interface for systems without Rich
def command_line_interface():
    """
    Run the command line interface for systems without Rich.

    Provides a text-based interface when the Rich library is not available.
    """
    print("\n=== Multi-Language File Sharding Tool v2.0 ===\n")
    print("This tool helps you break down large source code files into manageable shards.")
    print(f"Supported languages: {', '.join(lang_info['name'] for lang_info in SUPPORTED_LANGUAGES.values())}")
    print(f"Supported file types: {', '.join(get_supported_extensions())}")
    print("Enhanced with detailed metadata in the index.json output.\n")

    # Get user inputs
    while True:
        file_path = input("Enter the path to your source code file: ")
        # Expand home directory if path starts with ~
        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            print(f"Error: '{file_path}' is not a valid file. Please try again.")
            continue

        # Check if file type is supported
        language_id = detect_language(file_path)
        if not language_id:
            print(f"Error: File type not supported. Supported extensions: {', '.join(get_supported_extensions())}")
            continue

        break

    # Get target directory
    target_dir = input("Enter the target directory for shards (default: 'shards'): ")
    # Expand home directory if path starts with ~
    if target_dir:
        target_dir = os.path.expanduser(target_dir)
    else:
        target_dir = "shards"

    # Display detected language
    lang_name = SUPPORTED_LANGUAGES[language_id]['name']
    print(f"\nDetected language: {lang_name}")

    # Parse and analyze the source file
    print(f"\nAnalyzing {file_path}...")
    try:
        parser = get_parser(language_id)
        parsed_content, source = parser.parse_file(file_path)
        imports_and_globals = parser.extract_imports_and_globals(parsed_content, source)
        elements = parser.extract_code_elements(parsed_content, source)
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return

    # Display file analysis
    element_counts = {k: len(v) for k, v in elements.items() if v}
    print(f"\nFound elements in the {lang_name} file:")
    for element_type, count in element_counts.items():
        if count > 0:
            display_name = element_type.replace('_', ' ').title()
            print(f"  {display_name}: {count}")

    # Check if we have any code elements
    total_elements = sum(
        len(elements[key]) for key in ['functions', 'classes', 'namespaces', 'templates'] if key in elements)
    if total_elements == 0:
        print("No major code elements found in the file.")
        print("The file may contain only module-level code or data.")

        if len(elements.get('module_code', [])) > 0:
            print(f"Found {len(elements['module_code'])} lines of module-level code.")
            print("Creating a single shard for this file...")

            # Create a timestamped subfolder
            source_filename = os.path.basename(file_path)
            base_name = Path(source_filename).stem
            current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            output_dir = os.path.join(target_dir, f"{base_name}_{language_id}_shards_{current_time}")

            os.makedirs(output_dir, exist_ok=True)
            file_extension = SUPPORTED_LANGUAGES[language_id]['extensions'][0]
            comment_style = SUPPORTED_LANGUAGES[language_id]['comment_style']
            with open(os.path.join(output_dir, f"{base_name}_{language_id}_shard_001_complete{file_extension}"),
                      'w') as f:
                f.write(f"{comment_style} Complete {lang_name} file: {source_filename}\n\n")
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
    print("3. Group by comments/docstring similarity")
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
            max_per_shard = int(input(f"Enter maximum elements per shard [{suggested_size}]: ") or suggested_size)
            if max_per_shard < 1:
                print("Maximum must be at least 1.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")

    # Create a timestamped subfolder
    source_filename = os.path.basename(file_path)
    base_name = Path(source_filename).stem
    current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join(target_dir, f"{base_name}_{language_id}_shards_{current_time}")

    # Create shards
    try:
        strategy_name = {
            "by_type": "element types",
            "name_prefix": "name patterns",
            "docstring": "comment themes",
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
            source_filename,
            language_id
        )

        print("\nSharding complete!")
        print(f"Language: {lang_name}")
        print(f"Source file: {source_filename}")
        print(f"Output directory: {os.path.abspath(output_dir)}")
        print(f"Strategy used: {strategy_name}")
        print(f"Number of shards: {num_shards}")
        print(f"\nIndex includes enhanced metadata with parameter and return type information.")

        print("\n=== IMPORTANT: Using with AI Assistants ===")
        print("1. Upload the language-specific index.json file first")
        print(
            "2. Tell the AI: \"This index is complete and contains ALL existing elements from this specific source file\"")
        print("3. This prevents the AI from hallucinating non-existent functions or classes")
        print("4. Then upload specific shards as needed for detailed analysis")
        print("5. When working with multiple files, keep indices separate to maintain accuracy")

    except Exception as e:
        print(f"Error during sharding: {e}")


def main():
    """
    Main function to start the application.

    Checks for required dependencies and launches the appropriate interface.
    Automatically detects file types and applies appropriate parsing strategies.
    """
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
