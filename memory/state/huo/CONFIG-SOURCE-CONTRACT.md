# CONFIG-SOURCE-CONTRACT.md — Config Truth Source v1.0

> 建立于 2026-07-20，属于 Truth Architecture Phase B。
> 此契约定义配置域的唯一事实源和消费规则。

---

## 1. Authority

```
config_source:
  authority: defined_config_registry
  mode: versioned
  state: 🟡 Contract Design
  interface: TBD (tools/config_source.py)
```

配置事实源由框架 Config Registry 承载，所有运行态配置必须源自此注册中心。

禁止运行组件自行拼接、覆盖、或推理配置状态。

## 2. Properties

| 属性 | 约束 |
|:---|---:|
| Versioned | 每个配置项关联版本号或修改时间戳 |
| Traceable | 可追溯到修改来源和时间 |
| Immutable history | 历史版本可查询，不删除变更记录 |
| Authoritative | 框架 Config Registry 是唯一权威来源 |

## 3. Known Risks

当前配置来源可能分散于多处：

| 来源 | 风险 |
|:---|---:|
| OpenClaw config files (`config.yaml`) | 框架内建，权威 |
| 环境变量 | 运行时覆盖，无版本记录 |
| systemd 参数 | 启动时注入，查询困难 |
| 脚本默认值 (`DEFAULT_*` 常量) | 硬编码，不追踪 |
| service 文件 | 间接影响配置，无审计 |

**问题不是"没有配置"，而是：**
- 哪个优先？
- 哪个生效？
- 当前运行状态对应哪个版本？

## 4. Consumer Rules

### 4.1 禁止

Consumers **不得**：

```
自行拼接配置来源（部分读文件、部分读环境变量、部分硬编码）
运行时直接改写配置副本绕过版本记录
```

### 4.2 必须

通过 `tools/config_source.py` 获取配置：

```
Config Registry
 ↓
Config Reader (config_source.py)
 ↓
Consumer
```

### 4.3 允许

通过 Config Reader 进行以下操作：
- **获取当前有效配置** — `get_config()`
- **查询指定版本** — `get_config(version)`
- **查询配置来源** — `get_source()`
- **获取版本信息** — `get_version()`

## 5. Config Reader API (契约，待实现)

### 5.1 接口

```python
get_config(
    key: str | None = None,       # 配置键路径，None = 全量
    version: str | None = None,    # 指定版本，None = 当前
) -> ConfigResult

get_version(key: str) -> VersionInfo

get_source(key: str) -> SourceInfo
```

### 5.2 返回结构

```python
# ConfigResult
{
    "key":       "providers.ollama.apiKey",
    "value":     "...",
    "version":   "v2026-07-20.1",
    "source":    "gateway/config.yaml",
    "updated_at": "2026-07-20T12:00:00+08:00",
}

# VersionInfo
{
    "key":       "providers.ollama.apiKey",
    "current_version": "v2026-07-20.1",
    "versions": ["v2026-07-19.1", "v2026-07-20.1"],
}

# SourceInfo
{
    "key":       "providers.ollama.apiKey",
    "primary_source": "gateway/config.yaml",
    "overrides": [],
    "resolved":  "gateway/config.yaml",
}
```

### 5.3 不负责

Config Reader 不做以下事情：
- **修改配置** — 不写入
- **自动同步** — 不检测外部变更
- **热更新** — 不触发重新加载
- **校验** — 不验证配置有效性

## 6. 版本规则

### 6.1 版本来源

配置版本从以下来源派生（优先级从高到低）：

1. Config Registry 自身版本（如 schema 版本号）
2. 文件修改时间（mtime）
3. 配置项变更记录（events 中的配置修改事件）

### 6.2 版本字符串格式

```
v{date}.{seq}
# 示例：v2026-07-20.1
```

## 7. 验收标准

| 标准 | 状态 |
|:---|---:|
| ✅ get_config 返回唯一权威配置 | ❌ 待验证 |
| ✅ 消费者不再自行拼接配置 | ❌ 待验证 |
| ✅ 配置来源可追溯 | ❌ 待验证 |
| ✅ 运行状态可关联到配置版本 | ❌ 待验证 |
| ✅ 不修改配置、不热更新 | ✅ 无障碍 |

## 8. 版本记录

| 版本 | 日期 | 变更 |
|:---|---:|:---|
| v1.0 | 2026-07-20 | 初始契约。建立 Config Truth Source 边界定义。 |

| v1.0-audit-1 | 2026-07-20 | Reader 实现完成（config_source.py）。验证通过。 |
