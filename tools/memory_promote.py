#!/usr/bin/env python3
"""
memory_promote.py — 规则候选升级引擎

从 memory/candidates/ 选取高评分候选，写入 memory/rules/<category>.yaml。

用法:
  python3 tools/memory_promote.py list               # 列出可升级候选
  python3 tools/memory_promote.py promote <id>       # 升级指定候选
  python3 tools/memory_promote.py promote-all         # 批量升级（score > 0.75）
  python3 tools/memory_promote.py promote-all --dry-run  # 预览
  python3 tools/memory_promote.py promote-all --force    # 覆盖所有 pending
"""
import json, sys
from pathlib import Path
from datetime import datetime
import shutil

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
CANDIDATES_DIR = WORKSPACE / 'memory' / 'candidates'
RULES_DIR = WORKSPACE / 'memory' / 'rules'
ARCHIVE_DIR = WORKSPACE / 'memory' / 'archive'

# 规则文件映射
RULE_FILES = {
    'interaction': RULES_DIR / 'interaction.yaml',
    'project': RULES_DIR / 'project.yaml',
    'architecture': RULES_DIR / 'architecture.yaml',
    'governance': RULES_DIR / 'governance.yaml',
}

# 默认规则文件模版
DEFAULT_RULES_TEMPLATES = {
    'interaction.yaml': """# interaction.yaml — 交互行为规则
# 自动管理，手动修改会被治理管道覆盖
rules:
  - rule: "暂无规则"
    source: "system_init"
    promoted: "2026-07-20"
    score: 0
""",
    'project.yaml': """# project.yaml — 项目级规则
# 自动管理，手动修改会被治理管道覆盖
rules:
  - rule: "暂无规则"
    source: "system_init"
    promoted: "2026-07-20"
    score: 0
""",
    'architecture.yaml': """# architecture.yaml — 架构治理规则
# 自动管理，手动修改会被治理管道覆盖
rules:
  - rule: "暂无规则"
    source: "system_init"
    promoted: "2026-07-20"
    score: 0
""",
    'governance.yaml': """# governance.yaml — 治理原则
# 自动管理，手动修改会被治理管道覆盖
rules:
  - rule: "暂无规则"
    source: "system_init"
    promoted: "2026-07-20"
    score: 0
""",
}


def init_rules_dir():
    """初始化 rules 目录"""
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


def load_rules(category: str) -> dict:
    """加载某类已有规则"""
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
    """保存规则到 YAML（保留注释头）"""
    target = RULE_FILES[category]
    import yaml
    import io
    buf = io.StringIO()
    yaml.dump(rules_data, buf, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = buf.getvalue()
    # 从模板提取注释头（不包含 rules: 行）
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


def promote(candidate: dict, dry_run: bool = False) -> bool:
    """升级候选规则"""
    category = candidate.get('category', 'interaction')
    rule_text = candidate.get('candidate', '')
    
    if not rule_text:
        return False
    
    if dry_run:
        print(f"  [DRY RUN] 升级到 {RULE_FILES.get(category)}:")
        print(f"    rule: {rule_text}")
        print(f"    score: {candidate.get('score', 0):.3f}")
        return True
    
    # 加载已有规则
    rules_data = load_rules(category)
    rules = rules_data.get('rules', [])
    
    # 去重（规则库级别）
    for existing in rules:
        if rule_text in existing.get('rule', '') or existing.get('rule', '') in rule_text:
            # 已有相似规则：更新 score
            existing['score'] = max(existing.get('score', 0), candidate.get('score', 0))
            existing['hit_count'] = existing.get('hit_count', 1) + candidate.get('hit_count', 1)
            existing['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            existing['source'] = candidate.get('source_event', existing.get('source', ''))
            save_rules(category, rules_data)
            return True  # 更新，不是新增
    
    # 新规则
    new_rule = {
        'rule': rule_text,
        'source': candidate.get('source_event', ''),
        'promoted': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'score': candidate.get('score', 0),
        'hit_count': candidate.get('hit_count', 1),
    }
    rules.append(new_rule)
    rules_data['rules'] = rules
    save_rules(category, rules_data)
    return True


def promote_to_interaction_rule(candidate: dict, dry_run: bool = False) -> bool:
    """高优先级交互规则 → 写入 SOUL.md"""
    rule_text = candidate.get('candidate', '')
    if not rule_text:
        return False
    
    if dry_run:
        print(f"  [DRY RUN] 写入 SOUL.md:")
        print(f"    {rule_text}")
        return True
    
    soul_path = WORKSPACE / 'SOUL.md'
    with open(soul_path, 'a') as f:
        f.write(f"\n- {rule_text}  # {candidate['id']}\n")
    return True


def archive_candidate(candidate: dict):
    """归档已升级的候选"""
    candidate['archived_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    candidate['status'] = 'approved'
    
    out_path = CANDIDATES_DIR / f"{candidate['id']}.json"
    with open(out_path, 'w') as f:
        json.dump(candidate, f, ensure_ascii=False, indent=2)


def review_gate(candidate: dict) -> tuple:
    """审核门"""
    reasons = []
    if not candidate.get('candidate'):
        reasons.append('缺少规则文本')
    if candidate.get('status') not in ('pending', 'deduped'):
        reasons.append(f"状态不允许: {candidate.get('status')}")
    text = candidate.get('candidate', '')
    if len(text) < 10:
        reasons.append('规则文本过短')
    if len(text) > 500:
        reasons.append('规则文本过长')
    return len(reasons) == 0, reasons


def main():
    init_rules_dir()
    candidates = load_candidates()
    
    if not candidates:
        print("无待处理候选")
        return
    
    if len(sys.argv) < 2:
        print("用法: memory_promote.py list|promote|promote-all [--dry-run] [--force]")
        sys.exit(1)
    
    action = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    
    if action == 'list':
        print(f"=== 候选列表 ({len(candidates)} 条) ===")
        for c in candidates:
            status = c.get('status', 'unknown')
            score = c.get('score', 0)
            conf = c.get('confidence', 0)
            cat = c.get('category', '?')
            passed, reasons = review_gate(c)
            gate = '✅' if passed else '⛔'
            print(f"  {c['id']} [{cat}] status={status} score={score:.3f} conf={conf} {gate}")
            print(f"    '{c['candidate'][:80]}'")
            if not passed:
                print(f"    原因: {', '.join(reasons)}")
        return
    
    if action == 'promote' and len(sys.argv) > 2:
        rule_id = sys.argv[2]
        found = [c for c in candidates if c['id'] == rule_id]
        if not found:
            print(f"未找到: {rule_id}")
            sys.exit(1)
        c = found[0]
        passed, reasons = review_gate(c)
        if not passed:
            print(f"审核未通过: {', '.join(reasons)}")
            sys.exit(1)
        
        promote(c, dry_run)
        promote_to_interaction_rule(c, dry_run)
        if not dry_run:
            archive_candidate(c)
        print(f"  {c['id']} → {'dry-run' if dry_run else '已升级'}")
        return
    
    if action == 'promote-all':
        promoted_count = 0
        for c in candidates:
            if c.get('status') not in ('pending', 'deduped'):
                continue
            
            score = c.get('score', 0)
            if score < 0.75 and not force:
                if c.get('confidence', 0) < 0.8:
                    continue
            
            passed, reasons = review_gate(c)
            if not passed:
                continue
            
            # 升级
            cat = c.get('category', 'interaction')
            if cat == 'interaction' and score > 0.85:
                promote_to_interaction_rule(c, dry_run)
            
            promote(c, dry_run)
            if not dry_run:
                archive_candidate(c)
            promoted_count += 1
        
        print(f"\n共升级 {promoted_count}/{len(candidates)} 条 ({'dry-run' if dry_run else '生效'})")
        return
    
    print(f"未知操作: {action}")


if __name__ == '__main__':
    main()
