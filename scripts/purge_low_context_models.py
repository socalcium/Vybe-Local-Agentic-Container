#!/usr/bin/env python3
"""
Purge clearly low-context GGUF models (<32k) from all models directories.

Heuristic-based:
- Deletes files whose names include 2k/4k/8k/16k token hints
- Keeps files that include 32k/64k/128k
- Leaves unknowns intact for safety

Run: python scripts/purge_low_context_models.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Tuple


def add_project_root_to_path():
    this_file = Path(__file__).resolve()
    project_root = this_file.parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def discover_model_dirs() -> List[Path]:
    try:
        add_project_root_to_path()
        from vybe_app.config import Config
        return [Path(p) for p in Config.get_models_directories()]
    except Exception:
        # Fallback to ./models
        return [Path.cwd() / 'models']


LOW_HINTS = ('2k', '4k', '8k', '16k')
HIGH_HINTS = ('32k', '64k', '128k')


def classify(path: Path) -> str:
    name = path.name.lower()
    # High hints win
    if any(h in name for h in HIGH_HINTS):
        return 'keep'
    # Clear low hints
    if any(h in name for h in LOW_HINTS):
        return 'delete'
    # Common tiny model names (best-effort)
    tiny_markers = ('tinyllama', 'tinystories')
    if any(m in name for m in tiny_markers):
        return 'delete'
    # Unknown -> keep safe
    return 'keep'


def purge_low_context_models() -> Tuple[int, int, List[str]]:
    removed = 0
    kept = 0
    actions: List[str] = []
    for model_dir in discover_model_dirs():
        try:
            model_dir.mkdir(exist_ok=True, parents=True)
        except Exception:
            continue
        for path in model_dir.glob('*.gguf'):
            decision = classify(path)
            if decision == 'delete':
                try:
                    path.unlink(missing_ok=True)
                    removed += 1
                    actions.append(f"deleted: {path}")
                except Exception as e:
                    actions.append(f"failed_delete: {path} ({e})")
            else:
                kept += 1
                # actions.append(f"kept: {path}")  # too verbose
    return removed, kept, actions


def main() -> int:
    removed, kept, actions = purge_low_context_models()
    print(f"Models removed: {removed}; kept: {kept}")
    # Print up to 20 actions for visibility
    for line in actions[:20]:
        print(line)
    if removed > 0:
        print("Low-context models purged.")
    else:
        print("No clearly low-context models found.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


