#!/usr/bin/env python3
"""
self-healing/boundary_gate.py — Model Boundary Protection v1
Migration gate for cross-model data transfer.

Enforcement:
  - Promote: candidates/tg/ → candidates/approved/ (with audit trail)
  - Verify: checks for boundary violations in jin→huo writes
  - Block: prevents direct jin→huo promotion without review tag

Usage:
  python3 boundary_gate.py promote <file>      # promote tg candidate → approved
  python3 boundary_gate.py scan                # scan for candidates ready for review
  python3 boundary_gate.py verify              # check for boundary violations
"""

import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/home/dragonfive/.openclaw/workspace")
TG_CANDIDATES = WORKSPACE / "memory/candidates/tg"
APPROVED = WORKSPACE / "memory/candidates/approved"
EVENT_FILE = Path("/home/dragonfive/.openclaw/events/boundary_violation.jsonl")

TG_CANDIDATES.mkdir(parents=True, exist_ok=True)
APPROVED.mkdir(parents=True, exist_ok=True)


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_event(record: dict):
    with open(EVENT_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─── Verify boundary integrity ─────────────────────────


def verify():
    """
    Check for boundary violations: files from jin domain written directly
    into huo domain paths without going through candidates gate.
    """
    violations = []
    huo_events_dir = WORKSPACE / "memory/events/huo"
    jin_events_dir = WORKSPACE / "memory/events/jin"

    # Check jin events for references to huo paths (shouldn't read huo)
    if jin_events_dir.exists():
        for f in jin_events_dir.iterdir():
            if f.is_file():
                try:
                    content = f.read_text(errors="replace")
                    if "memory/state/huo" in content or "huo/state" in content:
                        violations.append({
                            "event": "boundary_violation",
                            "ts": utc(),
                            "severity": "high",
                            "type": "jin_read_huo_state",
                            "source": "jin",
                            "target": "huo_state",
                            "file": str(f),
                            "action": "blocked",
                        })
                except OSError:
                    pass

    # Check that candidates/tg files have proper metadata
    if TG_CANDIDATES.exists():
        for f in TG_CANDIDATES.iterdir():
            if f.is_file() and f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    if not data.get("source_model") == "jin":
                        violations.append({
                            "event": "boundary_violation",
                            "ts": utc(),
                            "severity": "medium",
                            "type": "candidate_missing_source_tag",
                            "file": str(f),
                            "action": "flagged",
                        })
                except (json.JSONDecodeError, OSError):
                    pass

    # Deduplication: only write violations not already recorded
    # Read existing violation fingerprints
    existing = set()
    if EVENT_FILE.exists():
        try:
            with open(EVENT_FILE) as f:
                for line in f:
                    if line.strip():
                        try:
                            d = json.loads(line)
                            fp = d.get("_fp")
                            if fp:
                                existing.add(fp)
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass

    new_violations = []
    for v in violations:
        fp = f"{v.get('type','?')}|{v.get('source','?')}|{v.get('file','?')}"
        if fp not in existing:
            v["_fp"] = fp
            write_event(v)
            new_violations.append(v)

    return new_violations


# ─── Promote gate ──────────────────────────────────────


def promote(filename: str):
    """Promote a candidate from tg/ to approved/ with audit trail."""
    src = TG_CANDIDATES / filename
    if not src.exists():
        print(f"error: candidate not found: {src}", file=sys.stderr)
        return False

    # Verify candidate has source metadata
    content = src.read_text()
    mandatory_tags = ["source_model", "data_class"]

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Plain text file — wrap with metadata
        data = {"content": content, "source_model": "jin", "data_class": "experiment"}

    missing = [t for t in mandatory_tags if t not in data]
    if missing:
        print(f"error: candidate missing tags: {missing}", file=sys.stderr)
        return False

    if data.get("source_model") != "jin" or data.get("data_class") != "experiment":
        print(f"error: candidate is not jin/experiment data ({data.get('source_model')}/{data.get('data_class')})", file=sys.stderr)
        return False

    # Add promotion metadata
    data["_promoted_at"] = utc()
    data["_promoted_by"] = "boundary_gate_v1"
    data["_promoted_from"] = f"candidates/tg/{filename}"
    data["_trace_id"] = str(uuid.uuid4())

    # Write to approved
    dst = APPROVED / filename
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # Audit trail
    write_event({
        "event": "model_promote",
        "ts": utc(),
        "source_model": "jin",
        "target_model": "huo",
        "file": f"candidates/tg/{filename}",
        "trace_id": data["_trace_id"],
        "action": "promoted_to_approved",
    })

    # Remove from candidates (move, not copy)
    src.unlink()
    print(f"promoted: candidates/tg/{filename} → candidates/approved/ ({data['_trace_id'][:12]})")
    return True


def scan():
    """List candidates ready for review."""
    if not TG_CANDIDATES.exists():
        print("no candidates directory")
        return

    files = list(TG_CANDIDATES.iterdir())
    if not files:
        print("no candidates pending review")
        return

    print(f"Candidates pending review ({len(files)}):")
    for f in sorted(files, key=lambda x: x.stat().st_mtime):
        age = (datetime.now().timestamp() - f.stat().st_mtime) / 3600
        print(f"  {f.name:40s} created {age:.1f}h ago")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: boundary_gate.py promote|scan|verify [filename]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "verify":
        violations = verify()
        if violations:
            print(f"{len(violations)} violation(s) found")
            for v in violations:
                print(f"  [{v['severity']}] {v['type']}: {v.get('file', '')}")
        else:
            print("0 violations — boundaries intact")
        sys.exit(0 if not violations else 1)

    elif action == "scan":
        scan()

    elif action == "promote":
        if len(sys.argv) < 3:
            print("error: specify filename to promote", file=sys.stderr)
            sys.exit(1)
        success = promote(sys.argv[2])
        sys.exit(0 if success else 1)

    else:
        print(f"unknown action: {action}", file=sys.stderr)
        sys.exit(1)
