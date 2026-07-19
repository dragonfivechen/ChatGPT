#!/usr/bin/env python3
"""
memory_dedup.py — 规则候选去重合并 + 评分引擎

加载 memory/candidates/，按语义相似度合并同类规则，
计算 Rule Score，更新候选状态。

用法:
  python3 tools/memory_dedup.py                          # 执行去重
  python3 tools/memory_dedup.py --list                   # 仅展示不修改
  python3 tools/memory_dedup.py --min-confidence 0.7     # 只处理高置信度
"""
import json, sys
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
CANDIDATES_DIR = WORKSPACE / 'memory' / 'candidates'
RULES_DIR = WORKSPACE / 'memory' / 'rules'

# Rule Scoring 权重
SCORE_WEIGHTS = {
    'confidence': 0.30,
    'hit_count': 0.25,
    'scope': 0.20,
    'behavior_impact': 0.15,
    'user_confirm': 0.10,
}

SCOPE_MAP = {
    'interaction': 0.6,
    'project': 0.8,
    'architecture': 1.0,
}

BEHAVIOR_IMPACT_MAP = {
    'correction_explicit': 1.0,
    'correction_implicit': 0.6,
    'principle': 0.8,
}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def extract_keywords(text: str) -> set:
    keywords = set()
    for w in text.replace('-', '').replace('，', '').replace('。', '').replace('？', '').replace('！', '').split():
        w = w.strip()
        if len(w) > 1:
            keywords.add(w)
    return keywords


def calculate_score(candidate: dict) -> float:
    """计算 Rule Score"""
    c = candidate.get('confidence', 0.5)
    h = candidate.get('hit_count', 1)
    
    feedback_type = candidate.get('feedback_type', 'unknown')
    scope = SCOPE_MAP.get(candidate.get('category', 'interaction'), 0.5)
    impact = BEHAVIOR_IMPACT_MAP.get(feedback_type, 0.5)
    
    # 用户确认（若candidate有confirm字段）
    user_confirm = 1.0 if candidate.get('user_confirm', False) else 0.5
    
    score = (
        SCORE_WEIGHTS['confidence'] * c +
        SCORE_WEIGHTS['hit_count'] * min(h / 5.0, 1.0) +
        SCORE_WEIGHTS['scope'] * scope +
        SCORE_WEIGHTS['behavior_impact'] * impact +
        SCORE_WEIGHTS['user_confirm'] * user_confirm
    )
    return round(score, 3)


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


def load_rules() -> dict:
    """加载已有规则用于去重"""
    rules = []
    if RULES_DIR.exists():
        for f in RULES_DIR.glob('*.yaml'):
            try:
                import yaml
                with open(f) as fh:
                    data = yaml.safe_load(fh)
                    if data and isinstance(data, dict):
                        rules.extend(data.get('rules', []))
            except Exception:
                pass
    return {'total': len(rules), 'texts': [r.get('rule', '') for r in rules]}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='候选去重+评分')
    parser.add_argument('--list', action='store_true', help='仅展示不修改')
    parser.add_argument('--min-confidence', type=float, default=0.0, help='最低置信度过滤')
    args = parser.parse_args()
    
    candidates = load_candidates()
    if not candidates:
        print("无待处理候选")
        return
    
    rules_data = load_rules()
    
    # 过滤
    if args.min_confidence > 0:
        candidates = [c for c in candidates if c.get('confidence', 0) >= args.min_confidence]
    
    print(f"加载 {len(candidates)} 条候选 | 已有 {rules_data['total']} 条规则")
    print()
    
    # 处理
    processed = set()
    results = []
    
    for i, c in enumerate(candidates):
        if c['id'] in processed or c.get('status') == 'duplicate':
            continue
        
        group = [c]
        processed.add(c['id'])
        
        # 找相似候选
        for j in range(i+1, len(candidates)):
            if candidates[j]['id'] in processed:
                continue
            
            sim = similarity(c['candidate'], candidates[j]['candidate'])
            kw_a = extract_keywords(c['candidate'])
            kw_b = extract_keywords(candidates[j]['candidate'])
            union = max(len(kw_a | kw_b), 1)
            overlap = len(kw_a & kw_b) / union
            
            if sim > 0.55 or overlap > 0.4:
                group.append(candidates[j])
                processed.add(candidates[j]['id'])
        
        if len(group) > 1:
            # 合并
            best = max(group, key=lambda x: x.get('confidence', 0))
            
            # 增加 hit count
            total_hits = sum(g.get('hit_count', 1) for g in group)
            merged_conf = max(g.get('confidence', 0) for g in group)
            
            best['hit_count'] = total_hits
            best['confidence'] = round(merged_conf, 2)
            
            # 计算分数
            score = calculate_score(best)
            best['score'] = score
            
            if not args.list:
                best['status'] = 'deduped'
                best['merged_group'] = [g['id'] for g in group]
                with open(CANDIDATES_DIR / f"{best['id']}.json", 'w') as fh:
                    json.dump(best, fh, ensure_ascii=False, indent=2)
                
                # 标记其他为 duplicate
                for g in group:
                    if g['id'] != best['id']:
                        g['status'] = 'duplicate'
                        g['merged_into'] = best['id']
                        g['notes'] = f"合并至 {best['id']}"
                        with open(CANDIDATES_DIR / f"{g['id']}.json", 'w') as fh:
                            json.dump(g, fh, ensure_ascii=False, indent=2)
            
            results.append({
                'type': 'merge',
                'count': len(group),
                'id': best['id'],
                'text': best['candidate'],
                'confidence': merged_conf,
                'score': score,
                'hits': total_hits,
            })
        else:
            score = calculate_score(c)
            c['score'] = score
            if not args.list and c.get('status') == 'pending':
                c['status'] = 'deduped'
                with open(CANDIDATES_DIR / f"{c['id']}.json", 'w') as fh:
                    json.dump(c, fh, ensure_ascii=False, indent=2)
            
            results.append({
                'type': 'single',
                'count': 1,
                'id': c['id'],
                'text': c['candidate'],
                'confidence': c.get('confidence', 0),
                'score': score,
                'hits': c.get('hit_count', 1),
            })
    
    # 排序输出
    results.sort(key=lambda r: r['score'], reverse=True)
    
    print("=== 去重+评分结果 ===")
    for r in results:
        tag = '🔗' if r['type'] == 'merge' else '📄'
        print(f"  {tag} score={r['score']:.3f} conf={r['confidence']} hits={r['hits']}")
        print(f"     '{r['text'][:80]}'")
    
    # 统计
    pending = [c for c in candidates if c.get('status') == 'pending']
    deduped = [c for c in candidates if c.get('status') == 'deduped']
    dups = [c for c in candidates if c.get('status') == 'duplicate']
    
    print(f"\n待审核: {len(pending)} | 已去重: {len(deduped)} | 合并/重复: {len(dups)}")
    print(f"最高分 candidate: score={results[0]['score']:.3f}" if results else "")
    
    # 推荐升级（score > 0.75）
    recommend = [r for r in results if r['score'] > 0.75]
    if recommend:
        print(f"\n推荐升级 ({len(recommend)} 条):")
        for r in recommend:
            print(f"  {r['id']} (score={r['score']:.3f})")

if __name__ == '__main__':
    main()
