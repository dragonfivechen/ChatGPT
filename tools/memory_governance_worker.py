#!/usr/bin/env python3
"""
memory_governance_worker.py — Memory 治理流水线

完整的治理管道：
  事件扫描 → 反馈检测 → 候选提取 → 去重评分 → 升级生效

用法:
  python3 tools/memory_governance_worker.py                      # 完整运行
  python3 tools/memory_governance_worker.py --dry-run             # 预览模式
  python3 tools/memory_governance_worker.py --days 7              # 扫描最近7天
  python3 tools/memory_governance_worker.py --agent huo           # 指定身份
  python3 tools/memory_governance_worker.py --until-promote       # 执行到升级步骤
  python3 tools/memory_governance_worker.py status                # 状态报告
"""
import json, sys, subprocess, os
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path.home() / '.openclaw' / 'workspace'
TOOLS_DIR = WORKSPACE / 'tools'
CANDIDATES_DIR = WORKSPACE / 'memory' / 'candidates'
RULES_DIR = WORKSPACE / 'memory' / 'rules'
EVENTS_DIR = WORKSPACE / 'memory' / 'events'

# 日志输出路径
PIPELINE_LOG = WORKSPACE / 'memory' / 'data' / 'governance-pipeline.jsonl'
GOVERNANCE_STATE = WORKSPACE / 'memory' / 'data' / 'system' / 'governance-state.json'
GOVERNANCE_LAST = WORKSPACE / 'memory' / 'data' / 'system' / 'governance-last.json'
GOVERNANCE_LOG = WORKSPACE / 'memory' / 'data' / 'system' / 'governance-pipeline.log'
GOVERNANCE_ERR = WORKSPACE / 'memory' / 'data' / 'system' / 'governance-error.log'


def run_script(name: str, args: list = None, dry_run: bool = False):
    """运行治理脚本"""
    script = TOOLS_DIR / name
    if not script.exists():
        print(f"[ERR] 脚本不存在: {script}")
        return None
    
    cmd = [sys.executable, str(script)]
    if args:
        cmd.extend(args)
    if dry_run:
        cmd.append('--dry-run')
    
    print(f"\n{'='*60}")
    print(f"  ▶ {name} {' '.join(args or [])}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(WORKSPACE))
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"[stderr] {result.stderr[:500]}")
    
    return result


def pipeline_status() -> dict:
    """获取治理流水线状态"""
    status = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'events': {},
        'candidates': {'pending': 0, 'deduped': 0, 'approved': 0, 'duplicate': 0, 'total': 0},
        'rules': {},
        'last_run': None,
    }
    
    # 扫描事件
    for agent_dir in sorted(EVENTS_DIR.iterdir()):
        if agent_dir.is_dir():
            md_files = list(agent_dir.glob('*.md'))
            jsonl_files = list(agent_dir.glob('*.jsonl'))
            last_modified = max(f.stat().st_mtime for f in [*md_files, *jsonl_files]) if md_files or jsonl_files else 0
            status['events'][agent_dir.name] = {
                'md_count': len(md_files),
                'jsonl_count': len(jsonl_files),
                'last_modified': datetime.fromtimestamp(last_modified).isoformat() if last_modified else 'never'
            }
    
    # 扫描候选
    if CANDIDATES_DIR.exists():
        for f in CANDIDATES_DIR.glob('rule-candidate-*.json'):
            try:
                with open(f) as fh:
                    c = json.load(fh)
                st = c.get('status', 'unknown')
                if st in status['candidates']:
                    status['candidates'][st] += 1
                else:
                    status['candidates'][st] = 1
                status['candidates']['total'] += 1
            except Exception:
                pass
    
    # 扫描规则
    if RULES_DIR.exists():
        for f in RULES_DIR.glob('*.yaml'):
            try:
                import yaml
                with open(f) as fh:
                    data = yaml.safe_load(fh)
                rules_count = len(data.get('rules', [])) if data else 0
            except Exception:
                rules_count = 0
            status['rules'][f.stem] = rules_count
    
    # 上次运行
    if PIPELINE_LOG.exists():
        try:
            with open(PIPELINE_LOG) as fh:
                last_line = fh.readlines()[-1] if fh else ''
            if last_line:
                last = json.loads(last_line)
                status['last_run'] = last.get('timestamp', 'unknown')
        except Exception:
            pass
    
    return status


def log_pipeline_run(action: str, status: dict):
    """记录流水线运行 (JSONL)"""
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'action': action,
        'status': {
            'candidates': status['candidates'],
            'rules': status['rules'],
        }
    }
    with open(PIPELINE_LOG, 'a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def write_state(status: dict, dry_run: bool = False):
    """写入治理状态 JSON（无模型调用，纯数据）"""
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'dry_run': dry_run,
        'events_scanned': sum(e['md_count'] + e['jsonl_count'] for e in status['events'].values()),
        'candidate_created': status['candidates'].get('pending', 0),
        'promoted': status['candidates'].get('approved', 0),
        'rejected': status['candidates'].get('deduped', 0) + status['candidates'].get('duplicate', 0),
        'rules_total': sum(status['rules'].values()) if status['rules'] else 0
    }
    
    # 写入 state（最新快照）
    GOVERNANCE_STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(GOVERNANCE_STATE, 'w') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    
    # 写入 last（最近一次运行摘要）
    with open(GOVERNANCE_LAST, 'w') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    
    print(f"[state] wrote: {GOVERNANCE_STATE.name} | events={record['events_scanned']} candidates={record['candidate_created']} promoted={record['promoted']}")


def main():
    # 管道日志标记
    GOV_LOG = GOVERNANCE_LOG
    GOV_ERR = GOVERNANCE_ERR
    
    GOV_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"START {datetime.now().isoformat()}")
    
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        st = pipeline_status()
        print("=== Memory Governance Pipeline Status ===")
        print(f"\nEvents:")
        for agent, info in st['events'].items():
            print(f"  {agent}: {info['md_count']} md, {info['jsonl_count']} jsonl")
        print(f"\nCandidates: {st['candidates']['total']} total")
        for k in ['pending', 'deduped', 'approved', 'duplicate']:
            print(f"  {k}: {st['candidates'].get(k, 0)}")
        print(f"\nRules:")
        for name, count in st['rules'].items():
            print(f"  {name}: {count} rules")
        print(f"\nLast run: {st.get('last_run', 'never')}")
        return
    
    dry_run = '--dry-run' in sys.argv
    days = 3
    agent = None
    until_promote = False
    
    for i, arg in enumerate(sys.argv):
        if arg == '--days' and i+1 < len(sys.argv):
            days = int(sys.argv[i+1])
        if arg == '--agent' and i+1 < len(sys.argv):
            agent = sys.argv[i+1]
        if arg == '--until-promote':
            until_promote = True
    
    print(f"{'='*60}")
    print(f"  Memory Governance Pipeline v1.0")
    print(f"  Days: {days} | Agent: {agent or 'all'} | Dry-run: {dry_run}")
    print(f"{'='*60}")
    
    # Step 1: Feedback Detection + Candidate Extraction
    extract_args = ['--days', str(days)]
    if agent:
        extract_args.extend(['--agent', agent])
    
    result = run_script('memory_candidate_extract.py', extract_args, dry_run)
    if result is None:
        sys.exit(1)
    
    # Step 2: Dedup + Scoring
    dedup_args = []
    if dry_run:
        dedup_args.append('--list')
    
    run_script('memory_dedup.py', dedup_args, dry_run=False)  # dedup always runs (safe, no write if --list)
    
    if until_promote:
        print("\n[stop] --until-promote, 跳过 promote")
    else:
        # Step 3: Promote
        promote_args = ['promote-all']
        if dry_run:
            promote_args.append('--dry-run')
        run_script('memory_promote.py', promote_args, dry_run)
    
    # Log + state file
    st = pipeline_status()
    log_pipeline_run('full-run' if not dry_run else 'dry-run', st)
    write_state(st, dry_run)
    
    print(f"\n{'='*60}")
    print(f"  Pipeline {'Dry Run' if dry_run else 'Complete'}")
    print(f"  Candidates pending: {st['candidates']['pending']}")
    print(f"  Rules on file: {sum(st['rules'].values()) if st['rules'] else 0}")
    print(f"  State: {GOVERNANCE_STATE}")
    print(f"{'='*60}")


if __name__ == '__main__':
    try:
        main()
        print(f"END {datetime.now().isoformat()} exit=0")
    except Exception as e:
        err_msg = f"{datetime.now().isoformat()} FATAL: {e}"
        print(f"END {datetime.now().isoformat()} exit=1")
        with open(GOVERNANCE_ERR, 'a') as f:
            f.write(err_msg + '\n')
        print(err_msg, file=sys.stderr)
        sys.exit(1)
