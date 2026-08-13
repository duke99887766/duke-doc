#!/usr/bin/env python3
"""Run deterministic regression checks for the Duke Doc skill collection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SKILL_CREATOR_VALIDATOR = Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"


def validation_python() -> str:
    candidates = [
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe",
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.is_file():
            code, _ = run([str(candidate), "-c", "import yaml"])
            if code == 0:
                return str(candidate)
    return sys.executable


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


def assert_contains(path: Path, phrases: list[str], failures: list[str]) -> None:
    content = path.read_text(encoding="utf-8-sig")
    for phrase in phrases:
        if phrase not in content:
            failures.append(f"{path.relative_to(ROOT)} 缺少契约关键词：{phrase}")


def assert_clean_utf8(path: Path, failures: list[str]) -> None:
    content = path.read_text(encoding="utf-8-sig")
    if "�" in content:
        failures.append(f"{path.relative_to(ROOT)} 包含 Unicode 替换字符，可能存在编码损坏。")


def basic_skill_validation(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return ["缺少 SKILL.md"]
    content = skill_file.read_text(encoding="utf-8-sig")
    if not content.startswith("---\n") or "\n---\n" not in content[4:]:
        return ["SKILL.md 缺少有效 Frontmatter 分隔符"]
    frontmatter = content[4 : content.find("\n---\n", 4)]
    fields = {}
    for line in frontmatter.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    if fields.get("name") != skill_dir.name:
        errors.append(f"name 应为 {skill_dir.name}")
    if not fields.get("description"):
        errors.append("description 不能为空")
    extra = sorted(set(fields) - {"name", "description"})
    if extra:
        errors.append("Frontmatter 包含非标准字段：" + ", ".join(extra))
    return errors


def main() -> int:
    failures: list[str] = []
    checks = 0
    yaml_python = validation_python()
    official_validator_available = run([yaml_python, "-c", "import yaml"])[0] == 0

    for skill_dir in sorted(path for path in SKILLS.iterdir() if path.is_dir()):
        checks += 1
        if not SKILL_CREATOR_VALIDATOR.is_file():
            failures.append(f"Skill 校验器不存在：{SKILL_CREATOR_VALIDATOR}")
            break
        if official_validator_available:
            code, output = run([yaml_python, "-X", "utf8", str(SKILL_CREATOR_VALIDATOR), str(skill_dir)])
            if code:
                failures.append(f"{skill_dir.name} 结构校验失败：{output}")
        else:
            for error in basic_skill_validation(skill_dir):
                failures.append(f"{skill_dir.name} 基础结构校验失败：{error}")

    contracts = {
        SKILLS / "duke-interview-requirement" / "SKILL.md": [
            "每轮集中询问 2～4 个关键问题",
            "恢复已有口径",
            "简短表达回答时",
            "R-001",
            "Q-001",
        ],
        SKILLS / "duke-doc" / "SKILL.md": [
            "需求状态账本",
            "影响资产清单",
            "历史数据",
            "原型",
        ],
        SKILLS / "duke-write-spec" / "SKILL.md": [
            "check_requirement_docs.py",
            "研发快速入口",
            "Frontmatter",
        ],
        SKILLS / "duke-build-requirement-prototype" / "SKILL.md": [
            "data-requirement-id",
            "check_html_prototype.py",
            "NG-ZORRO 18.2.x",
            "admin-ng-zorro-prototype.html",
        ],
        SKILLS / "duke-build-requirement-prototype" / "references" / "ng-zorro-admin-patterns.md": [
            "ng-zorro-antd@18.2.x",
            "data-design-system=\"ng-zorro-18.2.x\"",
            "既有页面",
            "移动端、营销页和非后台页面",
        ],
    }
    for path, phrases in contracts.items():
        checks += len(phrases)
        assert_contains(path, phrases, failures)

    prototype_openai_yaml = SKILLS / "duke-build-requirement-prototype" / "agents" / "openai.yaml"
    checks += 3
    assert_contains(prototype_openai_yaml, ["需求原型构建", "NG-ZORRO", "$duke-build-requirement-prototype"], failures)
    checks += 1
    assert_clean_utf8(prototype_openai_yaml, failures)

    document_validator = SKILLS / "duke-write-spec" / "scripts" / "check_requirement_docs.py"
    prototype_validator = SKILLS / "duke-build-requirement-prototype" / "scripts" / "check_html_prototype.py"
    fixtures = ROOT / "evals" / "fixtures"
    valid_doc = fixtures / "valid-requirement.md"
    invalid_doc = fixtures / "invalid-requirement.md"
    valid_html = fixtures / "valid-prototype.html"
    invalid_html = fixtures / "invalid-prototype.html"
    admin_html = SKILLS / "duke-build-requirement-prototype" / "assets" / "admin-ng-zorro-prototype.html"

    checks += 1
    code, output = run([sys.executable, "-X", "utf8", str(document_validator), str(valid_doc), "--require-frontmatter"])
    if code:
        failures.append(f"合法需求文档未通过：{output}")

    checks += 1
    code, _ = run([sys.executable, "-X", "utf8", str(document_validator), str(invalid_doc), "--require-frontmatter"])
    if code == 0:
        failures.append("缺失需求字段的正式文档未被阻断。")

    checks += 1
    code, output = run([sys.executable, "-X", "utf8", str(prototype_validator), str(valid_html)])
    if code or "WARN:" in output:
        failures.append(f"合法原型未干净通过：{output}")

    checks += 1
    code, _ = run([sys.executable, "-X", "utf8", str(prototype_validator), str(invalid_html)])
    if code == 0:
        failures.append("重复 HTML id 未被阻断。")

    checks += 1
    code, output = run([sys.executable, "-X", "utf8", str(prototype_validator), str(admin_html)])
    if code or "WARN:" in output:
        failures.append(f"NG-ZORRO 后台模板未干净通过：{output}")

    if failures:
        print(f"Regression checks: {checks}, failures: {len(failures)}")
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    print(f"Regression checks: {checks}, failures: 0")
    if not official_validator_available:
        print("WARN: PyYAML 不可用，官方 quick_validate.py 已由无依赖基础结构检查替代。")
    print("OK: Skill 结构、核心契约、文档校验和原型校验均通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
