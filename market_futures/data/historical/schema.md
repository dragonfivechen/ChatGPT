# Historical Data Schema v1.0

> Futures-Sim 外部历史行情 CSV 格式规范。
> 符合此规范的数据文件可直接被 `replay/loader.py` 加载，经 `replay/converter.py` 转换为 FUTURES_QUOTE 事件。

---

## 文件格式

- **编码:** UTF-8
- **换行:** LF
- **表头:** 首行必须包含列名
- **分隔符:** 逗号 `,`

## 列定义

| 列名 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `datetime` | string | ✅ | 时间戳，格式 `YYYY-MM-DD HH:mm:ss` 或 ISO-8601 |
| `symbol` | string | ✅ | 品种代码，大写。支持值见下方列表 |
| `open` | float | ✅ | 开盘价 |
| `high` | float | ✅ | 最高价 |
| `low` | float | ✅ | 最低价 |
| `close` | float | ✅ | 收盘价/最新价 |
| `volume` | int | ✅ | 成交量（张/手） |
| `oi` | int | ✅ | 持仓量（open interest） |

## 数据类型约束

- `open`/`high`/`low`/`close` > 0
- `high` >= `low`
- `volume` >= 0
- `oi` >= 0
- `symbol` 必须为受支持的品种代码

## 受支持的品种代码

取自 `futures_contracts.json`（15 个品种）：

```
RB — 螺纹钢
CU — 沪铜
AL — 沪铝
ZN — 沪锌
AU — 沪金
AG — 沪银
I  — 铁矿石
JM — 焦煤
J  — 焦炭
SC — 原油
FU — 燃料油
RU — 橡胶
TA — PTA
MA — 甲醇
PP — 聚丙烯
```

## 示例行

```
datetime,symbol,open,high,low,close,volume,oi
2026-01-06 09:00:00,RB,3300,3310,3295,3305,12500,100000
2026-01-06 09:05:00,RB,3305,3312,3300,3308,13200,100150
```

## 周期说明

当前 schema 不限制 K 线周期。

| 周期 | 说明 |
|------|------|
| 日线 | 最易获取，适合长时间跨度的策略稳定性验证 |
| 小时线 | 需部分付费数据源 |
| 分钟线 | 国内免费来源有限，需 Tushare Pro 等付费服务 |

建议从日线开始验证策略稳定性（Phase 6 Walk Forward 等）。

## 多品种文件

单个 CSV 可以包含多个品种，按 `symbol` 和 `datetime` 混合排列即可。
`loader.py` 支持通过 `symbols` 参数按品种过滤。

## 时间戳说明

- 北京时间（UTC+8）
- 日线数据：`datetime` 为交易日日期，格式 `YYYY-MM-DD` 即可
- 分钟线数据：`datetime` 格式 `YYYY-MM-DD HH:mm:ss`

## 加载验证

```bash
cd market_futures
python3 replay/loader.py data/historical/<your_file>.csv
```

成功输出样例：
```
[loader] ✅ 加载完成: 490 行 (总扫描 490 行)
```

---

*版本: v1.0 | 关联: Futures-Sim v0.1 Frozen Baseline | replay/loader.py*
