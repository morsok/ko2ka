from typing import List, Dict, Any, Optional
import difflib
from pathlib import Path

# We can use fuzzywuzzy/thefuzz if acceptable, but standard lib difflib is safer 
# if we want to minimize heavy dependencies not in plan. 
# Plan didn't specify fuzzy lib, so difflib is a good start.
# Actually, strict matching on series name is usually preferred + fuzzy on chapter number.

def match_series(komga_series: str, kavita_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    # 1. Exact match
    for s in kavita_results:
        # Check 'name' and 'originalName' if available
        if s.get('name', '').lower() == komga_series.lower():
            return s
            
    # 2. Fuzzy match if exact fails?
    # Let's keep it simple for now as requested.
    return None

def match_book_by_filename(komga_path: str, kavita_chapters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    target = Path(komga_path).name.lower()
    for ch in kavita_chapters:
        for f in ch.get('files', []):
            if Path(f.get('filePath', '')).name.lower() == target:
                return ch
    return None

def match_book(komga_number: float, kavita_chapters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Match a book based on number.
    """
    for ch in kavita_chapters:
        try:
            # Kavita might return number as string "1", "1.5", or even "1.0"
            c_num = float(ch.get('number', -1))
            if abs(c_num - komga_number) < 0.01:
                return ch
        except (ValueError, TypeError):
            continue
            
    return None
