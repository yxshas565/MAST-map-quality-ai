"""
Utilities for generating and applying unified diffs.
"""
import difflib
from typing import Optional


def generate_unified_diff(
    original: str,
    patched: str,
    fromfile: str = "original.py",
    tofile: str = "patched.py",
    context_lines: int = 3,
) -> str:
    """Generate a unified diff string between two code strings."""
    original_lines = original.splitlines(keepends=True)
    patched_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines, patched_lines,
        fromfile=fromfile, tofile=tofile,
        n=context_lines,
    )
    return "".join(diff)


def apply_patch_to_string(original: str, diff: str) -> Optional[str]:
    """
    Apply a unified diff to a source string.
    Returns patched string, or None if patch fails.
    Simple line-based apply — good enough for our controlled demo.
    """
    try:
        import patch as patch_lib  # python-patch library
        pset = patch_lib.fromstring(diff.encode())
        result = pset.apply(original.encode())
        return result.decode() if result else None
    except Exception:
        # Fallback: just return the diff itself with a note
        return None