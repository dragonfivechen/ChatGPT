# Plugin Capability Contract v1.0

**Phase 3.2 — 架构规范，非源码改动**
**Date:** 2026-07-17

---

## 基线事实

OpenClaw Plugin API 经源码审计确认：

- 暴露 50+ registerXxx 函数
- 能力覆盖完整（runtime / memory / event / io / notification / provider / security）
- 缺少能力声明/权限分级层
- 当前只有二元权限：插件启用/禁用（allowlist）
- 无细粒度 "此插件可 registerTool 但不可 registerChannel" 机制

---

## Section 1: Capability Classification

基于审计结果，定义能力命名空间：

```yaml
runtime:
  - tool.register          # 注册 Agent 工具
  - hook.subscribe         # 订阅生命周期事件
  - http.route             # 暴露 HTTP 端点
  - service.register       # 注册长驻服务
  - session.manage         # Session 管理
  - context.engine         # 上下文构建
  - lifecycle.hook         # Runtime 启动/停止

memory:
  - memory.read            # 搜索/读取记忆
  - memory.prompt.inject   # 注入记忆到 prompt
  - memory.provider        # 注册 memory 提供者
  - memory.corpus          # 补充外部语料

event:
  - event.subscribe        # 订阅事件
  - event.emit             # 发射事件

io:
  - web.fetch              # 网页抓取
  - web.search             # 网络搜索
  - media.resolve          # 媒体解析

notification:
  - channel.register       # 注册通信通道

provider:
  - model.provider         # AI 模型提供商
  - speech.provider        # 语音合成/识别
  - media.generation       # 图像/视频/音频生成

security:
  - audit.collector        # 安全审计收集
  - tool.policy            # 工具执行策略
```

### 规则

- Capability 是能力命名空间，不是 API 函数
- API 函数是 Capability 的当前实现映射
- Capability 保持稳定，API 函数可随版本变化
- 新增 Capability 必须先注册到分类

---

## Section 2: Capability Declaration

Plugin 必须显式声明所需能力：

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
    - memory.*           # 拒绝所有 memory 能力
    - io.*               # 拒绝所有 IO 能力
```

### 规则

- 默认策略：**deny by default**（插件仅获得声明的能力）
- 声明 `*` 通配符表示分类下所有能力（如 `runtime.*`）
- 声明 `deny` 列表显式拒绝某些能力
- 未声明 = 未申请 = 无权限

---

## Section 3: Capability Review & Grant

### 三层模型

```text
Plugin Identity
        ↓
Capability Declaration
        ↓
Activation Allowlist  (binary: 插件允许/禁止  ← 现有机制)
        ↓
Capability Grant      (granular: 能力允许/禁止  ← 新增治理层)
        ↓
Runtime Enforcement
```

### 现有机制对接

当前的 `allowlistPluginIds` 机制保留，定位调整为：

```
Allowlist        → 激活层（"哪个插件可以运行"）
Capability Grant → 能力层（"运行的插件能做什么"）
```

两者职责分离，不可相互替代。

---

## Section 4: Three Forbidden Rules

### 4.1 Capability Escalation

禁止插件在运行期间自行获取未声明的能力。

```
Plugin A
    ↓
声明: runtime.tool.register
    ↓
运行时: 尝试 registerChannel
    ↓
❌ 禁止
```

### 4.2 Hidden Capability

禁止插件调用未在 Capability Declaration 中声明的 API。

```
Plugin
    ↓
未声明: runtime.service.register
    ↓
调用: api.registerService(...)
    ↓
❌ 运行时拒绝
```

### 4.3 Capability Transitive Leak

禁止插件的未声明能力通过子插件或依赖隐式继承。

```
Plugin A
    ↓ 声明: runtime.tool.register
    ↓
Plugin B (A 的依赖)
    ↓ 隐式获得: runtime.service.register
    ↓
❌ 禁止隐式继承
```

---

## Section 5: Future Enforcement Design Rules

Phase 3.4（Runtime Enforcement Design）的约束前提：

- Enforcement 不应修改 Plugin API 的接口签名
- Enforcement 应位于 Plugin API 实现层（handler 注册时检查）
- 违反 Capability 声明的调用应被静默拒绝 + 写入 event 日志
- 任何 Capability 的授予 / 拒绝都必须可审计

---

## 附录: Current Allowlist vs Capability Grant

| 维度 | Activation Allowlist | Capability Grant |
|------|---------------------|------------------|
| 控制层面 | 插件能否激活 | 插件能做什么 |
| 粒度 | 二元（允许/禁止） | 分级（per-capability） |
| 决策时机 | 安装/配置时 | 声明 + 审查时 |
| 现有状态 | ✅ 源码已有 | ❌ 需补充 |
