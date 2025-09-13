"""
Policy Manager: loads and serves concise policy/guidance documents for the orchestrator.

- Policies are stored as Markdown files under `vybe_app/policies/`
- Provides helpers to fetch combined excerpts within a character budget
  so we do not bloat the orchestrator's prompt.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


class PolicyManager:
    def __init__(self, policies_dir: Path | None = None):
        base = Path(__file__).parent.parent
        self.policies_dir = policies_dir or (base / "policies")
        self._cache: dict[str, str] = {}

    def list_policies(self) -> List[Path]:
        if not self.policies_dir.exists():
            return []
        return sorted(self.policies_dir.glob("*.md"))

    def read_policy(self, filename: str) -> str:
        if filename in self._cache:
            return self._cache[filename]
        path = self.policies_dir / filename
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            text = ""
        self._cache[filename] = text
        return text

    def get_combined_excerpt(self, max_chars: int = 2000) -> str:
        """Concatenate all policies and clamp to `max_chars`. Order is stable."""
        texts: List[str] = []
        for p in self.list_policies():
            texts.append(f"\n\n# {p.stem.replace('_', ' ').title()}\n\n")
            texts.append(self.read_policy(p.name))
        combined = "".join(texts).strip()
        return combined[:max_chars] if len(combined) > max_chars else combined

    def get_excerpt_for(self, include_files: List[str], max_chars: int = 2000) -> str:
        """Combine only selected policy files by base name (without .md)."""
        if not include_files:
            return ""
        include_set = {f.lower().replace('.md','') for f in include_files}
        texts: List[str] = []
        for p in self.list_policies():
            base = p.stem.lower()
            if base in include_set:
                texts.append(f"\n\n# {p.stem.replace('_', ' ').title()}\n\n")
                texts.append(self.read_policy(p.name))
        combined = "".join(texts).strip()
        return combined[:max_chars] if len(combined) > max_chars else combined

    def get_excerpt(self, filenames: List[str], max_chars: int = 1600) -> str:
        """Concatenate a subset of policies by filename in order and clamp."""
        texts: List[str] = []
        for name in filenames:
            path = self.policies_dir / name
            if not path.exists():
                continue
            texts.append(f"\n\n# {path.stem.replace('_', ' ').title()}\n\n")
            texts.append(self.read_policy(path.name))
        combined = "".join(texts).strip()
        return combined[:max_chars] if len(combined) > max_chars else combined


# Singleton accessor
_policy_manager: PolicyManager | None = None


def get_policy_manager() -> PolicyManager:
    global _policy_manager
    if _policy_manager is None:
        _policy_manager = PolicyManager()
    return _policy_manager


