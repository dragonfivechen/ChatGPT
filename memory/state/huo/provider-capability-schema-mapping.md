# Schema ↔ Contract 字段映射表

**Phase 6.2.2 — 字段级追溯验证**
**Schema:** `provider-capability.schema.json`
**Contract:** `PROVIDER-CAPABILITY-CONTRACT.md` v1.0 FINAL

---

## 1. Contract Section → Schema Definition 覆盖

| Contract § | 内容 | Schema 覆盖 |
|:---|:---|:---|
| §0 | Scope | `$id`, `title`, `description` 头部定义；明确 "not routing/fallback/policy" |
| §1.1 | Capability Definition | `capabilityEntry.supported` — boolean，描述 "fact not preference" |
| §1.2 | Format definition | `capabilityEntry.format` — string，描述 "format changes ≠ capability changes" |
| §1.3 | Separation rule | `capabilityEntry` 中 `supported` 与 `format` 同层独立；conditional schema 在 `supported=false` 时强制 `format=null` |
| §2.1 | Evidence priority | `provenanceSource` enum 按信任度排列：runtime_verification > provider_adapter > runtime_detection > external_catalog > config_hint > unknown |
| §2.1 | Config is not fact | `config_hint` 的 description 注明 "Config is not fact — config is just a hint" |
| §2.2 | provenance vs evidence | `provenanceObject` (source+detail) 与 `evidenceObject` (type+value+timestamp) 分离定义 |
| §2.3 | Forbidden patterns | Schema 通过 `required: [supported, provenance, evidence]` 拒绝裸 `true` |
| §2.4 | Ownership change | Schema 不描述变更事件（Runtime 行为），但字段结构支持覆盖记录 |
| §3.1 | Schema semantics | 顶层 `capabilities` 对象枚举已知能力：thinking, tool_calls, reasoning_effort, temperature, streaming, vision；额外类 open via additionalProperties |
| §3.2 | Capability list | 预定义 6 个能力字段，每个映射到 `capabilityEntry` |
| §3.3 | Sub-capability (tool_calls) | `toolCallsSubCapability` definition + tool_calls 的 allOf 组合 |
| §3.4 | Schema boundary | description 注明不含 routing/fallback/cost/selection |
| §4.1 | evidence/provenance separation | 两个独立 definition 块，各自不同 required |
| §4.2 | evidenceType enum | 6 个类型枚举，按信任度排序 |
| §4.3 | evidence lifecycle | `evidenceObject.timestamp` 支持时间戳追踪 |
| §5 | Lifecycle | `lifecycleState` enum: unknown/detected/verified/deprecated；每个 capabilityEntry 可选包含 `state` |
| §6 | Conflict handling | Schema 不表达运行时冲突（JSON Schema 静态），但结构允许同一 capability 多来源并存 |
| §7 | Runtime boundary | Schema 定义只读结构（Registry 输出）；不定义写入权限（Runtime 行为） |
| §8 | ModelCompatConfig separation | Schema 仅包含能力字段；不包含 supportsUsageInStreaming、maxTokensField 等传输协议字段 |
| §9 | Registry relationship | `provider` + `models` 层级结构设计明确为 Registry v2 的前置定义 |
| §10 | Audit requirements | Schema 的结构可审计性：所有 provenance 和 evidence 必须存在，无例外 |

## 2. Capability 映射

| Capability | Config 来源 | Schema 字段 | Contract § |
|:---|:---|:---|:---:|
| thinking | `ModelDefinitionConfig.reasoning` + `compat.thinkingFormat` | `capabilities.thinking.supported` + `format` | §1, §3 |
| tool_calls | `compat.supportsTools` | `capabilities.tool_calls.supported` + `format` | §1, §3 |
| schema_validation | `compat.supportsStrictMode` | `capabilities.tool_calls.schema_validation.supported` + `format` | §3.3 |
| reasoning_effort | `compat.supportsReasoningEffort` | `capabilities.reasoning_effort.supported` | §1, §3 |
| temperature | 配置中未显式声明 | `capabilities.temperature.supported` | §3 |
| streaming | `compat.supportsUsageInStreaming` | `capabilities.streaming.supported` | §3 |
| vision | `ModelDefinitionConfig.input` | `capabilities.vision.supported` | §3 |

## 3. Provenance 映射

| provenanceSource | 对应场景 | Contract § | Schema 位置 |
|:---|:---|:---:|:---:|
| `runtime_verification` | API 响应中观测到能力证据 | §2.1 | `provenanceSource` enum |
| `provider_adapter` | 适配器代码声明 | §2.1 | `provenanceSource` enum |
| `runtime_detection` | 基于 baseUrl/API 签名的推断 | §2.1 | `provenanceSource` enum |
| `external_catalog` | OpenRouter 等外部能力目录 | §2.1 | `provenanceSource` enum |
| `config_hint` | 静态配置文件中的 hint | §2.1 | `provenanceSource` enum |
| `unknown` | 来源未知 | §2.1 | `provenanceSource` enum |

## 4. Evidence 映射

| evidenceType | 对应场景 | Contract § | Schema 位置 |
|:---|:---|:---:|:---:|
| `api_response_observation` | 直接观察到能力证据 | §4.2 | `evidenceType` enum |
| `api_error_pattern` | 错误模式推断 | §4.2 | `evidenceType` enum |
| `adapter_declaration` | 适配器代码声明 | §4.2 | `evidenceType` enum |
| `runtime_detection` | 运行时检测 | §4.2 | `evidenceType` enum |
| `openrouter_catalog` | OpenRouter 目录 | §4.2 | `evidenceType` enum |
| `static_config` | 静态配置 | §4.2 | `evidenceType` enum |

## 5. Lifecycle 映射

| lifecycleState | 含义 | Contract § | Schema 位置 |
|:---|:---|:---:|:---:|
| `unknown` | 未声明、未检测 | §5.1 | `lifecycleState` enum |
| `detected` | 已声明或检测 | §5.1 | `lifecycleState` enum |
| `verified` | 运行时验证通过 | §5.1 | `lifecycleState` enum |
| `deprecated` | 不再支持 | §5.1 | `lifecycleState` enum |

## 6. Schema 强制验证点

| 验证点 | Schema 实现 | Contract 来源 |
|:---|:---|:---:|
| 无 `provenance` → 拒绝 | `provenanceObject` 在 `required` | §2.3 "每项能力声明必须记录来源" |
| 无 `evidence` → 拒绝 | `evidenceObject` 在 `required` | §4.1 "evidence 与 provenance 职责分离" |
| `supported=false` 时 `format` 必须 null | conditional schema | §1.4 "不支持的能力 format 必须为 null" |
| 裸 `"thinking": true` → 拒绝 | `required: [supported, provenance, evidence]` | §2.3 "禁止隐藏推断" |
| 未知字段 → 拒绝 | `additionalProperties: false` 在每一层 | §3.4 "Schema 不包含 routing/fallback" |

## 7. 覆盖状态

| Contract § | 字段 | Schema 覆盖度 |
|:---|:---|:---:|
| §1.1 | supported | ✅ 完全覆盖 |
| §1.2 | format | ✅ 完全覆盖 |
| §1.3 | 分离规则 | ✅ conditional schema |
| §1.4 | null format | ✅ conditional schema |
| §2.1 | 证据优先级 | ✅ enum 排列 |
| §2.2 | provenance + evidence | ✅ 双对象 |
| §2.3 | 禁止隐藏推断 | ✅ required 约束 |
| §2.4 | 所有权变更 | ❌ 不覆盖（Runtime 行为） |
| §3.1 | 语义 Schema | ✅ 示例 + 约束 |
| §3.2 | 能力列表 | ✅ 6 个预定义 |
| §3.3 | tool_calls 子能力 | ✅ allOf 组合 |
| §3.4 | Schema 边界 | ✅ description 标注 |
| §4.1 | 职责分离 | ✅ 双对象定义 |
| §4.2 | evidenceType | ✅ 6 枚举 |
| §4.3 | evidence 生命周期 | ✅ timestamp 字段 |
| §5.1 | 生命周期状态 | ✅ 4 枚举 |
| §5.2 | 各状态定义 | ✅ description |
| §5.3 | 状态转换规则 | ❌ 不覆盖（Runtime 行为） |
| §5.4 | 禁止传递 | ✅ required 强制 |
| §6 | Conflict | ❌ 不覆盖（Runtime 行为） |
| §7 | Runtime Boundary | ❌ 不覆盖（Runtime 行为） |
| §8 | ModelCompatConfig | ✅ 不包含协议字段 |
| §9 | Registry 关系 | ✅ 层级结构设计 |
| §10 | Audit | ✅ 结构可审计 |

**覆盖统计:**
- ✅ 完全覆盖: 18/25
- ❌ Runtime 行为不覆盖: 7/25（所有权变更、状态转换、Conflict、Runtime Boundary、校验路径等，属于 Enforcement 层）
