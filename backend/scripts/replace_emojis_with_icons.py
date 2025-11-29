#!/usr/bin/env python3
"""
Systematically replace emojis with equivalent icon references across all files.

This script scans all files in a directory tree and replaces Unicode emojis
with icon references (e.g., :check:, :warning:, etc.) similar to Notion's icon system.

Usage:
    python replace_emojis_with_icons.py [--root ROOT_DIR] [--dry-run] [--backup] [--extensions EXT1,EXT2]

Examples:
    # Dry run to see what would be changed
    python replace_emojis_with_icons.py --root /data/dsa110-contimg --dry-run

    # Actually replace with backups
    python replace_emojis_with_icons.py --root /data/dsa110-contimg --backup

    # Only process specific file types
    python replace_emojis_with_icons.py --root /data/dsa110-contimg --extensions py,md,sh
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import unicodedata
import json
from datetime import datetime


class EmojiToIconMapper:
    """Maps Unicode emojis to icon names."""
    
    def __init__(self):
        # Comprehensive emoji to icon name mapping
        # Based on common emoji usage and Notion-style icon naming
        self.emoji_to_icon = {
            # Status/Checkmarks
            "✅": ":check:",
            "✓": ":check:",
            "✔": ":check:",
            "✔️": ":check:",
            "❌": ":cross:",
            "✗": ":cross:",
            "✖": ":cross:",
            "✖️": ":cross:",
            "❓": ":question:",
            "❔": ":question:",
            "⚠️": ":warning:",
            "⚠": ":warning:",
            "🔴": ":red_circle:",
            "🟢": ":green_circle:",
            "🟡": ":yellow_circle:",
            "🔵": ":blue_circle:",
            "⚫": ":black_circle:",
            "⚪": ":white_circle:",
            
            # Information
            "ℹ️": ":info:",
            "ℹ": ":info:",
            "💡": ":lightbulb:",
            "📝": ":memo:",
            "📄": ":page:",
            "📋": ":clipboard:",
            "📊": ":chart:",
            "📈": ":chart_up:",
            "📉": ":chart_down:",
            "📌": ":pin:",
            "📍": ":location:",
            
            # Tools/Actions
            "🔧": ":wrench:",
            "⚙️": ":gear:",
            "⚙": ":gear:",
            "🔨": ":hammer:",
            "🛠️": ":tools:",
            "🛠": ":tools:",
            "🔍": ":search:",
            "🔎": ":magnifying_glass:",
            "🔐": ":lock:",
            "🔓": ":unlock:",
            "🔑": ":key:",
            
            # Communication
            "💬": ":speech:",
            "📢": ":megaphone:",
            "📣": ":megaphone:",
            "📡": ":satellite:",
            "📻": ":radio:",
            "📺": ":tv:",
            "📱": ":phone:",
            "💻": ":laptop:",
            "🖥️": ":desktop:",
            "🖥": ":desktop:",
            
            # Files/Folders
            "📁": ":folder:",
            "📂": ":folder_open:",
            "🗂️": ":card_index:",
            "🗂": ":card_index:",
            "📑": ":bookmark:",
            "📚": ":books:",
            "📖": ":book:",
            "📗": ":green_book:",
            "📘": ":blue_book:",
            "📙": ":orange_book:",
            "📕": ":red_book:",
            
            # Time/Calendar
            "⏰": ":alarm:",
            "⏱️": ":stopwatch:",
            "⏱": ":stopwatch:",
            "⏲️": ":timer:",
            "⏲": ":timer:",
            "📅": ":calendar:",
            "📆": ":calendar_spiral:",
            "🗓️": ":calendar_pad:",
            "🗓": ":calendar_pad:",
            
            # Arrows/Direction
            "➡️": ":arrow_right:",
            "➡": ":arrow_right:",
            "⬅️": ":arrow_left:",
            "⬅": ":arrow_left:",
            "⬆️": ":arrow_up:",
            "⬆": ":arrow_up:",
            "⬇️": ":arrow_down:",
            "⬇": ":arrow_down:",
            "↗️": ":arrow_up_right:",
            "↗": ":arrow_up_right:",
            "↘️": ":arrow_down_right:",
            "↘": ":arrow_down_right:",
            "↖️": ":arrow_up_left:",
            "↖": ":arrow_up_left:",
            "↙️": ":arrow_down_left:",
            "↙": ":arrow_down_left:",
            "🔄": ":refresh:",
            "🔁": ":repeat:",
            "⏪": ":rewind:",
            "⏩": ":fast_forward:",
            "⏯️": ":play_pause:",
            "⏯": ":play_pause:",
            
            # Science/Technology
            "🔬": ":microscope:",
            "🔭": ":telescope:",
            "🧪": ":test_tube:",
            "⚗️": ":alembic:",
            "⚗": ":alembic:",
            "🧬": ":dna:",
            "🔋": ":battery:",
            "🔌": ":plug:",
            "💾": ":floppy:",
            "💿": ":cd:",
            "📀": ":dvd:",
            
            # Weather/Nature
            "☀️": ":sun:",
            "☀": ":sun:",
            "🌙": ":moon:",
            "⭐": ":star:",
            "🌟": ":star2:",
            "💫": ":dizzy:",
            "🌊": ":wave:",
            "🔥": ":fire:",
            "❄️": ":snowflake:",
            "❄": ":snowflake:",
            "☁️": ":cloud:",
            "☁": ":cloud:",
            
            # Symbols
            "✨": ":sparkles:",
            "💎": ":gem:",
            "🎯": ":target:",
            "🚀": ":rocket:",
            "🎨": ":art:",
            "🎭": ":theater:",
            "🎪": ":circus:",
            "🎬": ":movie:",
            "🎮": ":game:",
            "🎲": ":dice:",
            
            # People/Gestures
            "👤": ":person:",
            "👥": ":people:",
            "👨‍💻": ":technologist:",
            "👩‍💻": ":woman_technologist:",
            "🤖": ":robot:",
            
            # Flags/Countries (common ones)
            "🇺🇸": ":us:",
            "🇬🇧": ":gb:",
            "🇨🇦": ":ca:",
            "🇦🇺": ":au:",
            
            # Common punctuation/symbols that might be used as icons
            "→": ":arrow_right:",
            "←": ":arrow_left:",
            "↑": ":arrow_up:",
            "↓": ":arrow_down:",
            "•": ":bullet:",
            "▪": ":square:",
            "▫": ":square_white:",
            "■": ":square_black:",
            "□": ":square_empty:",
        }
        
        # Reverse mapping for lookup
        self.icon_to_emoji = {v: k for k, v in self.emoji_to_icon.items()}
    
    def get_icon_name(self, emoji: str) -> Optional[str]:
        """Get icon name for an emoji, or None if not mapped."""
        return self.emoji_to_icon.get(emoji)
    
    def is_emoji(self, char: str) -> bool:
        """Check if a character is an emoji using Unicode properties."""
        # Check if it's in our mapping first
        if char in self.emoji_to_icon:
            return True
        
        # Check Unicode emoji properties
        try:
            # Emoji property check
            if unicodedata.name(char, "").startswith(("EMOJI", "REGIONAL INDICATOR")):
                return True
            
            # Check common emoji Unicode ranges
            code_point = ord(char)
            emoji_ranges = [
                (0x1F600, 0x1F64F),  # Emoticons
                (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
                (0x1F680, 0x1F6FF),  # Transport and Map
                (0x1F1E0, 0x1F1FF),  # Regional indicators
                (0x2600, 0x26FF),    # Misc symbols
                (0x2700, 0x27BF),    # Dingbats
                (0xFE00, 0xFE0F),    # Variation Selectors
                (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
                (0x1FA00, 0x1FA6F),  # Chess Symbols
                (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
            ]
            
            for start, end in emoji_ranges:
                if start <= code_point <= end:
                    return True
        except (ValueError, TypeError):
            pass
        
        return False
    
    def find_all_emojis(self, text: str) -> List[Tuple[int, int, str]]:
        """Find all emojis in text, returning (start, end, emoji) tuples."""
        emojis = []
        i = 0
        while i < len(text):
            char = text[i]
            
            # Check for multi-character emojis (with variation selectors)
            if i + 1 < len(text):
                two_char = text[i:i+2]
                if self.is_emoji(two_char) or two_char in self.emoji_to_icon:
                    emojis.append((i, i + 2, two_char))
                    i += 2
                    continue
            
            if self.is_emoji(char) or char in self.emoji_to_icon:
                emojis.append((i, i + 1, char))
            
            i += 1
        
        return emojis


class EmojiReplacer:
    """Replace emojis in files with icon references."""
    
    def __init__(self, root_dir: Path, extensions: Optional[List[str]] = None, 
                 dry_run: bool = False, backup: bool = False, verbose: bool = False):
        self.root_dir = Path(root_dir).resolve()
        self.extensions = extensions
        self.dry_run = dry_run
        self.backup = backup
        self.verbose = verbose
        self.mapper = EmojiToIconMapper()
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "files_modified": 0,
            "emojis_found": 0,
            "emojis_replaced": 0,
            "emojis_unmapped": defaultdict(int),
            "errors": [],
        }
        
        # Files to ignore
        self.ignore_dirs = {
            ".git", "__pycache__", "node_modules", ".pytest_cache",
            ".coverage", ".mypy_cache", "dist", "build", ".venv", "venv",
            ".egg-info", ".idea", ".vscode", ".DS_Store", ".codacy",
        }
        
        self.ignore_files = {
            ".gitignore", ".gitattributes", ".coverage",
        }
    
    def should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        # Check if in ignored directory (check all path parts)
        for part in file_path.parts:
            if part in self.ignore_dirs:
                return False
            # Also check if path contains ignored substrings
            if any(ignore in str(file_path) for ignore in ["/.local/", "/archive/", "/legacy"]):
                return False
        
        # Check if ignored file
        if file_path.name in self.ignore_files:
            return False
        
        # Check extension filter
        if self.extensions:
            if file_path.suffix.lstrip(".") not in self.extensions:
                return False
        
        # Skip binary files (heuristic: check if file is text-based)
        try:
            # Try to read as text to see if it's binary
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\x00" in chunk:
                    return False  # Likely binary
        except (IOError, OSError):
            return False
        
        return True
    
    def replace_emojis_in_text(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Replace emojis in text with icon references."""
        replacements = defaultdict(int)
        result = text
        offset = 0
        
        # Find all emojis
        emojis = self.mapper.find_all_emojis(text)
        
        # Process in reverse order to maintain indices
        for start, end, emoji in reversed(emojis):
            icon_name = self.mapper.get_icon_name(emoji)
            
            if icon_name:
                # Replace emoji with icon reference
                result = result[:start] + icon_name + result[end:]
                replacements[emoji] += 1
            else:
                # Emoji not in mapping - try to generate a name
                try:
                    unicode_name = unicodedata.name(emoji.split()[0], "")
                    # Generate a reasonable icon name from Unicode name
                    icon_name = self._generate_icon_name(emoji, unicode_name)
                    if icon_name:
                        result = result[:start] + icon_name + result[end:]
                        replacements[emoji] += 1
                    else:
                        self.stats["emojis_unmapped"][emoji] += 1
                except (ValueError, TypeError):
                    self.stats["emojis_unmapped"][emoji] += 1
        
        return result, dict(replacements)
    
    def _generate_icon_name(self, emoji: str, unicode_name: str) -> Optional[str]:
        """Generate an icon name from Unicode name if not in mapping."""
        # Simple heuristic: convert Unicode name to icon name
        # e.g., "WHITE HEAVY CHECK MARK" -> ":white_check_mark:"
        if not unicode_name:
            return None
        
        # Convert to lowercase, replace spaces with underscores
        name = unicode_name.lower().replace(" ", "_")
        
        # Remove common prefixes
        for prefix in ["emoji", "symbol", "sign"]:
            if name.startswith(prefix + "_"):
                name = name[len(prefix) + 1:]
        
        return f":{name}:"
    
    def process_file(self, file_path: Path) -> Tuple[bool, Optional[List[Tuple[str, str, int]]]]:
        """Process a single file, replacing emojis.
        
        Returns:
            (modified, details) where details is a list of (emoji, icon, count) tuples
        """
        try:
            # Read file
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                original_text = f.read()
            
            # Replace emojis
            new_text, replacements = self.replace_emojis_in_text(original_text)
            
            if replacements:
                self.stats["emojis_found"] += sum(replacements.values())
                self.stats["emojis_replaced"] += sum(replacements.values())
                
                if new_text != original_text:
                    # Prepare details for verbose output
                    details = []
                    for emoji, count in replacements.items():
                        icon = self.mapper.get_icon_name(emoji)
                        if icon:
                            details.append((emoji, icon, count))
                    
                    if not self.dry_run:
                        # Create backup if requested
                        if self.backup:
                            backup_path = file_path.with_suffix(
                                file_path.suffix + f".emoji_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            )
                            with open(backup_path, "w", encoding="utf-8") as f:
                                f.write(original_text)
                        
                        # Write modified content
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_text)
                    
                    self.stats["files_modified"] += 1
                    return True, details if self.verbose else None
            
            return False, None
            
        except Exception as e:
            error_msg = f"Error processing {file_path}: {e}"
            self.stats["errors"].append(error_msg)
            print(f"ERROR: {error_msg}", file=sys.stderr)
            return False, None
    
    def process_directory(self):
        """Process all files in directory tree."""
        print(f"Scanning directory: {self.root_dir}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Backup: {'YES' if self.backup else 'NO'}")
        if self.extensions:
            print(f"Extensions: {', '.join(self.extensions)}")
        print("-" * 60)
        
        # Walk directory tree
        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file() and self.should_process_file(file_path):
                self.stats["files_processed"] += 1
                
                modified, details = self.process_file(file_path)
                if modified:
                    rel_path = file_path.relative_to(self.root_dir)
                    action = "Would modify" if self.dry_run else "Modified"
                    print(f"{action}: {rel_path}")
                    if self.verbose and details:
                        for emoji, icon, count in details:
                            print(f"    {emoji} -> {icon} ({count}x)")
        
        # Print statistics
        self.print_statistics()
    
    def print_statistics(self):
        """Print processing statistics."""
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files {'would be ' if self.dry_run else ''}modified: {self.stats['files_modified']}")
        print(f"Emojis found: {self.stats['emojis_found']}")
        print(f"Emojis replaced: {self.stats['emojis_replaced']}")
        
        if self.stats["emojis_unmapped"]:
            print(f"\nUnmapped emojis (not replaced):")
            for emoji, count in sorted(self.stats["emojis_unmapped"].items(), 
                                     key=lambda x: x[1], reverse=True):
                print(f"  {emoji} (U+{ord(emoji[0]):04X}): {count} occurrences")
        
        if self.stats["errors"]:
            print(f"\nErrors: {len(self.stats['errors'])}")
            for error in self.stats["errors"][:10]:  # Show first 10
                print(f"  {error}")


def main():
    parser = argparse.ArgumentParser(
        description="Replace emojis with icon references in files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--root",
        type=str,
        default="/data/dsa110-contimg",
        help="Root directory to process (default: /data/dsa110-contimg)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup files before modifying"
    )
    
    parser.add_argument(
        "--extensions",
        type=str,
        help="Comma-separated list of file extensions to process (e.g., 'py,md,sh')"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed information about each replacement"
    )
    
    args = parser.parse_args()
    
    # Parse extensions
    extensions = None
    if args.extensions:
        extensions = [ext.strip().lstrip(".") for ext in args.extensions.split(",")]
    
    # Create replacer and process
    replacer = EmojiReplacer(
        root_dir=args.root,
        extensions=extensions,
        dry_run=args.dry_run,
        backup=args.backup,
        verbose=args.verbose,
    )
    
    replacer.process_directory()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
