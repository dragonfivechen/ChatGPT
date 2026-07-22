# System Asset Scan Schedule v1.1

> 资产扫描调度规则。
> 扫描频率与扫描深度独立——频率决定触发间隔，深度决定扫描范围。

---

## Design

```text
扫描频率              扫描深度
    ↓                    ↓
决定触发间隔            决定扫描范围
    ↓                    ↓
Light: 1d               path / file / service
Medium: 3d              module + semantic mapping
Full: 7d                all assets + classification + consistency + snapshot
```

执行日期是调度结果，不是规则定义。

例如：

```text
上一次 Medium: 周一
下一次 Medium: 周一 + 3d = 周四

上一次 Full: 周日
下一次 Full: 周日 + 7d = 周日
```

不是：

```text
星期一 = Medium ❌
星期三 = Medium ❌
星期日 = Full   ❌
```

## Levels

```yaml
light:
  interval: 1d
  scope:
    - path existence
    - file count change
    - service/timer count change
  output: ASSET_LIGHT_SCAN event

medium:
  interval: 3d
  scope:
    - module_mapping
    - semantic_mapping
    - file mapping completeness
  output: ASSET_MEDIUM_SCAN event

full:
  interval: 7d
  scope:
    - all assets
    - classification (7 categories)
    - consistency check
    - snapshot baseline
  output: ASSET_SNAPSHOT event
```

## Implementation

```text
scripts/asset_observer.py --mode light     # interval: 1d
scripts/asset_observer.py --mode medium    # interval: 3d
scripts/asset_observer.py --mode full      # interval: 7d
```

实际调度由外部 cron / systemd timer 实现，依据 last_run + interval 判断是否触发。

## Version

| Version | Date | Change |
|:--------|:----:|:-------|
| v1.0 | 2026-07-22 | Initial — 按星期绑定深度（设计耦合，已废弃） |
| v1.1 | 2026-07-22 | 解耦：频率独立于深度，interval 驱动触发 |
