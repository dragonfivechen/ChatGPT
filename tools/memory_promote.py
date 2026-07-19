#!/usr/bin/env python3
"""
memory_promote.py — 规则候选升级引擎 (v2.0 + Patch-001/002/003/004)

从 memory/candidates/ 选取已审批候选，写入 memory/rules/<category>.yaml。

Patch-001: Promotion Approval Gate — 需先经过 approved 状态
Patch-002: SOUL.md 写入已从自动流程中移除，改为显式 --soul
Patch-003: 每个 promoted rule 必须包含证据契约
Patch-004: Fact Provenance — source_event 为必填

用法:
  python3 tools/memory_promote.py list                          # 列出候选
  python3 tools/memory_promote.py validate <id>                 # 标记为 validated
  python3 tools/memory_promote.py approve <id>                  # 标记为 approved
  python3 tools/memory_promote.py promote <id>                  # 升级（需 approved）
  python3 tools/memory_promote.py promote <id> --soul           # 升级并允许写入 SOUL.md
  python3 tools/memory_promote.py promote-all                   # 批量升级已 approved
  python3 tools/memory_promote.py promote-all --dry-run         # 预览
  python3 tools/memory_promote.py reject <id>                   # 拒绝
"""
import json, sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
CANDIDATES_DIR = WORKSPACE / 'memory' / 'candidates'
RULES_DIR = WORKSPACE / 'memory' / 'rules'
ARCHIVE_DIR = WORKSPACE / 'memory' / 'archive'

# Promotion 状态机：state 流转顺序
PROMOTION_STATES = ['pending', 'validated', 'approved', 'promoted', 'rejected']
VALID_TRANSITIONS = {
    'pending':   ['validated', 'rejected'],
    'validated': ['approved', 'rejected'],
    'approved':  ['promoted', 'rejected'],
    'promoted':  [],
    'rejected':  [],
}

# 规则文件映射
RULE_FILES = {
    'interaction':  RULES_DIR / 'interaction.yaml',
    'project':      RULES_DIR / 'project.yaml',
    'architecture': RULES_DIR / 'architecture.yaml',
    'governance':   RULES_DIR / 'governance.yaml',
}

DEFAULT_RULES_TEMPLATES = {
    'interaction.yaml': "# interaction.yaml — 交互行为规则\n# 自动管理，手动修改会被治理管道覆盖\nrules:\n  - rule: \"暂无规则\"\n    source: \"system_init\"\n    promoted: \"2026-07-20\"\n    score: 0\n",
    'project.yaml': "# project.yaml — 项目级规则\n# 自动管理，手动修改会被治理管道覆盖\nrules:\n  - rule: \"暂无规则\"\n    source: \"system_init\"\n    promoted: \"2026-07-20\"\n    score: 0\n",
    'architecture.yaml': "# architecture.yaml — 架构治理规则\n# 自动管理，手动修改会被治理管道覆盖\nrules:\n  - rule: \"暂无规则\"\n    source: \"system_init\"\n    promoted: \"2026-07-20\"\n    score: 0\n",
    'governance.yaml': "# governance.yaml — 治理原则\n# 自动管理，手动修改会被治理管道覆盖\nrules:\n  - rule: \"暂无规则\"\n    source: \"system_init\"\n    promoted: \"2026-07-20\"\n    score: 0\n",
}


def init_rules_dir():
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for fname in RULE_FILES.values():
        fname = Path(fname)
        if not fname.exists():
            with open(fname, 'w') as f:
                f.write(DEFAULT_RULES_TEMPLATES.get(fname.name, f"# {fname.name}\nrules: []\n"))


def load_candidates() -> list:
    if not CANDIDATES_DIR.exists():
        return []
    cands = []
    for f in sorted(CANDIDATES_DIR.glob('rule-candidate-*.json')):
        try:
            with open(f) as fh:
                cands.append(json.load(fh))
        except json.JSONDecodeError:
            pass
    return cands


def save_candidate(candidate: dict):
    """写回候选文件"""
    out_path = CANDIDATES_DIR / f"{candidate['id']}.json"
    with open(out_path, 'w') as f:
        json.dump(candidate, f, ensure_ascii=False, indent=2)


def load_rules(category: str) -> dict:
    target = RULE_FILES.get(category)
    if not target or not target.exists():
        return {'rules': []}
    try:
        import yaml
        with open(target) as fh:
            data = yaml.safe_load(fh)
        if data and isinstance(data, dict):
            return data
    except Exception:
        pass
    return {'rules': []}


def save_rules(category: str, rules_data: dict):
    target = RULE_FILES[category]
    import yaml
    import io
    buf = io.StringIO()
    yaml.dump(rules_data, buf, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = buf.getvalue()
    template = DEFAULT_RULES_TEMPLATES.get(target.name, '')
    header_lines = []
    for line in template.split('\n'):
        if line.startswith('#') or line.strip() == '':
            header_lines.append(line)
        else:
            break
    with open(target, 'w') as f:
        for hl in header_lines:
            f.write(hl + '\n')
        f.write(content)
    print(f"  ✅ 已写入 {target}")


# ── Patch-001: Approval Gate ──

def _transition_allowed(current: str, target: str) -> bool:
    if target not in PROMOTION_STATES:
        return False
    if current == target:
        return True
    return target in VALID_TRANSITIONS.get(current, [])


def transition(candidate: dict, target_state: str, reason: str = '') -> bool:
    """执行状态转换"""
    current = candidate.get('state', 'pending')
    if not _transition_allowed(current, target_state):
        print(f"  ⛔ 状态转换拒绝: {current} → {target_state}")
        return False
    candidate['state'] = target_state
    candidate['state_changed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    if reason:
        candidate.setdefault('state_log', []).append({
            'from': current,
            'to': target_state,
            'reason': reason,
            'at': candidate['state_changed_at'],
        })
    save_candidate(candidate)
    print(f"  ✅ {candidate['id']}: {current} → {target_state}")
    return True


# ── Patch-003: Promotion Evidence Contract ──

REQUIRED_EVIDENCE_FIELDS = [
    'source_event', 'validator', 'approved_at', 'approval_reason', 'promotion_id',
]


def _check_evidence(candidate: dict) -> list:
    missing = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        if not candidate.get(field):
            missing.append(field)
    return missing


# ── Patch-004: Fact Provenance ──

def _enforce_provenance(candidate: dict) -> list:
    issues = []
    if not candidate.get('source_event'):
        issues.append('source_event is required for promotion')
    return issues


# ── Patch-005: Unified Truth Write Gate ──

def validate_promotion_authority(candidate: dict) -> tuple[bool, list[str]]:
    """
    统一写入门：所有 Truth 写入（Facts / Rules / SOUL）必须通过此门。

    Returns:
        (passed: bool, reasons: list[str])
    """
    reasons = []

    # 1. 状态检查
    if candidate.get('state') != 'approved':
        reasons.append(f"state='{candidate.get('state')}', 需要 'approved'")

    # 2. 证据契约检查
    missing = _check_evidence(candidate)
    if missing:
        reasons.append(f"证据契约缺失: {', '.join(missing)}")

    # 3. 来源追溯检查
    provenance_issues = _enforce_provenance(candidate)
    reasons.extend(provenance_issues)

    return len(reasons) == 0, reasons


# ── Patch-002: SOUL.md is explicit only ──

SOUL_MD_FLAG = '--soul'


def promote_to_soulmd(candidate: dict, dry_run: bool = False) -> bool:
    """仅当显式 --soul 标志时写入 SOUL.md — 通过 unified gate 验证"""
    rule_text = candidate.get('candidate', '')
    if not rule_text:
        return False

    # Patch-005: 走统一写入门
    passed, reasons = validate_promotion_authority(candidate)
    if not passed:
        print(f"  ⛔ SOUL.md 写入拒绝: {'; '.join(reasons)}")
        return False

    if dry_run:
        print(f"  [DRY RUN] 写入 SOUL.md: {rule_text}")
        return True
    soul_path = WORKSPACE / 'SOUL.md'
    with open(soul_path, 'a') as f:
        f.write(f"\n- {rule_text}  # {candidate['id']}\n")
    print(f"  ✅ 已写入 SOUL.md")
    return True


# ── Core: promote ──

def promote(candidate: dict, dry_run: bool = False, write_soul: bool = False) -> bool:
    """升级候选规则 — 通过 unified gate 验证"""
    # Patch-005: 走统一写入门
    passed, reasons = validate_promotion_authority(candidate)
    if not passed:
        print(f"  ⛔ 升级拒绝: {'; '.join(reasons)}")
        return False

    category = candidate.get('category', 'interaction')
    rule_text = candidate.get('candidate', '')
    if not rule_text:
        return False

    if dry_run:
        print(f"  [DRY RUN] 升级到 {RULE_FILES.get(category)}: {rule_text}")
        return True

    rules_data = load_rules(category)
    rules = rules_data.get('rules', [])

    # 去重
    for existing in rules:
        if rule_text in existing.get('rule', '') or existing.get('rule', '') in rule_text:
            existing['score'] = max(existing.get('score', 0), candidate.get('score', 0))
            existing['hit_count'] = existing.get('hit_count', 1) + candidate.get('hit_count', 1)
            existing['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            existing['source'] = candidate.get('source_event', existing.get('source', ''))
            save_rules(category, rules_data)
            print(f"  ✅ 更新已有规则 (score={existing['score']:.3f})")
            return True

    # 新规则 — Patch-003: 完整证据契约
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    new_rule = {
        'rule': rule_text,
        'source': candidate.get('source_event', ''),
        'promoted': now_ts,
        'score': candidate.get('score', 0),
        'hit_count': candidate.get('hit_count', 1),
        'promotion_id': candidate.get('promotion_id', f"promote-{candidate['id']}"),
        'validator': candidate.get('validator', 'system'),
        'approved_at': candidate.get('approved_at', now_ts),
        'approval_reason': candidate.get('approval_reason', ''),
    }
    rules.append(new_rule)
    rules_data['rules'] = rules
    save_rules(category, rules_data)
    return True


def review_gate(candidate: dict) -> tuple:
    """审核门 — 检查基本完整性"""
    reasons = []
    if not candidate.get('candidate'):
        reasons.append('缺少规则文本')
    state = candidate.get('state', 'pending')
    if state not in ('pending', 'validated', 'approved'):
        reasons.append(f"state 不允许: {state}")
    text = candidate.get('candidate', '')
    if len(text) < 10:
        reasons.append('规则文本过短')
    if len(text) > 500:
        reasons.append('规则文本过长')
    return len(reasons) == 0, reasons


# ── CLI ──

def main():
    init_rules_dir()
    candidates = load_candidates()

    if not candidates:
        print("无待处理候选")
        return

    if len(sys.argv) < 2:
        print("用法: memory_promote.py list|validate|approve|promote|reject <id> [--dry-run] [--soul]")
        sys.exit(1)

    action = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    write_soul = SOUL_MD_FLAG in sys.argv

    if action == 'list':
        print(f"=== 候选列表 ({len(candidates)} 条) ===")
        for c in candidates:
            state = c.get('state', c.get('status', 'unknown'))
            score = c.get('score', 0)
            conf = c.get('confidence', 0)
            cat = c.get('category', '?')
            has_evidence = all(c.get(f) for f in REQUIRED_EVIDENCE_FIELDS)
            ev_tag = '📋' if has_evidence else '⚠️'
            print(f"  {c['id']} [{cat}] state={state} score={score:.3f} conf={conf} {ev_tag}")
            print(f"    '{c['candidate'][:80]}'")
        return

    if action == 'validate' and len(sys.argv) > 2:
        found = [c for c in candidates if c['id'] == sys.argv[2]]
        if not found:
            print(f"未找到: {sys.argv[2]}")
            sys.exit(1)
        transition(found[0], 'validated')
        return

    if action == 'approve' and len(sys.argv) > 2:
        found = [c for c in candidates if c['id'] == sys.argv[2]]
        if not found:
            print(f"未找到: {sys.argv[2]}")
            sys.exit(1)
        c = found[0]
        # 自动填充 evidence 字段（留空则提示）
        if not c.get('validator'):
            c['validator'] = 'system'
        if not c.get('approved_at'):
            c['approved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        if not c.get('promotion_id'):
            c['promotion_id'] = f"promote-{c['id']}"
        if not c.get('approval_reason'):
            c['approval_reason'] = '(待填写)'
        transition(c, 'approved')
        return

    if action == 'promote' and len(sys.argv) > 2:
        found = [c for c in candidates if c['id'] == sys.argv[2]]
        if not found:
            print(f"未找到: {sys.argv[2]}")
            sys.exit(1)
        c = found[0]
        promoted = promote(c, dry_run, write_soul)
        if promoted and not dry_run:
            if write_soul:
                promote_to_soulmd(c, dry_run)
            transition(c, 'promoted')
            print(f"  ✅ {c['id']} 已升级")
        return

    if action == 'promote-all':
        promoted_count = 0
        for c in candidates:
            if c.get('state') != 'approved':
                continue
            if promote(c, dry_run, write_soul):
                if not dry_run:
                    if write_soul and c.get('category') == 'interaction':
                        promote_to_soulmd(c, dry_run)
                    transition(c, 'promoted')
                promoted_count += 1
        print(f"\n共升级 {promoted_count}/{len(candidates)} 条 ({'dry-run' if dry_run else '生效'})")
        return

    if action == 'reject' and len(sys.argv) > 2:
        found = [c for c in candidates if c['id'] == sys.argv[2]]
        if not found:
            print(f"未找到: {sys.argv[2]}")
            sys.exit(1)
        transition(found[0], 'rejected', sys.argv[3] if len(sys.argv) > 3 else '')
        return

    print(f"未知操作: {action}")


if __name__ == '__main__':
    main()
