```yaml
contract:
  name: EVIDENCE-CONTRACT
  version: v1.0
  purpose: 确保任何分析结论绑定可追溯证据，证据必须声明来源、范围、处理方式
  scope: 所有涉及系统数据分析的推理过程（燃🔥、烬🔥及任何未来 Agent）
  level: L1
  parent: FREEZE-CONTRACT
  owner: 燃🔥
  status: active
  type: evidence / analysis_governance
  authority_impact: A1
  created: 2026-07-21

verification:
  required: true
  method: manual
  evidence:
    - "memory/events/huo/"
    - "ollama-production.jsonl"

binding:
  target: model-context

enforcement:
  mode: advisory
  mechanism: bootstrap-prompt
```

# EVIDENCE-CONTRACT v1.0

> 证据契约 — 分析结论与事实之间的桥梁
> 等级: L1（基线治理级）
> 上位约束: FREEZE-CONTRACT
> 权限影响: A1（要求行动/证明）

**填补的缺口：**

```
事实产生
 ↓
事件记录
 ↓
证据引用   ← EVIDENCE-CONTRACT
 ↓
分析结论
 ↓
行动建议
```

**与已有契约的关系：**

```text
FREEZE-CONTRACT
 |
 ├── EVENT-SOURCE-CONTRACT   → 事实来源
 ├── MEMORY-OWNERSHIP-CONTRACT → 记忆来源
 ├── FACT-SOURCE-CONTRACT    → 事实真理源
 └── EVIDENCE-CONTRACT v1.0  → 分析结论与事实之间的桥梁
       ├── 证据提交规则
       ├── 数据范围声明
       ├── 分析验证门
       ├── 结论证明要求
       └── 违规纠正
```

**后续扩张原则：** 仅当出现重复违反案例后，再考虑增加自动检查。当前保持文档契约即可。

---

## 1. 证据对象定义

所有系统数据分析涉及的证据需声明元数据：

```yaml
evidence:
  id:          str          # 唯一标识
  source:      str          # 原始来源路径/名称
  timestamp_range:
    start:     str          # ISO-8601
    end:       str          # ISO-8601
  type:
    - raw_event             # 原始事件
    - log                   # 日志
    - metric                # 指标
    - file                  # 文件
    - command_output        # 命令执行结果
    - memory_record         # memory 记录
  integrity:
    hash:      str          # 可选文件哈希
    immutable: bool         # 原始数据是否不可变
```

---

## 2. 分析证据提交要求

任何数据分析结论提交时必须附 Evidence Package：

```text
1. 原始来源
2. 查询命令 / 提取方式
3. 原始数量（before_filter）
4. 过滤规则（filter）
5. 最终样本数量（after_filter）
6. 结论引用范围
```

**错误写法（无证据链）：**

> `event_classify 有30%失败`

**正确写法（有证据链）：**

```text
Evidence:
source: ollama-production.jsonl
filter: type=="event_classify"
records:
  before_filter: 240
  after_filter: 48
parser: jq '.output'
result:
  empty_output: 0
  multiline_output: 18
  single_label: 30
```

---

## 3. 分析前验证门

分析流程必须经过证据门：

```text
问题
 ↓
寻找证据
 ↓
验证证据完整性
 ↓
确认数据边界（scope / validity）
 ↓
统计
 ↓
分析
 ↓
结论
```

**禁止的顺序：**

```text
结论
 ↓
寻找支持证据
```

---

## 4. 数据范围契约

所有数据源必须标记：

```yaml
data_scope:
  environment:
    - production
    - evaluation
    - test

consumer:
  - human_only
  - automated

validity:
  - valid
  - invalid
  - contaminated
```

**应用示例：**

```yaml
ollama-eval.jsonl:
  scope: evaluation
  production: false

ollama-production.jsonl:
  scope: production
  production: true
  validity_note: "2026-07-21T04:00:33Z 前含 44 条引号 bug 缺陷记录"
```

---

## 5. 证据等级

| 等级 | 定义 | 适用场景 |
|:---:|:----|:---------|
| E0 | 无证据，推测 | 初始假设、排除方向 |
| E1 | 单条原始样本 | 现象描述、个案验证 |
| E2 | 多条原始记录（<10） | 模式识别、小范围确认 |
| E3 | 统计验证（≥10） | 定量结论、趋势分析 |
| E4 | 多来源交叉验证 | 根因确认、权威结论 |

**所有分析结论必须声明等级。**

示例：

```text
event_classify prompt 存在歧义

Evidence Level: E3

依据:
48 条生产记录统计
source: ollama-production.jsonl
parser: python3 逐行复核
```

---

## 6. 分析输出格式约束

分析结论统一格式：

```text
结论:
  （一句话结论）

证据:
  - source:
  - range:
  - count:

验证:
  - 是否生产数据:
  - 是否过滤:
  - 是否存在混入:
  - 数据边界确认:

置信等级:
  E0-E4
```

---

## 7. 违反与纠正

| 违反类型 | 后果 | 纠正方式 |
|:---------|:-----|:---------|
| 结论无证据 | 结论降级为 E0 | 补充证据链 |
| 证据范围声明错误 | 结论标记为 contaminated | 重新核查范围 |
| 跨数据集混用未声明 | 分析无效，需重新提交 | 分开统计+合并分析 |
| 伪造/篡改证据 | 永久记录 + 权限审查 | A4 级介入 |

---

## 8. 此事件的触发原因

此次 ollama-production 数据分析过程暴露的缺失：

| 发现项 | 缺失证据项 | 契约约束 |
|:-------|:-----------|:---------|
| 数据集混淆（eval vs production） | 缺少 scope 声明 | §4 数据范围契约 |
| jq 管道误读为"空输出" | 缺少 parser evidence 和原始样本复核 | §2 证据提交要求 |
| bash bug 错误归因于模型 | 缺少链路证据（echo → bash → jq） | §3 验证门 |
| event_classify 误判为空 | 缺少原始输出复核 | §2 证据提交要求 + §5 证据等级 |

---

## 附录 A：应用模板

```yaml
analysis_submission:
  question:
  evidence_package:
    source:
    query:
    before_filter:
    filter:
    after_filter:
    parser:
  conclusion:
  evidence_level:
  data_scope:
    environment:
    consumer:
    validity:
  verified:
    - production_data_checked
    - filter_disclosed
    - no_contamination
```
