# 模型边界迁移闸门

## 目录结构

```
candidates/
├── tg/          ← 烬🔥实验数据暂存区
├── approved/    ← 审核通过，燃🔥可安全读取
└── archive/     ← 已处理的历史候选
```

## 迁移规则

1. 烬🔥实验数据 → 写入 `candidates/tg/`
2. 审核通过 → `promote.py candidate -> approved`
3. 燃🔥只读取 `candidates/approved/`
4. 禁止直接写入 `memory/events/huo/` 或 `memory/state/huo/`

## 闸门条件

候选需满足以下条件才能被 promote：
- 来源标记为 jin/experiment
- 内容不引用 terminal 机密
- 明确标记 `data_class: experiment`
