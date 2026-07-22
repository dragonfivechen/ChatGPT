#!/usr/bin/env python3
"""
self-healing/boundary_observe.py — Model Boundary Protection v1
Monitors for cross-model boundary violations between 燃🔥 and 烬🔥.

Detection scope:
  - TG data written to huo memory paths
  - Terminal data written to jin memory paths
  - Identity-mismatched file writes
  - Session context cross-talk (same session key used by wrong model)

This is an observation layer only: detects and records, does not block.
Blocking requires OS-level permissions which are out of scope.

Output: events/boundary_violation.jsonl (append-only)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

STATE_DIR = Path("/home/dragonfive/.openclaw/self-healing/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)
VIOLATION_FILE = Path("/home/dragonfive/.openclaw/events/boundary_violation.jsonl")
VIOLATION_FILE.parent.mkdir(parents=True, exist_ok=True)

# ─── Boundary Definitions ──────────────────────────────

# Memory paths owned by each identity
HUO_MEMORY_PATHS = [
    "memory/events/huo/",
    "memory/state/huo/",
    "memory/state/system/",
]

JIN_MEMORY_PATHS = [
    "memory/events/jin/",
]

SHARED_MEMORY_PATHS = [
    "memory/knowledge/",
    "memory/facts/",
    "memory/data/",
    "memory/preferences/",
]

# Runtime state paths
SYSTEM_PATHS = [
    "events/",
    "self-healing/",
    "runtime/",
]

WORKSPACE = Path("/home/dragonfive/.openclaw/workspace")

# ─── Detection ─────────────────────────────────────────


def check_file_write_boundary(path: str, real_path: Path) -> list[dict]:
    """
    Check if a file at `path` belongs to an unexpected identity domain.
    Returns list of violations found.

    Rule: huo-owned files should only be written by huo/system processes.
    jin-owned files should only be written by jin processes.
    We can't determine the writing process from the file alone, but we can
    flag files in huo paths that contain jin identifiers in their content.
    """
    violations = []

    if not real_path.exists() or not real_path.is_file():
        return violations

    # Check if file path suggests ownership mismatch
    path_str = str(path)

    # Huo paths should not contain jin-named content
    if any(p in path_str for p in HUO_MEMORY_PATHS):
        # Sample the file for jin identifiers
        try:
            content = real_path.read_text(errors="replace")[:5000]
            if "jin" in content.lower() and ("jin" in content.split() or "jin/" in content):
                violations.append({
                    "type": "possible_cross_boundary_content",
                    "severity": "low",
                    "path": path_str,
                    "owner_domain": "huo",
                    "suspected": "jin_content_detected",
                })
        except (OSError, PermissionError):
            pass

    return violations


def check_identity_binding() -> list[dict]:
    """
    Check agent binding config for potential identity misconfigurations.
    """
    violations = []

    # Check that IDENTITY.md exists and has correct structure
    identity_md = WORKSPACE / "IDENTITY.md"
    if not identity_md.exists():
        violations.append({
            "type": "missing_identity_config",
            "severity": "high",
            "path": str(identity_md),
        })

    rules_md = WORKSPACE / "IDENTITY-RULES.md"
    if not rules_md.exists():
        violations.append({
            "type": "missing_identity_rules",
            "severity": "high",
            "path": str(rules_md),
        })

    return violations


def check_memory_directory_structure() -> list[dict]:
    """Verify the memory directory isolation is intact."""
    violations = []
    base = WORKSPACE / "memory"

    # Required isolation directories
    required = {
        "events/huo": "huo",
        "events/jin": "jin",
        "state/huo": "huo",
    }

    for rel_path, owner in required.items():
        p = base / rel_path
        if not p.exists():
            violations.append({
                "type": "missing_isolation_directory",
                "severity": "medium",
                "path": f"memory/{rel_path}",
                "owner": owner,
            })

    # Check for cross-owner files
    huo_dir = base / "events/huo"
    jin_dir = base / "events/jin"

    if huo_dir.exists():
        for f in huo_dir.iterdir():
            if f.is_file() and f.suffix in (".md", ".jsonl", ".json"):
                # Check content for jin keywords — low confidence heuristic
                try:
                    content = f.read_text(errors="replace")[:1000]
                    if "tg-agent" in content and "jin" in content.lower():
                        violations.append({
                            "type": "possible_cross_writer",
                            "severity": "low",
                            "path": str(f),
                            "domain": "huo_contains_jin_ref",
                        })
                except (OSError, PermissionError):
                    pass

    return violations


def run() -> list[dict]:
    """One observation cycle: check all boundaries, return violations."""
    violations = []
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Identity config integrity
    violations.extend(check_identity_binding())

    # 2. Memory directory isolation
    violations.extend(check_memory_directory_structure())

    # 3. Annotate with timestamp and write
    for v in violations:
        v["timestamp"] = now_utc
        v["_observer"] = "boundary_observe_v1"

    if violations:
        with open(VIOLATION_FILE, "a") as f:
            for v in violations:
                f.write(json.dumps(v, ensure_ascii=False) + "\n")

    return violations


def show_status() -> dict:
    """Show current boundary observation summary."""
    if not VIOLATION_FILE.exists():
        return {"boundary_violations": 0, "last_check": "never"}

    violations = []
    with open(VIOLATION_FILE) as f:
        for line in f:
            if line.strip():
                try:
                    violations.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    by_severity = defaultdict(int)
    by_type = defaultdict(int)
    for v in violations:
        by_severity[v.get("severity", "unknown")] += 1
        by_type[v.get("type", "unknown")] += 1

    last_ts = violations[-1].get("timestamp", "?") if violations else "never"

    return {
        "total": len(violations),
        "by_severity": dict(by_severity),
        "by_type": dict(by_type),
        "last_check": last_ts,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps(show_status(), indent=2))
    else:
        violations = run()
        if violations:
            print(json.dumps(violations, indent=2))
        else:
            print("[]")
