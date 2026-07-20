# 数据契约 — 市场筛选系统

> 定义各层和各数据源的输入输出结构，保证单向依赖。
> 所有新增数据源必须先定义契约，再实现采集。

---

## 已有数据源

### L0 Scan (`l0_scan.json`)
**职责：** 保存市场原始事实，不做判断。
**来源：** East Money clist 接口

```json
{
  "version": 1,
  "pool_stage": "scan",
  "generated_at": "2026-07-20T12:10:18+08:00",
  "total": 200,
  "description": "L0 Scan: 原始行情事实，不做判断",
  "symbols": ["300317", "300040", ...],
  "details": [
    {
      "symbol": "300317",
      "name": "珈伟新能",
      "metrics": {
        "amount": 696257258.81,
        "change_pct": 10.17,
        "volume": 1619812,
        "turnover_pct": 19.54,
        "vol_ratio": 5.36,
        "amplitude_pct": 18.4,
        "momentum_20d_pct": 30.0,
        "capital_flow": 15999391.0,
        "total_market_cap": 3777357243,
        "industry": "电力"
      },
      "discovery_tags": ["amount", "gainers", "turnover", "amplitude", "momentum_20d"]
    }
  ]
}
```

**消费方：** L1 Admission, L2 Scoring (趋势/成交/波动因子)

---

### L1 Admission Pool (`admission_pool.json`)
**职责：** 基础规则判断 + 过滤证据。
**来源：** L0 → admission filter

```json
{
  "version": 1,
  "pool_stage": "admission",
  "generated_at": "2026-07-20T12:10:18+08:00",
  "source_snapshot": "l0_scan_20260720_121018",
  "admitted_count": 114,
  "rejected_count": 86,
  "total_candidates": 200,
  "trace_start": "300317-20260720-001",
  "trace_end": "603501-20260720-114",
  "symbols": ["300317", ...],
  "details": [
    {
      "symbol": "300317",
      "name": "珈伟新能",
      "pool_stage": "admission",
      "trace_id": "300317-20260720-001",
      "admitted": true,
      "filters": {
        "liquidity":  {"passed": true, "tag": "liquidity_ok"},
        "trend":      {"passed": true, "tag": "trend_uptrend"},
        "volatility": {"passed": true, "tag": "volatility_good"},
        "spike":      {"passed": true, "tag": "no_spike"}
      },
      "admission_reasons": ["liquidity_ok", "trend_uptrend", "volatility_good", "no_spike"],
      "discovery_tags": ["amount", "gainers", "turnover", "amplitude", "momentum_20d"]
    }
  ]
}
```

**消费方：** L2 Scoring（指定要评分的标的）

---

## 新增数据源契约

### Kline Snapshot (`kline_snapshot.json`)
**职责：** 提供日 K 线事实，用于 L2 趋势质量和价格结构计算。
**消费方：** L2 Scoring
**覆盖范围：** L1 Admission Pool 全量股票
**周期：** L1 生成后立即采集，每日最多 1 次

```json
{
  "version": 1,
  "pool_stage": "kline",
  "generated_at": "2026-07-20T12:12:00+08:00",
  "source_snapshot": "l0_scan_20260720_121018",
  "description": "K线事实：日线 OHLCV 用于 L2 评分因子计算",
  "symbol_count": 114,
  "symbols": ["300317", ...],
  "bar_count": 20,
  "details": [
    {
      "symbol": "300317",
      "name": "珈伟新能",
      "bars": [
        {"date": "2026-07-20", "open": 12.00, "high": 12.50, "low": 11.90, "close": 12.35, "volume": 1619812, "amount": 696257258.81},
        {"date": "2026-07-17", "open": 11.50, "high": 11.80, "low": 11.20, "close": 11.30, "volume": 1200000, "amount": 500000000},
        ...
      ],
      "ma5": 12.10,
      "ma20": 11.80,
      "high_20d": 12.50,
      "low_20d": 10.80,
      "amplitude_avg_20d": 4.2
    }
  ]
}
```

**因子用途：**
| 因子 | 分项 | 依赖字段 |
|------|------|---------|
| 趋势质量 | 均线多头 10分 | ma5, ma20 |
| 趋势质量 | 价格位置 7分 | close, high_20d, low_20d |
| 价格结构 | 突破状态 8分 | close, high_20d |
| 价格结构 | K线结构 7分 | open, high, low, close |
| 波动质量 | 波动稳定性 7分 | amplitude_avg_20d |

**实现方案：** East Money push2his kline API，单股逐次请求。

---

### Flow Snapshot (`flow_snapshot.json`)
**职责：** 提供资金流向事实，用于 L2 资金质量评分。
**消费方：** L2 Scoring
**覆盖范围：** L1 Admission Pool 全量股票
**周期：** L1 生成后立即采集，每日最多 1 次

```json
{
  "version": 1,
  "pool_stage": "flow",
  "generated_at": "2026-07-20T12:13:00+08:00",
  "source_snapshot": "l0_scan_20260720_121018",
  "description": "资金流事实：主力/散户资金流向用于 L2 评分因子",
  "symbol_count": 114,
  "symbols": ["300317", ...],
  "details": [
    {
      "symbol": "300317",
      "name": "珈伟新能",
      "main_net_inflow": 15999391.0,
      "flow_ratio": 2.3,
      "retail_net_inflow": -3200000.0,
      "main_inflow_days": 3
    }
  ]
}
```

**因子用途：**
| 因子 | 分项 | 依赖字段 |
|------|------|---------|
| 资金质量 | 资金方向 10分 | main_net_inflow |
| 资金质量 | 资金占比 7分 | flow_ratio (main_net_inflow / amount) |
| 资金质量 | 持续性 8分 | main_inflow_days |

**实现方案：** East Money push2 个股资金流 API，单股逐次请求。

---

## 数据流转关系

```
L0 Scan (clist)
 ├──→ L1 Admission (规则过滤)
 ├──→ L2 Scoring (趋势/成交/波动因子)
 │
Kline API (push2his)
 └──→ L2 Scoring (趋势MA/价格结构因子)
 │
Flow API (push2)
 └──→ L2 Scoring (资金质量因子)
 │
 ┌─────────────────────┐
 │ L2 Scoring Pool     │  ← 消费 L0 + Kline + Flow
 │   factors + score   │     不产生原始事实
 └─────────┬───────────┘
           ↓ score DESC
L3 Candidate Pool (容量截断)
```

**约束：**
- L2 消费已有事实，不自己产生事实
- Kline/Flow 不依赖对方
- L3 只排序截断，不改评分
- Kline/Flow 覆盖范围 = L1 通过股票，不独立扩展
