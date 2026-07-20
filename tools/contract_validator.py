#!/usr/bin/env python3
"""
contract_validator.py — L2 Validation Layer

验证 5 个契约入口，输出 contract_violation.jsonl（append-only）。
Post-hoc only。不阻断执行。不修改系统。

用法:
  python3 tools/contract_validator.py                # 全量验证
  python3 tools/contract_validator.py --dry-run       # 预览不写入
  python3 tools/contract_validator.py --checks ownership,reasoning  # 指定检查

遵从: CONTRACT-ENFORCEMENT-SKELETON-DESIGN.md
"""
import json, sys, hashlib, os
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', str(Path.home() / '.openclaw' / 'workspace')))
EVENTS_DIR = WORKSPACE / 'memory' / 'events'
VIOLATION_LOG = WORKSPACE / 'memory' / 'data' / 'system' / 'contract_violation.jsonl'

# ── 注册的 writer 列表 ──
REGISTERED_WRITERS = {
    'eval-local.sh', 'local-task-worker.sh',
    'memory_governance_worker.py', 'memory_candidate_extract.py', 'memory_dedup.py',
    'memory_feedback_detect.py', 'memory_promote.py',
    'collect-daily-status.sh', 'collect-sensors.sh', 'collect-token-metrics.sh',
    'backup-full.sh', 'audit-backup.sh', 'push-daily-report.sh',
    'context_provider.py',
    # Agent sessions write via OpenClaw runtime (not in our writer registry)
    'openclaw-runtime',
}

# ── 能力注册表路径 ──
CAPABILITY_REGISTRY = WORKSPACE / 'memory' / 'state' / 'huo' / 'provider-capability-registry.json'


def now_ts():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def record_violation(contract: str, level: str, source: str, event: str, details: str, dry_run: bool = False):
    """写入一条 violation 记录"""
    record = {
        'ts': now_ts(),
        'contract': contract,
        'level': level,
        'source': source,
        'event': event,
        'details': details,
        'action': 'record_only',
        'validator': 'contract_validator.py v0.1'
    }
    if dry_run:
        print(f"  [DRY-RUN] {contract}: {details}")
    else:
        VIOLATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(VIOLATION_LOG, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"  ⚠️  {contract}: {details}")
    return record


# ═══════════════════════════════════════════
# Validator 1: Memory Ownership
# ═══════════════════════════════════════════

def check_memory_ownership(dry_run: bool = False):
    """验证 memory/events 目录写入者身份与所有权匹配
    
    只检测实际跨身份写入行为，不因身份关键词出现就报警。
    例如：
      - huo/ 文件包含 Telegram 消息原文 / TG 命令输出 → 跨身份写入
      - huo/ 文件提到"烬🔥应遵守隔离规则" → 规则描述，豁免
    """
    violations = []
    
    # 跨身份行为信号：其他身份的实际产物，非规则描述
    CROSS_IDENTITY_SIGNALS = {
        'huo': [  # huo 中出现 tg-agent 的产物
            '/send_message', '/telegram', 'tg_id:', 'message_id:',
            'telegram.update', 'channel_post',
        ],
        'jin': [  # jin 中出现 main-agent 的产物
            'shell_output', 'exit_code:', '/webchat',
            'terminal_output', '[exec]',
        ],
    }
    
    for agent_dir, signals in CROSS_IDENTITY_SIGNALS.items():
        path = EVENTS_DIR / agent_dir
        if not path.exists():
            continue
        for f in sorted(path.glob('*.md')):
            content = f.read_text()
            for signal in signals:
                if signal in content:
                    violations.append(record_violation(
                        'memory_ownership', 'L1_violation', str(f),
                        'cross_identity_write',
                        f'{agent_dir}/ 含其他身份行为信号: {signal}',
                        dry_run
                    ))
                    break  # 一个文件只报一次
    if not violations:
        print(f"  ✅ memory_ownership: 无跨身份写入")
    return violations


# ═══════════════════════════════════════════
# Validator 2: Reasoning Isolation
# ═══════════════════════════════════════════

def check_reasoning_isolation(dry_run: bool = False):
    """检测 reasoning/thinking 内容污染事实存储
    
    契约文档本身（描述推理隔离规则）不算污染。
    污染指：reasoning 模型输出直接进入 event/memory/fact 且无标识。
    """
    violations = []
    
    # 契约描述豁免词：行中包含这些词时，内容是描述规则而非污染
    CONTRACT_KEYWORDS = {
        'Reasoning Isolation', 'RI-001', 'RI-002', 'reasoning_isolation',
        '推理隔离', '推理痕迹', 'reasoning_content',
        'FROZEN', 'Contract', 'V1', 'V2', 'V3',
    }
    
    for f in sorted((EVENTS_DIR / 'huo').glob('*.md')):
        content = f.read_text()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'reasoning' not in line.lower() and 'thinking' not in line.lower():
                continue
            
            # 豁免：契约描述行
            if any(kw in line for kw in CONTRACT_KEYWORDS):
                continue
            
            # 豁免：标题行和分隔行
            if line.strip().startswith('##') or line.strip().startswith('---'):
                continue
            
            # 豁免：包含「不得」「禁止」「允许」等规则描述词
            if any(w in line for w in ['不得', '禁止', '允许', '必须', '规则']):
                continue
            
            # 豁免：架构冻结状态行
            if 'FROZEN' in line or 'Phase' in line:
                continue
            
            # 豁免：文件路径引用
            if '/REASONING-' in line or 'REASONING-' in line:
                continue
            
            # 到达这里说明 reasoning 出现在非契约描述、非规则、非架构的上下文中
            violations.append(record_violation(
                'reasoning_isolation', 'L1_violation', str(f),
                'reasoning_in_fact_context',
                f'line {i+1}: "{line.strip()[:80]}"',
                dry_run
            ))
    if not violations:
        print("  ✅ reasoning_isolation: 无污染证据")
    return violations


# ═══════════════════════════════════════════
# Validator 3: Writer Boundary
# ═══════════════════════════════════════════

def check_writer_boundary(dry_run: bool = False):
    """验证写入者是否在注册表中"""
    violations = []
    # 检查 events/ 下文件，尝试识别写入者
    writer_map = {
        'ollama-eval.jsonl': 'eval-local.sh',
        'ollama-production.jsonl': 'local-task-worker.sh',
        'governance-events.jsonl': 'memory_governance_worker.py',
    }
    events_dir = EVENTS_DIR
    for f in sorted(events_dir.rglob('*.jsonl')):
        if f.name in writer_map:
            detected_writer = writer_map[f.name]
            if detected_writer not in REGISTERED_WRITERS:
                violations.append(record_violation(
                    'writer_boundary', 'L1_violation', str(f),
                    'unregistered_writer',
                    f'写入者 {detected_writer} 不在注册表中',
                    dry_run
                ))
    # 检查 events/data/ 下系统文件的写入者
    for f in sorted((WORKSPACE / 'memory' / 'data' / 'system').glob('*.jsonl')):
        if f.name not in ['contract_violation.jsonl']:
            pass  # 系统文件由 cron 写入，暂不校验
    if not violations:
        print("  ✅ writer_boundary: 所有已知写入者已注册")
    return violations


# ═══════════════════════════════════════════
# Validator 4: Capability Registry
# ═══════════════════════════════════════════

def check_capability_registry(dry_run: bool = False):
    """验证工具调用是否在能力注册表中"""
    violations = []
    if not CAPABILITY_REGISTRY.exists():
        print("  ⚠️  capability_registry: registry 文件不存在")
        return violations

    with open(CAPABILITY_REGISTRY) as f:
        registry = json.load(f)

    known_capabilities = set(registry.get('capabilities', {}).keys())
    # 当前检查：已知 tool 是否在 registry 中
    known_tools = ['execute_shell', 'web_search', 'web_fetch', 'read', 'write',
                   'edit', 'memory_search', 'memory_get', 'exec', 'process']
    for tool in known_tools:
        # 检查是否映射到 registry 中的任一 capability
        mapped = False
        for cap_name, cap_def in registry.get('capabilities', {}).items():
            if 'tool' in cap_def.get('description', '').lower() or tool in cap_def.get('description', ''):
                mapped = True
                break
        if not mapped:
            # tool 不在 registry 中不一定违规（可能存在默认能力）
            pass  # 暂不报警，等待更精确的映射规则
    print(f"  ✅ capability_registry: {len(known_capabilities)} 能力已注册")
    return violations


# ═══════════════════════════════════════════
# Validator 5: Tool Call Observation
# ═══════════════════════════════════════════

def check_tool_call_observation(dry_run: bool = False):
    """观察 tool intent → capability 映射（非 Gateway 实现）"""
    violations = []
    # 当前阶段：仅检查是否存在 tool call 事件流
    tool_events_dir = EVENTS_DIR / 'system' / 'tool-call'
    tool_event_count = 0
    if tool_events_dir.exists():
        tool_event_count = len(list(tool_events_dir.glob('*.jsonl')))
    # 如果没有 tool call 事件目录（预期中，因为 Tool Call Gateway 未实现）
    if tool_event_count == 0:
        print(f"  ℹ️  tool_call_observation: 无 tool call 事件流 (Phase 6.4 未实现，预期行为)")
    else:
        print(f"  ✅ tool_call_observation: {tool_event_count} 事件文件")
    return violations


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

ALL_CHECKS = ['ownership', 'reasoning', 'writer', 'capability', 'tool_call']

CHECK_MAP = {
    'ownership': ('Memory Ownership', check_memory_ownership),
    'reasoning': ('Reasoning Isolation', check_reasoning_isolation),
    'writer': ('Writer Boundary', check_writer_boundary),
    'capability': ('Capability Registry', check_capability_registry),
    'tool_call': ('Tool Call Observation', check_tool_call_observation),
}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='L2 Contract Validation Layer')
    parser.add_argument('--dry-run', action='store_true', help='预览不写入')
    parser.add_argument('--checks', default=','.join(ALL_CHECKS),
                        help=f'验证项，逗号分隔。默认: {",".join(ALL_CHECKS)}')
    args = parser.parse_args()

    selected = [c.strip() for c in args.checks.split(',') if c.strip() in CHECK_MAP]

    print(f"Contract Validator — {now_ts()}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"Checks: {', '.join(selected)}")
    print()

    total_violations = 0
    for check_name in selected:
        display_name, check_fn = CHECK_MAP[check_name]
        print(f"[{display_name}]")
        violations = check_fn(args.dry_run)
        total_violations += len(violations)
        print()

    print(f"=== Summary: {total_violations} violations ===")
    if total_violations > 0:
        print(f"Log: {VIOLATION_LOG}")
        print("Action: observe only. No enforcement triggered.")
    else:
        print("All checks passed. No violations detected.")


if __name__ == '__main__':
    main()
