#!/usr/bin/env python3
"""
memory_candidate_extract.py — 从反馈信号中提炼规则候选

输入：feedback events（来自 memory_feedback_detect.py）
输出：结构化规则候选 → memory/candidates/

用法:
  python3 tools/memory_candidate_extract.py                    # 自动扫描+提取
  python3 tools/memory_candidate_extract.py --agent huo        # 指定身份
  python3 tools/memory_candidate_extract.py --days 3           # 最近3天
  python3 tools/memory_candidate_extract.py --dry-run          # 预览不写入
"""
import re, json, sys
from pathlib import Path
from datetime import datetime, timezone


RULE_PATTERNS = [
    # 行为规则：不要/不应该/禁止/别
    (r'(?:不要|不应该|不允许|禁止|别)\s*(.+?)(?:[，。]|$)', 0.85),
    (r'(?:应该|必须|要)\s*(.+?)(?:[，。]|$)', 0.70),
    # 原则声明（带/不带 bullet 和 bold）
    (r'(?:-\s*)?\*{0,2}原则[：:]\s*(.+?)(?:[，。]|$)', 0.85),
    # 纪律/规则/准则/边界 声明
    (r'(?:纪律|规则|准则|边界)[：:]\s*(.+?)(?:[，。]|$)', 0.90),
    # 通用 bullet：用证据证明、调用方契约 这类非 section-header 的 bullet
    (r'-\s+(?!.*(?:阶段|Phase|##))(?:\*{0,2})?(.+?)(?:[，。]|$)', 0.65),
]

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
CANDIDATES_DIR = WORKSPACE / 'memory' / 'candidates'

# 引入反馈检测
sys.path.insert(0, str(WORKSPACE / 'tools'))
from memory_feedback_detect import scan_events



CATEGORY_KEYWORDS = {
    'interaction': ['问', '说', '确认', '解释', '回答', '输出', '回复'],
    'project': ['彩票', '日报', '报表', '推送', '通知', '格式'],
    'architecture': ['配置', '身份', '边界', '隔离', '模块', '路由', '记忆'],
}


def is_noise(text: str) -> bool:
    """噪声过滤"""
    noise_patterns = [
        r'^\|\s+\w+\s+\|',      # 表格行
        r'^\d+[.:]\d+',            # 版本号/编号
        r'^`[^`]+`',                 # 代码上下文
        r'^\w+/\w+\.\w+',         # 文件路径
        r'^\*\*\w+\*\*:',        # 标记属性
        r'^\d+\s*(ms|tok|条|%)',   # 指标
    ]
    return any(re.match(p, text) for p in noise_patterns)


def extract_rule_candidates(feedback_events: list) -> list:
    """从反馈事件中提炼规则候选"""
    candidates = []
    
    for fb in feedback_events:
        text = fb['text']
        
        # 噪声过滤
        if is_noise(text):
            continue
        
        # 尝试提取规则模式
        extracted = False
        for pattern, base_conf in RULE_PATTERNS:
            m = re.search(pattern, text)
            if m:
                rule_text = m.group(1).strip()
                # 清理 bold markers
                rule_text = rule_text.replace('**', '').replace('*', '').strip()
                # 跳过过短或过长
                if len(rule_text) < 8 or len(rule_text) > 200:
                    continue
                if is_noise(rule_text):
                    continue
                
                # 置信度调整
                conf = base_conf
                if fb['type'] == 'correction_explicit':
                    conf += 0.05
                elif fb['type'] == 'principle':
                    conf += 0.10
                conf = min(conf, 0.98)
                
                # 分类
                category = classify_rule(rule_text)
                
                candidates.append({
                    'candidate': rule_text,
                    'confidence': round(conf, 2),
                    'category': category,
                    'feedback_type': fb['type'],
                    'source': fb['source'],
                    'source_line': fb.get('line', 0),
                    'agent': fb.get('agent', 'unknown'),
                    'date': fb.get('date', 'unknown'),
                })
                extracted = True
        
        if not extracted and fb['type'] == 'correction_explicit':
            if is_noise(text):
                continue
            # 高置信度但无法提取规则模式 → 使用文本本身
            conf = min(0.80 + (0.05 if fb['type'] == 'principle' else 0), 0.95)
            category = classify_rule(text)
            candidates.append({
                'candidate': text[:150],
                'confidence': round(conf, 2),
                'category': category,
                'feedback_type': fb['type'],
                'source': fb['source'],
                'source_line': fb.get('line', 0),
                'agent': fb.get('agent', 'unknown'),
                'date': fb.get('date', 'unknown'),
            })
    
    return candidates


def classify_rule(text: str) -> str:
    """对规则文本自动分类"""
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return 'interaction'


def load_existing_candidates() -> list:
    """加载已有 candidates"""
    cands = []
    if CANDIDATES_DIR.exists():
        for f in sorted(CANDIDATES_DIR.glob('rule-candidate-*.json')):
            try:
                with open(f) as fh:
                    cands.append(json.load(fh))
            except json.JSONDecodeError:
                pass
    return cands


def is_duplicate(new_cand: dict, existing: list) -> bool:
    """简单去重检查"""
    new_text = new_cand.get('candidate', '')
    for ec in existing:
        old_text = ec.get('candidate', '')
        if new_text == old_text:
            return True
        if len(new_text) > 20 and new_text[:20] in old_text:
            return True
        if len(old_text) > 20 and old_text[:20] in new_text:
            return True
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='规则候选提取器')
    parser.add_argument('--agent', default=None, help='身份')
    parser.add_argument('--days', type=int, default=7, help='扫描天数')
    parser.add_argument('--dry-run', action='store_true', help='预览不写入')
    parser.add_argument('--min-confidence', type=float, default=0.65, help='最低置信度')
    args = parser.parse_args()
    
    # Step 1: 扫描反馈
    feedbacks, file_count = scan_events(args.agent, args.days)
    print(f"[detect] 扫描 {file_count} 文件，发现 {len(feedbacks)} 条反馈信号")
    
    # Step 2: 提取规则候选
    raw_candidates = extract_rule_candidates(feedbacks)
    print(f"[extract] 提炼 {len(raw_candidates)} 条规则候选")
    
    # Step 3: 去重 + 过滤
    existing = load_existing_candidates()
    dedup_count = 0
    confidence_filter = 0
    
    new_candidates = []
    for rc in raw_candidates:
        if rc['confidence'] < args.min_confidence:
            confidence_filter += 1
            continue
        if is_duplicate(rc, existing):
            dedup_count += 1
            continue
        new_candidates.append(rc)
    
    print(f"[filter] 置信度过滤: {confidence_filter}, 去重过滤: {dedup_count}")
    print(f"[output] 新候选: {len(new_candidates)} 条")
    
    if args.dry_run:
        print("\n=== 预览 ===")
        for nc in new_candidates:
            print(f"  [{nc['category']}] conf={nc['confidence']}: {nc['candidate'][:60]}")
        return
    
    # Step 4: 写入 candidates
    for idx, nc in enumerate(new_candidates):
        rule_id = f"rule-candidate-{nc['date']}-{idx:03d}"
        
        # 避免 ID 冲突
        existing_ids = {c['id'] for c in existing}
        base_id = rule_id
        counter = 1
        while rule_id in existing_ids:
            rule_id = f"{base_id}-{counter}"
            counter += 1
        
        candidate = {
            "id": rule_id,
            "source_event": nc['source'],
            "source_line": nc['source_line'],
            "agent": nc['agent'],
            "date": nc['date'],
            "category": nc['category'],
            "feedback_type": nc['feedback_type'],
            "candidate": nc['candidate'],
            "confidence": nc['confidence'],
            "score": 0.0,
            "hit_count": 1,
            "status": "pending"
        }
        
        out_path = CANDIDATES_DIR / f"{rule_id}.json"
        with open(out_path, 'w') as outf:
            json.dump(candidate, outf, ensure_ascii=False, indent=2)
        print(f"  🆕 {rule_id}: [{nc['category']}] '{nc['candidate'][:60]}...'")
    
    print(f"\n[total] 新增 {len(new_candidates)} 条候选 → {CANDIDATES_DIR}")


if __name__ == '__main__':
    main()
