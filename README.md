# Duke Doc Skills

面向中文产品需求与产品研究工作的 Codex Skill 集合，采用“专业 Skill＋编排 Skill”结构。

## Skills

| Skill | 用途 |
| --- | --- |
| `duke-doc` | 编排多阶段需求、数据、原型和文档资产 |
| `duke-interview-requirement` | 将模糊需求收敛为结构化需求包 |
| `duke-analyze-requirement-data` | 将历史业务数据转化为需求证据和待确认问题 |
| `duke-build-requirement-prototype` | 根据已确认规则构建和校验HTML需求原型，后台页面优先采用NG-ZORRO规范 |
| `duke-write-acceptance` | 将业务规则转换为可执行验收标准 |
| `duke-write-spec` | 输出轻量 Spec、标准需求或完整 PRD |
| `duke-review-spec` | 从产品、研发和测试视角评审文档 |
| `duke-check-implementation` | 对照需求规则与实现证据完成验收 |
| `duke-capture-web-research` | 采集网页资料并沉淀可追溯的产品研究笔记 |

## 使用方式

- 端到端处理：使用 `$duke-doc`。
- 单独梳理需求：使用 `$duke-interview-requirement`。
- 使用Excel、CSV或历史明细验证需求：使用 `$duke-analyze-requirement-data`。
- 制作或更新浏览器可预览的需求原型：使用 `$duke-build-requirement-prototype`。
- 单独生成验收标准：使用 `$duke-write-acceptance`。
- 已有明确需求并需要文档：使用 `$duke-write-spec`。
- 已有文档并需要评审：使用 `$duke-review-spec`。
- 已有需求和实现证据：使用 `$duke-check-implementation`。
- 需要将竞品、行业、规则或技术网页沉淀为研究笔记：使用 `$duke-capture-web-research`。

各 Skill 的 `description` 已定义自动触发边界，日常自然语言请求也可以自动匹配。

## 安装

在 PowerShell 中从仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本会将 `skills` 下的九个 Skill 同步到 `CODEX_HOME\skills`；未设置 `CODEX_HOME` 时使用当前用户的 `.codex\skills`。

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

## 回归检查

```powershell
python -X utf8 .\evals\run-regression.py
```

回归检查覆盖 Skill 基础结构、核心职责契约、文档校验正反例和 HTML 原型校验正反例。环境安装 `PyYAML` 时同时运行官方 `quick_validate.py`；缺少依赖时使用无依赖基础结构检查并明确警告。
