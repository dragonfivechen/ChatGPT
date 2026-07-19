# Capability Registry Model v1.0

**Phase 3.3 — 架构规范，非源码改动**
**Date:** 2026-07-17

---

## 定位

Capability Registry 是 Plugin Capability 的目录模型。

Phase 3.2 定义了 "Capability 是什么"。
Phase 3.3 定义 "Capability 存在哪里、如何描述"。

不涉及 Runtime Enforcement（Phase 3.4）。

---

## Section 1: Capability Identity

基于 Phase 3.1 审计 + Phase 3.2 Contract 冻结的能力命名空间：

```yaml
runtime:
  - tool.register
  - hook.subscribe
  - http.route
  - service.register
  - lifecycle.hook
  - compaction.provider

memory:
  - memory.read
  - memory.prompt.inject
  - memory.provider
  - memory.write

event:
  - event.subscribe
  - event.emit
  - event.append
  - event.read

io:
  - web.fetch
  - web.search
  - media.resolve

notification:
  - channel.register

provider:
  - model.provider
  - speech.provider
  - media.generation

security:
  - audit.collector
  - tool.policy
```

### 命名规则

- 格式：`<category>.<name>`
- 全小写，句点分隔
- 不允许通配符在注册表中存在（但声明时可用 `category.*`）
- 新能力加入 Registry 时必须指定 category

---

## Section 2: Capability Metadata

每个注册表条目包含：

```yaml
capability:
  id:               # 能力标识，如 "runtime.tool.register"
  category:         # 所属分类：runtime | memory | event | io | notification | provider | security
  description:      # 能力说明
  risk_level:       # low | medium | high
  depends_on:       # 依赖的能力列表（可选）
  exposed_api:      # 当前对应的 Plugin API 函数
```

### 完整 Registry 表

```yaml
registry:
  - id: runtime.tool.register
    category: runtime
    description: 向 Agent 注册自定义工具
    risk_level: high
    depends_on: []
    exposed_api: registerTool()

  - id: runtime.hook.subscribe
    category: runtime
    description: 订阅 Agent 生命周期事件
    risk_level: medium
    depends_on: []
    exposed_api: registerHook()

  - id: runtime.http.route
    category: runtime
    description: 暴露 HTTP 端点
    risk_level: high
    depends_on: [runtime.service.register]
    exposed_api: registerHttpRoute()

  - id: runtime.service.register
    category: runtime
    description: 注册长驻 Gateway 服务
    risk_level: high
    depends_on: [runtime.lifecycle.hook]
    exposed_api: registerService()

  - id: runtime.lifecycle.hook
    category: runtime
    description: 订阅 Runtime 启动/停止事件
    risk_level: medium
    depends_on: []
    exposed_api: registerRuntimeLifecycle()

  - id: memory.read
    category: memory
    description: 搜索和读取 Memory 记录
    risk_level: low
    depends_on: []
    exposed_api: registerTool()  # memory_search/memory_get

  - id: memory.prompt.inject
    category: memory
    description: 注入记忆内容到 Agent prompt
    risk_level: medium
    depends_on: []
    exposed_api: registerMemoryPromptSection()

  - id: memory.provider
    category: memory
    description: 注册自定义 Memory 提供者
    risk_level: medium
    depends_on: [memory.read]
    exposed_api: registerMemoryRuntime()

  - id: event.subscribe
    category: event
    description: 订阅系统事件
    risk_level: low
    depends_on: []
    exposed_api: registerAgentEventSubscription()

  - id: event.emit
    category: event
    description: 发射系统事件
    risk_level: low
    depends_on: []
    exposed_api: emitAgentEvent()

  - id: io.web.fetch
    category: io
    description: 抓取网页内容
    risk_level: low
    depends_on: []
    exposed_api: registerWebFetchProvider()

  - id: io.web.search
    category: io
    description: 执行网络搜索
    risk_level: low
    depends_on: []
    exposed_api: registerWebSearchProvider()

  - id: io.media.resolve
    category: io
    description: 媒体地址解析
    risk_level: low
    depends_on: []
    exposed_api: registerHostedMediaResolver()

  - id: notification.channel.register
    category: notification
    description: 注册通信通道（Telegram 等）
    risk_level: high
    depends_on: [runtime.service.register]
    exposed_api: registerChannel()

  - id: provider.model
    category: provider
    description: 注册 AI 模型提供商
    risk_level: medium
    depends_on: []
    exposed_api: registerProvider()

  - id: provider.speech
    category: provider
    description: 注册语音合成/识别提供商
    risk_level: medium
    depends_on: []
    exposed_api: registerSpeechProvider()

  - id: provider.media.generation
    category: provider
    description: 注册图像/视频/音频生成提供商
    risk_level: medium
    depends_on: []
    exposed_api: registerImageGenerationProvider()

  - id: security.audit.collector
    category: security
    description: 注册安全审计收集器
    risk_level: high
    depends_on: [event.subscribe]
    exposed_api: registerSecurityAuditCollector()

  - id: security.tool.policy
    category: security
    description: 注册工具执行策略
    risk_level: high
    depends_on: [runtime.tool.register]
    exposed_api: registerTrustedToolPolicy()
```

  - id: event.append
    category: event
    description: 向事件日志追加只读事件记录
    risk_level: medium
    depends_on: []
    exposed_api: appendEvent()

  - id: event.read
    category: event
    description: 读取事件日志
    risk_level: low
    depends_on: []
    exposed_api: readEvent()

  - id: lottery.collect
    category: io
    description: 从指定开奖数据源采集开奖信息
    risk_level: low
    depends_on: [io.web.fetch]
    exposed_api: lottery.collect()

  - id: lottery.validate
    category: event
    description: 对开奖数据执行格式、完整性、时间及重复校验
    risk_level: medium
    depends_on: [event.append]
    exposed_api: lottery.validate()

  - id: lottery.analyze
    category: provider
    description: 对已确认开奖事件进行统计分析
    risk_level: low
    depends_on: [event.read]
    exposed_api: lottery.analyze()

  - id: lottery.report
    category: notification
    description: 根据分析结果生成开奖报告
    risk_level: low
    depends_on: [lottery.analyze]
    exposed_api: lottery.report()

  - id: lottery.statistics
    category: io
    description: 基于事件事实的描述性统计（频率/奇偶/区间/和值）
    risk_level: low
    depends_on: [event.read]
    produces: [cache/lottery/statistics/*]
    exposed_api: lottery.statistics()

  - id: lottery.check
    category: io
    description: 预测号码 vs 真实开奖事件比对，输出命中统计
    risk_level: low
    depends_on: [event.read]
    produces: [cache/lottery/check/*]
    exposed_api: lottery.check()

  - id: lottery.notify
    category: notification
    description: 将开奖报告发送到已授权通知渠道
    risk_level: medium
    depends_on: [notification.channel.register]
    exposed_api: lottery.notify()

  - id: memory.write
    category: memory
    description: 按 Memory Ownership 契约将数据持久化写入指定 namespace
    risk_level: high
    depends_on: [memory.read]
    exposed_api: n/a (系统内部能力，非 Plugin API)

  - id: compaction.provider
    category: runtime
    description: Session Transcript Compaction — 控制 transcript/trajectory 增长
    risk_level: high
    depends_on: [runtime.lifecycle.hook]
    exposed_api: registerCompactionProvider()

---

## Section 3: Plugin Declaration

插件声明其所需能力的格式：

```yaml
plugin:
  id: example-plugin
  name: Example Plugin
  version: 1.0.0

declare:
  capabilities:
    - runtime.tool.register
    - event.subscribe

  deny:
    - memory.*
    - io.*
```

### 声明规则

- `capabilities` 列表：显式声明需要的能力
- `deny` 列表：显式拒绝的能力（防止误授予）
- 支持 `category.*` 通配符声明所有子能力
- 未声明的能力 = 未申请 = 运行时拒绝

---

## Section 4: Capability Dependency

### 依赖规则

- 当 Plugin 声明能力 A，若 A 有 `depends_on`，系统自动要求 A 的依赖也授予
- Plugin 不需显式声明 `depends_on` 中的能力（自动展开）
- 如果 Plugin 声明 A 但拒绝 A 的依赖，声明无效

### 示例

Plugin 声明 `notification.channel.register`：

```
声明: notification.channel.register
       ↓
自动展开依赖:
  runtime.service.register
       ↓
  runtime.lifecycle.hook
       ↓
最终授予:
  - notification.channel.register
  - runtime.service.register
  - runtime.lifecycle.hook
```

### 隔离规则

依赖自动展开不违反 Phase 3.2 的 "Capability Transitive Leak" 禁止规则，原因：
- 依赖展开是 Capability Grant 阶段的静态检查
- 不是运行时的隐式继承
- 展开结果在 Grant 时即固定，不可运行时扩展

---

## Section 5: Risk Level Policy

| Risk Level | 审查要求 | 示例 |
|------------|---------|------|
| low | 自动批准 | memory.read, event.subscribe |
| medium | 需配置确认 | runtime.hook.subscribe, memory.prompt.inject |
| high | 显式批准，建议人工审查 | runtime.tool.register, notification.channel.register |

---

## 附录: Capability Identity vs API Function

Capability 是稳定标识，API 是当前实现。以下映射表只为追踪，不为约束：

| Capability | 当前 API | 可能的未来 API |
|-----------|---------|---------------|
| runtime.tool.register | registerTool() | registerAgentTool() / registerExternalTool() |
| notification.channel.register | registerChannel() | registerChannelProvider() |
| memory.read | memory_search / memory_get tools | searchMemory() API |
