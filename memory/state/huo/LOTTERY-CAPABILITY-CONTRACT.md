# Lottery Capability Contract v1.0

**Phase: Capability Definition — 非源码改动**
**Date:** 2026-07-17

---

## 前置说明

Lottery System 是 External Worker，不是 Plugin。因此：

- 使用 `worker` 声明代替 `plugin` 声明
- Capability category 映射到现有 7 个语义分类，不新增 `external` 分类
- 三条铁律（Escalation / Hidden / Transitive Leak）继承适用

---

## Section 1: Capability Identity

```yaml
capability:

  id: lottery.collect

  category: io

  description:
    从指定开奖数据源采集彩票开奖信息，
    不负责判断结果真实性，不修改事件历史。

  risk_level: low

  depends_on:
    - io.fetch

  exposed_api:
    lottery.collect()
```

```yaml
capability:

  id: lottery.validate

  category: event

  description:
    对开奖数据执行格式、完整性、
    时间顺序及重复事件校验。

  risk_level: medium

  depends_on:
    - event.append

  exposed_api:
    lottery.validate()
```

```yaml
capability:

  id: lottery.analyze

  category: provider

  description:
    对已确认开奖事件进行统计分析，
    只读取历史事件，不产生事实事件。

  risk_level: low

  depends_on:
    - event.read

  exposed_api:
    lottery.analyze()
```

```yaml
capability:

  id: lottery.report

  category: notification

  description:
    根据分析结果生成开奖报告。

  risk_level: low

  depends_on:
    - lottery.analyze

  exposed_api:
    lottery.report()
```

```yaml
capability:

  id: lottery.notify

  category: notification

  description:
    将开奖报告发送到已授权通知渠道。

  risk_level: medium

  depends_on:
    - notification.send

  exposed_api:
    lottery.notify()
```

---

## Section 2: Capability Registry Entry

```yaml
registry:

  lottery.collect:
    owner: lottery-worker
    category: io
    risk_level: low
    writer: lottery-worker
    state_mutation: false

  lottery.validate:
    owner: lottery-worker
    category: event
    risk_level: medium
    writer: validator
    state_mutation: true

  lottery.analyze:
    owner: lottery-worker
    category: provider
    risk_level: low
    writer: none
    state_mutation: false

  lottery.report:
    owner: lottery-worker
    category: notification
    risk_level: low
    writer: reporter
    state_mutation: false

  lottery.notify:
    owner: lottery-worker
    category: notification
    risk_level: medium
    writer: notifier
    state_mutation: false
```

---

## Section 3: Worker Declaration

```yaml
worker:

  id: lottery-worker

  type:
    external_worker

  declare:

    capabilities:
      - lottery.collect
      - lottery.validate
      - lottery.analyze
      - lottery.report
      - lottery.notify

  deny:
    - lottery.predict
    - lottery.auto_bet
    - event.modify
    - event.delete
```

---

## Section 4: 三条铁律

### 4.1 Capability Escalation

禁止 lottery-worker 在运行期间自行获取未声明的能力。

能力变化必须经过：修改 Contract → Registry 审核 → 重新部署。

### 4.2 Hidden Capability

禁止声明 `lottery.collect` 但实际调用 `notification.send` 或 `event.modify`。

所有运行时 API 调用必须在 `declare.capabilities` 中显式列出。

### 4.3 Capability Transitive Leak

禁止 `lottery.analyze` 隐式获得 `lottery.notify`。

依赖关系不自动扩展为权限继承。

---

## Section 5: Trust Boundary

```yaml
trust_boundary:

  source:
    official_lottery_data

  producer:
    lottery-worker

  validator:
    deterministic_validator

  authority:
    event_store
```

规则：

- Worker 提交观察结果
- Validator 判断格式合法
- Event Store 保存事实
- 分析模块只能消费事实，不产生事实

---

## 冻结范围

### 包含

- 数据采集
- 数据验证
- 历史统计
- 报告生成
- 通知推送

### 明确排除

- 预测能力
- 选号建议作为系统决策
- 自动购买
- 资金相关能力
