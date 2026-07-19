# Credential Access Contract v1.0

**Origin:** Audit credential boundary — 10-round integrity audit (2026-07-20)
**Date:** 2026-07-20
**Status:** 🔒 FROZEN

---

## 1. 目的

定义 Git push 操作所需的 credential 访问规则，防止 token 泄露、越权使用、输出污染。

本 Contract 不管理 credential 的存储和生成，只定义运行时的使用边界。

---

## 2. Credential 位置

只定义引用路径，不保存实际值。

```text
Credential Ref:
.secrets/push-gate.json.github_token
```

**禁止：**

- token 实际值进入 `memory/` 任何 namespace
- token 进入 git commit message / log / event
- token 出现在 audit report 输出
- token 被写入 `runtime/` 上下文

---

## 3. Scope Boundary

```yaml
allowed:
  repository: dragonfivechen/ChatGPT
  operation: git push
  auth_mode: https + PAT

forbidden:
  - git clone private repo
  - account administration
  - organization access
  - cross-repository access
```

---

## 4. Output Safety

强制规则：

| 禁止 | 原因 |
|------|------|
| `echo $TOKEN` | stdout 泄露 |
| `print(token)` | 程序输出泄露 |
| debug dump environment | env 含 credential |
| `git remote -v` with embedded token | git config 残留 |
| trace / debug log 含 token | 日志文件泄露 |

---

## 5. Runtime Usage Flow

```
read credential from .secrets/push-gate.json
         ↓
construct temporary https URL: https://user:token@github.com/...
         ↓
git push
         ↓
restore clean remote URL: https://github.com/...
         ↓
verify: git remote -v (no token residue)
```

验证：

```bash
git remote -v
# origin  https://github.com/dragonfivechen/ChatGPT.git (fetch)
# origin  https://github.com/dragonfivechen/ChatGPT.git (push)
# 不含 token
```

---

## 6. Permission Requirement

```yaml
secrets_directory: .secrets/
owner:            runtime user (dragonfive)
mode:             600 (-rw-------)
group:            none
encryption:       none (filesystem permission only)
```

---

## 7. Audit Evidence

每次 credential 使用后需确认：

```text
PASS:
  - remote URL clean
  - .secrets permission 600
  - git config no residue
  - shell history no token echo
```

**不保留** token 值、不记录 credential 内容、不写入 event log。

---

## 8. Violation Handling

| Violation | Action |
|-----------|--------|
| token 出现在 stdout | 立即撤销 token，报告 |
| token 写入 git history | force push 清除，撤销 token |
| token 写入 event / log | 清除日志记录，撤销 token |
| token 越权操作 | 撤销 token，审计操作范围 |

---

## 9. Credential Lifecycle

### Validity

Credential 有效性不是永恒状态。使用前需确认：

```text
- credential exists
- scope matches target repository
- operation is git push only
```

### Failure Classification

`push failed` 不一定是网络错误。按类型区分：

```text
Authentication Failure
  ├── token missing / empty
  ├── token expired
  ├── token revoked
  ├── permission denied
  └── scope mismatch
```

### Rotation Rule

```text
credential invalid
     ↓
replace in .secrets/push-gate.json
     ↓
retry push
     ↓
cleanup residue
     ↓
verify remote clean
```

不追溯、不回滚、不修改已推送的 commit。

---

## 10. Contract Evolution

```text
Baseline: v1.0 (2026-07-20)
🔒 FROZEN

Extension requires:
- 新的 credential 类型
- 新的目标 repository
- 新的操作类型（非 git push）

All:
→ Evidence-driven
→ Versioned
→ Audited
```
