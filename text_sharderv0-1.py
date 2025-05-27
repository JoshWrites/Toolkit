#!/usr/bin/env python3
"""
Literary Text Sharder v1.0 with Msty Integration
===============================================

A tool for breaking down large literary works into intelligent shards for AI analysis.
Integrates with Msty's local AI service to automatically discover characters, themes, 
and structure without requiring cloud APIs or manual preprocessing.

Features:
---------
* Automated discovery of characters, themes, and literary elements
* Multiple sharding strategies based on discovered content
* Integration with Msty/Ollama local AI service
* Enhanced literary index with metadata
* Zero manual preprocessing required

Requirements:
------------
* Python 3.9+
* Msty app running with Llama 3.2 (or compatible model)
* requests library

Usage:
------
1. Start Msty and ensure Llama 3.2 is downloaded
2. Run: python literary_sharder.py
3. Follow prompts to select text file and options
4. Get intelligent shards ready for detailed AI analysis
"""

import json
import os
import re
import sys
import datetime
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
import requests
import time

# Try to import rich for better UI (optional)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


class MstyIntegration:
    """Handles communication with Msty's local AI service."""
    
    def __init__(self, model_name="llama3.2"):
        self.model_name = model_name
        self.base_url = "http://localhost:10000"  # Default Ollama/Msty endpoint
        self.api_url = f"{self.base_url}/api/generate"
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Msty/Ollama service is running and model is available."""
        try:
            # Check if service is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if our model is available
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            # Check for exact match or partial match (e.g., llama3.2:latest)
            for model in model_names:
                if self.model_name in model or model in self.model_name:
                    self.model_name = model  # Use the exact model name found
                    return True
            
            print(f"Warning: Model '{self.model_name}' not found.")
            print(f"Available models: {', '.join(model_names)}")
            return False
            
        except requests.exceptions.RequestException:
            return False
    
    def analyze_text(self, text: str, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Send text to Msty for analysis with retry logic."""
        if not self.available:
            return None
        
        payload = {
            "model": self.model_name,
            "prompt": f"{prompt}\n\nText to analyze:\n{text}",
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "top_p": 0.9
            }
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, json=payload, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    print(f"API error: {response.status_code}")
                    time.sleep(2)
            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
        
        return None


class LiteraryAnalyzer:
    """Handles literary text analysis and pattern discovery."""
    
    def __init__(self, msty: MstyIntegration):
        self.msty = msty
        self.discovered_elements = {
            'characters': set(),
            'themes': set(),
            'locations': set(),
            'time_periods': set(),
            'narrative_techniques': set()
        }
    
    def structural_analysis(self, text: str) -> Dict[str, any]:
        """Perform initial structural analysis without AI."""
        
        # Find chapter/section boundaries
        chapter_patterns = [
            r'^Chapter\s+\d+',
            r'^CHAPTER\s+[IVXLC]+',
            r'^Book\s+\d+',
            r'^Part\s+\d+',
            r'^Act\s+[IVXLC]+',
            r'^Scene\s+[IVXLC]+',
            r'^\d+\.',
            r'^[IVXLC]+\.',
        ]
        
        chapters = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            for pattern in chapter_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    chapters.append({
                        'title': line,
                        'line_number': i,
                        'pattern': pattern
                    })
                    break
        
        # Extract potential character names (capitalized words that appear frequently)
        potential_characters = []
        words = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        word_counts = Counter(words)
        
        # Filter for names that appear multiple times and aren't common words
        common_words = {'The', 'And', 'But', 'When', 'Where', 'What', 'Who', 'How', 'Why',
                       'This', 'That', 'These', 'Those', 'Then', 'Now', 'Here', 'There'}
        
        for word, count in word_counts.items():
            if count >= 3 and word not in common_words and len(word) >= 3:
                potential_characters.append((word, count))
        
        # Sort by frequency
        potential_characters.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'chapters': chapters,
            'total_length': len(text),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'potential_characters': potential_characters[:20],  # Top 20 candidates
            'has_dialogue': '"' in text or '"' in text or '"' in text,
            'estimated_reading_time': len(text.split()) // 250  # ~250 words per minute
        }
    
    def create_analysis_windows(self, text: str, window_size: int = 3000, overlap: int = 500) -> List[str]:
        """Create overlapping windows for AI analysis."""
        windows = []
        words = text.split()
        
        for i in range(0, len(words), window_size - overlap):
            window_words = words[i:i + window_size]
            if len(window_words) > 100:  # Skip very small windows
                windows.append(' '.join(window_words))
        
        return windows
    
    def analyze_window_for_elements(self, window: str) -> Dict[str, Set[str]]:
        """Analyze a text window to discover literary elements."""
        
        # Prompt for discovering literary elements
        prompt = """Analyze this literary text excerpt carefully. Extract and list:

1. CHARACTER NAMES: Any character names mentioned (first names, last names, titles)
2. THEMES: Major themes, concepts, or ideas explored
3. LOCATIONS: Places, settings, geographical references
4. TIME INDICATORS: Historical periods, seasons, times of day
5. NARRATIVE TECHNIQUES: Point of view, literary devices used

Format your response as a JSON object with these exact keys:
{
    "characters": ["name1", "name2"],
    "themes": ["theme1", "theme2"],
    "locations": ["place1", "place2"],
    "time_periods": ["period1", "period2"],
    "narrative_techniques": ["technique1", "technique2"]
}

Be specific and avoid generic terms. Only include elements clearly present in the text."""
        
        response = self.msty.analyze_text(window, prompt)
        
        if not response:
            return {k: set() for k in self.discovered_elements.keys()}
        
        # Try to parse JSON response
        try:
            # Clean up the response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # Convert lists to sets and clean up
                result = {}
                for key in self.discovered_elements.keys():
                    if key in parsed and isinstance(parsed[key], list):
                        # Clean and filter the items
                        cleaned_items = set()
                        for item in parsed[key]:
                            if isinstance(item, str) and len(item.strip()) > 1:
                                cleaned_items.add(item.strip())
                        result[key] = cleaned_items
                    else:
                        result[key] = set()
                
                return result
        except (json.JSONDecodeError, AttributeError):
            # Fallback: try to extract information with regex
            return self._fallback_extraction(response)
        
        return {k: set() for k in self.discovered_elements.keys()}
    
    def _fallback_extraction(self, response: str) -> Dict[str, Set[str]]:
        """Fallback method to extract elements when JSON parsing fails."""
        result = {k: set() for k in self.discovered_elements.keys()}
        
        # Try to find character names (capitalized words)
        chars = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', response)
        result['characters'] = set(chars[:10])  # Limit to avoid noise
        
        # Look for theme keywords
        theme_keywords = ['love', 'death', 'war', 'peace', 'family', 'honor', 'revenge', 
                         'power', 'freedom', 'justice', 'betrayal', 'redemption']
        for keyword in theme_keywords:
            if keyword.lower() in response.lower():
                result['themes'].add(keyword)
        
        return result
    
    def progressive_discovery(self, text: str, max_windows: int = 10) -> Dict[str, Set[str]]:
        """Progressively discover elements using sliding window analysis."""
        
        if not self.msty.available:
            print("Msty not available. Using structural analysis only.")
            return {k: set() for k in self.discovered_elements.keys()}
        
        windows = self.create_analysis_windows(text)
        
        # Limit the number of windows to analyze for efficiency
        if len(windows) > max_windows:
            # Take windows from beginning, middle, and end
            selected_windows = []
            selected_windows.extend(windows[:3])  # Beginning
            mid_point = len(windows) // 2
            selected_windows.extend(windows[mid_point-1:mid_point+2])  # Middle
            selected_windows.extend(windows[-3:])  # End
            
            # Add a few random samples
            import random
            remaining = [w for i, w in enumerate(windows) if i not in [0,1,2,mid_point-1,mid_point,mid_point+1,-3,-2,-1]]
            if remaining:
                selected_windows.extend(random.sample(remaining, min(2, len(remaining))))
                
            windows = selected_windows
        
        print(f"Analyzing {len(windows)} text windows with Llama 3.2...")
        
        # Progress tracking
        if RICH_AVAILABLE:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("Discovering literary elements...", total=len(windows))
                
                for i, window in enumerate(windows):
                    progress.update(task, description=f"Analyzing window {i+1}/{len(windows)}")
                    elements = self.analyze_window_for_elements(window)
                    
                    # Merge discovered elements
                    for key, values in elements.items():
                        self.discovered_elements[key].update(values)
                    
                    progress.advance(task)
        else:
            for i, window in enumerate(windows):
                print(f"Analyzing window {i+1}/{len(windows)}...")
                elements = self.analyze_window_for_elements(window)
                
                # Merge discovered elements
                for key, values in elements.items():
                    self.discovered_elements[key].update(values)
        
        # Filter and rank discovered elements
        return self._filter_and_rank_elements()
    
    def _filter_and_rank_elements(self) -> Dict[str, Set[str]]:
        """Filter out noise and rank discovered elements by relevance."""
        filtered = {}
        
        # Filter characters (remove common words, single letters, etc.)
        filtered_chars = set()
        common_words = {'The', 'And', 'But', 'Then', 'When', 'Where', 'What', 'This', 'That'}
        
        for char in self.discovered_elements['characters']:
            if (len(char) >= 2 and 
                char not in common_words and 
                not char.isdigit() and
                re.match(r'^[A-Za-z\s\-\'\.]+$', char)):
                filtered_chars.add(char)
        
        filtered['characters'] = filtered_chars
        
        # Filter other elements similarly
        for key in ['themes', 'locations', 'time_periods', 'narrative_techniques']:
            filtered_items = set()
            for item in self.discovered_elements[key]:
                if len(item) >= 2 and not item.isdigit():
                    filtered_items.add(item)
            filtered[key] = filtered_items
        
        return filtered


class LiterarySharder:
    """Main class for creating intelligent literary text shards."""
    
    def __init__(self):
        self.msty = MstyIntegration()
        self.analyzer = LiteraryAnalyzer(self.msty)
    
    def load_text_file(self, file_path: str) -> str:
        """Load and clean text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Basic cleaning
            text = re.sub(r'\r\n', '\n', text)  # Normalize line endings
            text = re.sub(r'\n{3,}', '\n\n', text)  # Reduce excessive line breaks
            
            return text
        except Exception as e:
            raise Exception(f"Error loading file: {e}")
    
    def create_character_based_shards(self, text: str, characters: Set[str], max_size: int = 5000) -> Dict[str, List[str]]:
        """Create shards based on character appearances."""
        shards = defaultdict(list)
        
        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_shard = []
        current_size = 0
        shard_count = 1
        
        for paragraph in paragraphs:
            # Check which characters appear in this paragraph
            paragraph_chars = []
            for char in characters:
                if char.lower() in paragraph.lower():
                    paragraph_chars.append(char)
            
            # Determine shard key based on characters present
            if paragraph_chars:
                shard_key = f"characters_{'_'.join(sorted(paragraph_chars[:2]))}"
            else:
                shard_key = "no_main_characters"
            
            # Add to current shard or start new one if too large
            if current_size + len(paragraph) > max_size and current_shard:
                shards[f"{shard_key}_{shard_count}"] = current_shard
                current_shard = [paragraph]
                current_size = len(paragraph)
                shard_count += 1
            else:
                current_shard.append(paragraph)
                current_size += len(paragraph)
        
        # Add final shard
        if current_shard:
            shards[f"final_section_{shard_count}"] = current_shard
        
        return shards
    
    def create_thematic_shards(self, text: str, themes: Set[str], max_size: int = 5000) -> Dict[str, List[str]]:
        """Create shards based on thematic content."""
        shards = defaultdict(list)
        
        # Split text into sections (by double line break or chapter markers)
        sections = re.split(r'\n\s*\n|\n(?=Chapter|\nBook|\nPart)', text)
        sections = [s.strip() for s in sections if s.strip()]
        
        for i, section in enumerate(sections):
            # Find themes present in this section
            section_themes = []
            for theme in themes:
                if theme.lower() in section.lower():
                    section_themes.append(theme)
            
            # Group by primary theme or create general sections
            if section_themes:
                primary_theme = section_themes[0]
                shard_key = f"theme_{primary_theme.replace(' ', '_')}"
            else:
                shard_key = f"general_section_{(i // 3) + 1}"
            
            # Split large sections
            if len(section) > max_size:
                chunks = [section[i:i+max_size] for i in range(0, len(section), max_size)]
                for j, chunk in enumerate(chunks):
                    shards[f"{shard_key}_part_{j+1}"].append(chunk)
            else:
                shards[shard_key].append(section)
        
        return shards
    
    def create_structural_shards(self, text: str, structure: Dict, max_size: int = 5000) -> Dict[str, List[str]]:
        """Create shards based on structural elements (chapters, acts, etc.)."""
        shards = {}
        
        if structure['chapters']:
            # Split by chapters
            lines = text.split('\n')
            current_chapter = []
            current_chapter_name = "prologue"
            
            for line_num, line in enumerate(lines):
                # Check if this line starts a new chapter
                new_chapter = None
                for chapter in structure['chapters']:
                    if chapter['line_number'] == line_num:
                        new_chapter = chapter['title']
                        break
                
                if new_chapter:
                    # Save previous chapter
                    if current_chapter:
                        chapter_text = '\n'.join(current_chapter)
                        if len(chapter_text) > max_size:
                            # Split large chapters
                            chunks = [chapter_text[i:i+max_size] for i in range(0, len(chapter_text), max_size)]
                            for i, chunk in enumerate(chunks):
                                shards[f"{self._sanitize_name(current_chapter_name)}_part_{i+1}"] = [chunk]
                        else:
                            shards[self._sanitize_name(current_chapter_name)] = [chapter_text]
                    
                    # Start new chapter
                    current_chapter = [line]
                    current_chapter_name = new_chapter
                else:
                    current_chapter.append(line)
            
            # Add final chapter
            if current_chapter:
                chapter_text = '\n'.join(current_chapter)
                shards[self._sanitize_name(current_chapter_name)] = [chapter_text]
        else:
            # No clear chapters, split by size
            sections = self._split_by_size(text, max_size)
            for i, section in enumerate(sections):
                shards[f"section_{i+1}"] = [section]
        
        return shards
    
    def _sanitize_name(self, name: str) -> str:
        """Convert a string to a valid filename."""
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:50]
    
    def _split_by_size(self, text: str, max_size: int) -> List[str]:
        """Split text into chunks of approximately max_size."""
        sections = []
        words = text.split()
        
        current_section = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) + 1 > max_size and current_section:
                sections.append(' '.join(current_section))
                current_section = [word]
                current_size = len(word)
            else:
                current_section.append(word)
                current_size += len(word) + 1
        
        if current_section:
            sections.append(' '.join(current_section))
        
        return sections
    
    def create_enhanced_index(self, shards: Dict[str, List[str]], discovered_elements: Dict[str, Set[str]], structure: Dict) -> Dict:
        """Create comprehensive index of all shards and their content."""
        
        index = {
            "metadata": {
                "created": datetime.datetime.now().isoformat(),
                "total_shards": len(shards),
                "analysis_model": self.msty.model_name if self.msty.available else "structural_only",
                "source_structure": structure
            },
            "discovered_elements": {k: list(v) for k, v in discovered_elements.items()},
            "shards": {}
        }
        
        for shard_name, shard_content in shards.items():
            content_text = '\n'.join(shard_content)
            
            # Find which elements appear in this shard
            shard_elements = {
                'characters': [],
                'themes': [],
                'locations': [],
                'time_periods': [],
                'narrative_techniques': []
            }
            
            for element_type, elements in discovered_elements.items():
                for element in elements:
                    if element.lower() in content_text.lower():
                        shard_elements[element_type].append(element)
            
            index["shards"][shard_name] = {
                "word_count": len(content_text.split()),
                "character_count": len(content_text),
                "elements_present": shard_elements,
                "preview": content_text[:200] + "..." if len(content_text) > 200 else content_text
            }
        
        return index
    
    def save_shards(self, shards: Dict[str, List[str]], index: Dict, output_dir: str, source_filename: str):
        """Save shards and index to files."""
        
        # Create timestamped output directory
        base_name = os.path.splitext(os.path.basename(source_filename))[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        final_output_dir = os.path.join(output_dir, f"{base_name}-Literary-Shards-{timestamp}")
        
        os.makedirs(final_output_dir, exist_ok=True)
        
        # Save individual shards
        for shard_name, shard_content in shards.items():
            shard_filename = f"{shard_name}.txt"
            shard_path = os.path.join(final_output_dir, shard_filename)
            
            with open(shard_path, 'w', encoding='utf-8') as f:
                f.write(f"# Literary Shard: {shard_name}\n")
                f.write(f"# Source: {source_filename}\n")
                f.write(f"# Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write('\n\n'.join(shard_content))
        
        # Save index
        index_path = os.path.join(final_output_dir, "literary_index.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        # Create README with usage instructions
        self._create_readme(final_output_dir, len(shards), source_filename, index["discovered_elements"])
        
        return final_output_dir
    
    def _create_readme(self, output_dir: str, num_shards: int, source_filename: str, discovered_elements: Dict):
        """Create README with usage instructions."""
        
        readme_content = f"""# Literary Analysis Shards - {os.path.basename(source_filename)}

This directory contains {num_shards} intelligent shards created from the literary work "{source_filename}".

## Discovered Elements

**Characters Found:** {', '.join(list(discovered_elements['characters'])[:10])}
**Major Themes:** {', '.join(list(discovered_elements['themes'])[:8])}
**Locations:** {', '.join(list(discovered_elements['locations'])[:8])}
**Time Periods:** {', '.join(list(discovered_elements['time_periods'])[:5])}

## How to Use with AI Assistants

### Step 1: Upload the Index First
- Upload `literary_index.json` to your AI assistant
- Tell the AI: "This index contains ALL elements discovered in this literary work"
- This prevents hallucination of non-existent characters or themes

### Step 2: Strategic Shard Upload
- Upload relevant shards based on your analysis goals
- For character analysis: Upload character-focused shards
- For thematic analysis: Upload theme-based shards
- For plot analysis: Upload structural/chronological shards

### Step 3: Effective Prompts
- "Analyze the relationship between [Character A] and [Character B] in these shards"
- "Trace the development of the theme of [theme] across these sections"
- "Compare the narrative style in these different parts of the work"
- "Identify symbolic elements and their evolution in these passages"

## Analysis Suggestions

- **Character Development**: Track how characters change across different shards
- **Thematic Evolution**: See how themes develop throughout the work
- **Narrative Techniques**: Compare stylistic differences between sections
- **Symbolic Analysis**: Follow symbols and motifs across the text
- **Historical Context**: Analyze time period references and cultural elements

## Preventing AI Hallucination

1. Always reference the index when asking about characters or themes
2. If the AI mentions elements not in the index, ask it to verify against available content
3. Request specific quotes and references to validate claims
4. Use the shard previews in the index to guide your analysis focus

Created with Literary Text Sharder v1.0 using Msty + Llama 3.2
"""
        
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def process_literary_work(self, file_path: str, strategy: str = "auto", max_shard_size: int = 5000, output_dir: str = "literary_shards") -> str:
        """Main method to process a literary work into intelligent shards."""
        
        print(f"Loading literary work: {file_path}")
        text = self.load_text_file(file_path)
        
        print("Performing structural analysis...")
        structure = self.analyzer.structural_analysis(text)
        
        print("Discovering literary elements with AI...")
        discovered_elements = self.analyzer.progressive_discovery(text)
        
        # Choose sharding strategy
        if strategy == "auto":
            # Automatically choose best strategy based on discovered content
            if len(discovered_elements['characters']) >= 5:
                strategy = "character"
            elif len(discovered_elements['themes']) >= 3:
                strategy = "thematic"
            else:
                strategy = "structural"
        
        print(f"Creating shards using {strategy} strategy...")
        
        if strategy == "character":
            shards = self.create_character_based_shards(text, discovered_elements['characters'], max_shard_size)
        elif strategy == "thematic":
            shards = self.create_thematic_shards(text, discovered_elements['themes'], max_shard_size)
        else:  # structural
            shards = self.create_structural_shards(text, structure, max_shard_size)
        
        print("Creating enhanced index...")
        index = self.create_enhanced_index(shards, discovered_elements, structure)
        
        print("Saving shards and index...")
        output_path = self.save_shards(shards, index, output_dir, file_path)
        
        return output_path


def display_rich_interface():
    """Rich-based user interface."""
    if not RICH_AVAILABLE:
        return False
    
    console.print(Panel(
        "Intelligent Literary Text Sharder\n\n"
        "Break down large literary works into smart, analyzable shards using AI-discovered "
        "characters, themes, and structure. Perfect for deep literary analysis with AI assistants.\n\n"
        "✨ Automatic discovery of characters and themes\n"
        "📚 Multiple intelligent sharding strategies\n" 
        "🔍 Enhanced literary index with metadata\n"
        "🤖 Integrates with Msty + Llama 3.2",
        title="Literary Sharder v1.0",
        border_style="blue"
    ))
    
    # Check Msty availability
    sharder = LiterarySharder()
    if not sharder.msty.available:
        console.print(Panel(
            "[red]⚠️  Msty/Ollama not detected![/]\n\n"
            "Please ensure:\n"
            "• Msty is running\n"
            "• Llama 3.2 model is downloaded\n"
            "• Service is accessible at localhost:11434\n\n"
            "The tool will fall back to structural analysis only.",
            title="AI Service Status",
            border_style="red"
        ))
    else:
        console.print(f"[green]✅ Connected to Msty with model: {sharder.msty.model_name}[/]")
    
    # Get user inputs
    file_path = Prompt.ask("\nEnter path to your literary text file (.txt)")
    file_path = os.path.expanduser(file_path)
    
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File '{file_path}' not found.[/]")
        return False
    
    # Sharding strategy
    console.print("\n[bold]Sharding Strategies:[/]")
    strategies_table = Table(show_header=False, box=None)
    strategies_table.add_column("Option", style="cyan")
    strategies_table.add_column("Description")
    
    strategies_table.add_row("1. Auto", "Let AI choose best strategy based on content")
    strategies_table.add_row("2. Character-based", "Group by character appearances") 
    strategies_table.add_row("3. Thematic", "Group by themes and concepts")
    strategies_table.add_row("4. Structural", "Group by chapters/sections")
    
    console.print(strategies_table)
    
    strategy_choice = Prompt.ask("\nChoose strategy", choices=["1", "2", "3", "4"], default="1")
    strategy_map = {"1": "auto", "2": "character", "3": "thematic", "4": "structural"}
    strategy = strategy_map[strategy_choice]
    
    max_size = int(Prompt.ask("Maximum shard size (characters)", default="5000"))
    output_dir = Prompt.ask("Output directory", default="literary_shards")
    output_dir = os.path.expanduser(output_dir)
    
    # Process the file
    try:
        with console.status("[bold green]Processing literary work..."):
            result_path = sharder.process_literary_work(file_path, strategy, max_size, output_dir)
        
        console.print(f"\n[bold green]✅ Success![/] Shards created in:")
        console.print(f"[cyan]{os.path.abspath(result_path)}[/]")
        
        console.print(Panel(
            "[bold]Next Steps:[/]\n\n"
            "1. Upload 'literary_index.json' to Claude first\n"
            "2. Tell Claude: 'This index contains ALL elements in this literary work'\n"
            "3. Upload relevant .txt shards for your specific analysis\n"
            "4. Ask focused questions about characters, themes, or structure",
            title="Usage Instructions",
            border_style="green"
        ))
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        return False


def command_line_interface():
    """Simple command line interface for systems without Rich."""
    print("\n=== Literary Text Sharder v1.0 ===")
    print("Intelligent sharding for large literary works")
    
    # Check Msty
    sharder = LiterarySharder()
    if sharder.msty.available:
        print(f"✅ Connected to Msty with {sharder.msty.model_name}")
    else:
        print("⚠️  Msty not detected - falling back to structural analysis")
        print("To enable AI discovery, ensure Msty is running with Llama 3.2")
    
    # Get inputs
    file_path = input("\nEnter path to your literary text file: ").strip()
    file_path = os.path.expanduser(file_path)
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return
    
    print("\nSharding Strategies:")
    print("1. Auto (recommended)")
    print("2. Character-based")
    print("3. Thematic")
    print("4. Structural")
    
    choice = input("Choose strategy (1-4, default 1): ").strip() or "1"
    strategy_map = {"1": "auto", "2": "character", "3": "thematic", "4": "structural"}
    strategy = strategy_map.get(choice, "auto")
    
    max_size = input("Maximum shard size in characters (default 5000): ").strip()
    max_size = int(max_size) if max_size.isdigit() else 5000
    
    output_dir = input("Output directory (default 'literary_shards'): ").strip() or "literary_shards"
    output_dir = os.path.expanduser(output_dir)
    
    # Process
    try:
        print("\nProcessing literary work...")
        result_path = sharder.process_literary_work(file_path, strategy, max_size, output_dir)
        
        print(f"\n✅ Success! Shards created in: {os.path.abspath(result_path)}")
        print("\nNext steps:")
        print("1. Upload 'literary_index.json' to your AI assistant first")
        print("2. Tell the AI: 'This index contains ALL elements in this work'")
        print("3. Upload relevant .txt shards for your analysis")
        print("4. Ask focused questions about characters, themes, or structure")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main entry point."""
    if RICH_AVAILABLE:
        if not display_rich_interface():
            command_line_interface()
    else:
        command_line_interface()


if __name__ == "__main__":
    main()
