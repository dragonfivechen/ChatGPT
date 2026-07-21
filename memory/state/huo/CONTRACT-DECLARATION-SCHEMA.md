# CONTRACT-DECLARATION-SCHEMA v1.0

> 治理契约声明块 schema — 定义 META-CONTRACT 体系下所有 Governance Contract 的标准字段
> 归属: M0 META-CONTRACT v1.2
> 与 OpenClaw Runtime Contract 的关系: 不同抽象层，无字段冲突

---

## 1. 定位

本 schema 约束的是 **Governance Contract（治理契约）** 的声明块，不是 OpenClaw 源码中的 Runtime Contract（TypeScript interface / JSON schema / test fixture）。

治理契约声明块是 markdown 文件头部的 yaml 代码块，用于 META-CONTRACT 识别、Registry 索引、等级判定。

---

## 2. 声明块字段定义

```yaml
contract:
  name:          str        # 契约名称（大写，下划线分隔）
  purpose:       str        # 存在理由（一句话，必须）
  scope:         str        # 影响范围描述（非枚举，描述性文本）
  level:         str        # M0 / L0 / L1 / L2 / L3 / L4
  parent:        str|null   # 上位契约（null 表示无）
  owner:         str        # Owner 身份
  status:        str        # proposal / active / frozen / deprecated / archived

verification:
  required:      bool       # 是否需要验证
  method:        str        # source / runtime / manual
  evidence:      [str]      # 证据路径列表

  comment: "verification 块为可选。不声明表示 verification_status: unknown"
```

---

## 3. 可选扩展字段

```yaml
contract:
  version:       str        # 语义版本号（推荐）
  type:          str        # 语义分类（如 boundary / capability / privilege_control）
  authority_impact: str     # A0-A4（META-CONTRACT v1.2 Q7）
  created:       str        # ISO-8601 日期
  binding:                  # 约束生效层
    target:      str        # runtime / workspace / model-context / os

  enforcement:              # 约束执行方式
    mode:        str        # automatic / procedural / advisory
    mechanism:   str        # 具体执行机制（gateway-policy / governance-review / bootstrap-prompt）
```

---

## 4. 字段约束

| 字段 | 必填 | 限制 |
|------|:----:|------|
| name | ✅ | 仅允许大写字母、数字、下划线、连字符 |
| purpose | ✅ | 一句话描述契约存在理由 |
| scope | ✅ | 描述性文本，说明约束范围 |
| level | ✅ | 仅允许 M0/L0/L1/L2/L3/L4 |
| parent | ✅ | 必须引用 Registry 中已登记的契约名，或 null |
| owner | ✅ | 有效身份标识 |
| status | ✅ | 仅允许 proposal / active / frozen / deprecated / archived |
| version | ❌ | 推荐，语义版本格式 |
| type | ❌ | 自由文本，META-CONTRACT 内部语义分类 |
| authority_impact | ❌ | 仅允许 A0/A1/A2/A3/A4 |
| created | ❌ | ISO-8601 日期字符串 |
| verification.required | ❌ | bool |
| verification.method | ❌ | source / runtime / manual |
| binding.target | ❌ | runtime / workspace / model-context / os |
| enforcement.mode | ❌ | automatic / procedural / advisory |
| enforcement.mechanism | ❌ | 自由文本，描述具体执行机制 |

---

## 5. 状态值含义

| 状态 | 含义 |
|------|------|
| proposal | 提议中，未生效 |
| active | 活跃，可引用 |
| frozen | 冻结，不再修改 |
| deprecated | 废弃，不再推荐使用 |
| archived | 归档，历史记录 |

---

## 6. 与 OpenClaw Runtime Contract 的对比

| 维度 | Governance Contract（本 schema） | OpenClaw Runtime Contract |
|------|--------------------------------|--------------------------|
| 作用 | 治理规则声明 | 运行时 API/数据约束 |
| 格式 | YAML 代码块 + Markdown | TypeScript interface / JSON schema |
| 验证方式 | META-CONTRACT 五问 + 人工审查 | TypeScript 编译 + 运行时校验 |
| 声明位置 | `memory/state/huo/` 下的 `.md` 文件 | `.ts` 接口定义 / `.json` schema / `.json` 测试夹具 |
| 变更频率 | 低（治理冻结后极少变更） | 中（随功能迭代变更） |
| 字段交集 | 无字段冲突 | 不同命名空间 |

---

## 7. 完整示例

```yaml
contract:
  name: PRIVILEGE-CONTROL
  purpose: 定义特权操作的授权、执行、审计规则，防止权限滥用和跃迁
  scope: privileged operations (root, sudo, credential, irreversible)
  level: L1
  type: privilege_control
  authority_impact: A3
  parent: FREEZE-CONTRACT
  owner: 燃🔥
  status: active
  version: v1.0
  created: 2026-07-21
```

---

## 8. 历史迁移说明

本 schema 发布于所有现有契约之后。此前登记的 23 个契约声明块发布于 schema 定稿前，存在字段不完整的情况（主要是缺少 `purpose`）。

迁移原则：

- 不批量修改已有契约
- 新契约必须遵循本 schema
- 已有契约在下次修订时补齐字段
- Registry 仍以实际声明块内容为准

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始 schema，定义 Governance Contract 声明块标准字段 |
| v1.1 | 2026-07-21 | 增加 verification 块（required / method / evidence），为可验证治理预留入口 |
| v1.2 | 2026-07-21 | 增加 binding + enforcement 块（target / mode / mechanism），区分约束生效层与执行方式 |
