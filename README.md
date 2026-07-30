# Duke Doc Skills

面向中文产品需求工作的 Codex Skill 集合，采用“专业 Skill＋编排 Skill”结构。

## Skills

| Skill | 用途 |
| --- | --- |
| `duke-doc` | 编排多阶段需求流程并选择交付深度 |
| `duke-interview-requirement` | 将模糊需求收敛为结构化需求包 |
| `duke-write-acceptance` | 将业务规则转换为可执行验收标准 |
| `duke-write-spec` | 输出轻量 Spec、标准需求或完整 PRD |
| `duke-review-spec` | 从产品、研发和测试视角评审文档 |
| `duke-check-implementation` | 对照需求规则与实现证据完成验收 |

## 使用方式

- 端到端处理：使用 `$duke-doc`。
- 单独梳理需求：使用 `$duke-interview-requirement`。
- 单独生成验收标准：使用 `$duke-write-acceptance`。
- 已有明确需求并需要文档：使用 `$duke-write-spec`。
- 已有文档并需要评审：使用 `$duke-review-spec`。
- 已有需求和实现证据：使用 `$duke-check-implementation`。

各 Skill 的 `description` 已定义自动触发边界，日常自然语言请求也可以自动匹配。

## 安装

在 PowerShell 中从仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本会将 `skills` 下的六个 Skill 同步到 `CODEX_HOME\skills`；未设置 `CODEX_HOME` 时使用当前用户的 `.codex\skills`。

指定其他目录：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1 -TargetRoot 'D:\my-codex\skills'
```

该命令只对本次安装进程临时绕过脚本执行限制，不修改系统的长期执行策略。

## 结构

```text
skills/   独立可安装的 Skill
scripts/  仓库级安装工具
evals/    路由和职责边界回归场景
```
