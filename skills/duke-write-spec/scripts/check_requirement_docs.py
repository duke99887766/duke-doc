#!/usr/bin/env python3
"""Validate requirement Markdown structure, traceability, links, and index registration."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote


COMMON_FRONTMATTER_REQUIRED = {"文档类型", "文档状态", "创建时间", "更新时间"}
REQUIREMENT_FRONTMATTER_REQUIRED = {"需求阶段", "版本"}
REQUIREMENT_DOC_TYPES = {"产品需求文档", "产品设计方案", "业务规则说明", "项目导航"}
VALID_DOC_STATUS = {"草稿", "评审中", "生效中", "待更新", "已归档"}
VALID_REQ_STAGE = {"需求中", "待开发", "开发中", "联调中", "验收中", "已上线", "已取消"}
VALID_PROTOTYPE_STATUS = {"无原型", "草稿", "待同步", "已同步", "已废弃"}
DATE_FIELDS = {"创建时间", "更新时间", "计划上线"}
PROTOTYPE_ENTRY_LINE_LIMIT = 60


def clean_yaml_scalar(value: str) -> str:
    return value.strip().strip('"').strip("'")


def parse_frontmatter(content: str) -> dict[str, str | list[str]]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---", 4)
    if end < 0:
        raise ValueError("Frontmatter缺少结束分隔符。")
    fields: dict[str, str | list[str]] = {}
    lines = content[4:end].splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line[0].isspace() or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = clean_yaml_scalar(value)
        if value:
            fields[key] = value
            index += 1
            continue

        list_values: list[str] = []
        cursor = index + 1
        while cursor < len(lines) and (not lines[cursor] or lines[cursor][0].isspace()):
            item = lines[cursor].strip()
            if item.startswith("-"):
                list_values.append(clean_yaml_scalar(item[1:]))
            cursor += 1
        fields[key] = list_values if list_values else ""
        index = cursor
    return fields


def scalar_field(frontmatter: dict[str, str | list[str]], field: str) -> str:
    value = frontmatter.get(field, "")
    return value if isinstance(value, str) else ""


def list_field(frontmatter: dict[str, str | list[str]], field: str) -> list[str]:
    value = frontmatter.get(field, "")
    if isinstance(value, list):
        return [item for item in value if item]
    return [value] if value else []


def parse_date(value: str, field: str, errors: list[str]) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} 必须使用 YYYY-MM-DD：{value}")
        return None


def is_template_document(path: Path, content: str) -> bool:
    return "Obsidian模板" in path.parts or "{{date}}" in content or "{{title}}" in content


def required_frontmatter_fields(path: Path, content: str, frontmatter: dict[str, str | list[str]]) -> set[str]:
    if is_template_document(path, content):
        return set()
    required = set(COMMON_FRONTMATTER_REQUIRED)
    if scalar_field(frontmatter, "文档类型") in REQUIREMENT_DOC_TYPES:
        required.update(REQUIREMENT_FRONTMATTER_REQUIRED)
    return required


def extract_defined_numbers(prefix: str, content: str) -> set[int]:
    escaped = re.escape(prefix)
    patterns = (
        rf"(?m)^\s*\|\s*{escaped}-(\d{{3,}})\s*\|",
        rf"(?m)^\s*(?:#{{1,6}}\s+|[-*+]\s+|\d+[.)]\s+)(?:\*\*)?{escaped}-(\d{{3,}})\b",
        rf"(?m)^\s*(?:\*\*)?{escaped}-(\d{{3,}})(?:\*\*)?\s*[：:]",
    )
    return {int(value) for pattern in patterns for value in re.findall(pattern, content)}


def check_continuity(prefix: str, content: str, warnings: list[str]) -> set[int]:
    numbers = {int(value) for value in re.findall(rf"\b{prefix}-(\d{{3,}})\b", content)}
    defined_numbers = extract_defined_numbers(prefix, content)
    if defined_numbers:
        missing = sorted(set(range(min(defined_numbers), max(defined_numbers) + 1)) - defined_numbers)
        if missing:
            warnings.append(
                f"[本文定义] {prefix}编号存在缺口："
                + ", ".join(f"{prefix}-{n:03d}" for n in missing)
            )
    return numbers


def clean_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    target = re.sub(r":\d+$", "", target)
    return unquote(target)


def resolve_local_target(path: Path, raw_target: str, repo_root: Path) -> Path | None:
    target = clean_link_target(raw_target)
    if not target or re.match(r"^(https?://|mailto:|tel:)", target, re.I):
        return None
    if re.match(r"^[A-Za-z]:[\\/]", target):
        return Path(target).resolve()
    if target.startswith("/"):
        return (repo_root / target.lstrip("/")).resolve()
    return (path.parent / target).resolve()


def check_links(path: Path, content: str, repo_root: Path, warnings: list[str]) -> None:
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
        resolved = resolve_local_target(path, raw_target, repo_root)
        if resolved is None:
            continue
        if not resolved.exists():
            warnings.append(f"[跨资产] 本地链接目标不存在：{raw_target}")


def find_deprecated_rules(content: str) -> set[str]:
    deprecated: set[str] = set()
    for line in content.splitlines():
        if re.search(r"已废弃|作废|不再使用|已被.+替代", line):
            deprecated.update(re.findall(r"\bR-\d{3,}\b", line))
    return deprecated


def second_level_headings(content: str) -> list[str]:
    headings: list[str] = []
    fence_char = ""
    for line in content.splitlines():
        stripped = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_char:
            if fence_match and fence_match.group(1)[0] == fence_char:
                fence_char = ""
            continue
        if fence_match:
            fence_char = fence_match.group(1)[0]
            continue
        heading_match = re.match(r"^##(?!#)\s+(.+?)\s*$", line)
        if heading_match:
            headings.append(heading_match.group(1).strip())
    return headings


def normalize_heading_title(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*(?:[.、]|\s)+", "", title).strip()


def check_update_record_position(content: str, warnings: list[str]) -> None:
    headings = second_level_headings(content)
    update_indexes = [
        index for index, heading in enumerate(headings) if normalize_heading_title(heading) == "更新记录"
    ]
    if len(update_indexes) > 1:
        warnings.append("[结构顺序] 更新记录只应保留一个二级章节。")
    if update_indexes and update_indexes[-1] != len(headings) - 1:
        warnings.append("[结构顺序] 更新记录应位于最后一个二级章节。")


def read_prototype_rules(path: Path, warnings: list[str]) -> set[str]:
    try:
        html = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        warnings.append(f"[原型关联] 原型文件不是有效UTF-8，未检查规则追溯：{path}")
        return set()
    values = re.findall(r"data-requirement-id\s*=\s*[\"']([^\"']+)[\"']", html, re.I)
    return {rule for value in values for rule in re.findall(r"\bR-\d{3,}\b", value)}


def check_prototype_contract(
    path: Path,
    content: str,
    frontmatter: dict[str, str | list[str]],
    repo_root: Path,
    document_rules: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    status = scalar_field(frontmatter, "原型状态")
    prototype_files = list_field(frontmatter, "原型文件")
    all_html_links = re.findall(r"\[[^\]]+\]\(([^)]*\.html(?:[#?][^)]*)?)\)", content, re.I)

    if not status:
        if all_html_links:
            warnings.append("[原型关联] 检测到HTML原型链接，但Frontmatter未登记原型状态和原型文件。")
        return

    if status not in VALID_PROTOTYPE_STATUS:
        errors.append(f"无效原型状态：{status}")
        return

    if status == "无原型":
        if prototype_files or all_html_links:
            warnings.append("[原型关联] 原型状态为“无原型”，但仍登记或引用了HTML原型。")
        return

    if not prototype_files:
        errors.append(f"原型状态为“{status}”时必须填写原型文件。")

    first_lines = "\n".join(content.splitlines()[:PROTOTYPE_ENTRY_LINE_LIMIT])
    top_html_links = re.findall(r"\[[^\]]+\]\(([^)]*\.html(?:[#?][^)]*)?)\)", first_lines, re.I)
    has_quick_entry = bool(re.search(r"^##\s+(?:\d+[.、]\s*)?研发快速入口\s*$", first_lines, re.M))
    has_l1_entry = bool(re.search(r"(?:页面)?原型[：:].*\.html", first_lines, re.I))
    if not top_html_links or not (has_quick_entry or has_l1_entry):
        errors.append(f"正文前{PROTOTYPE_ENTRY_LINE_LIMIT}行必须提供可点击的研发原型入口。")

    top_targets = {
        resolved
        for target in top_html_links
        if (resolved := resolve_local_target(path, target, repo_root)) is not None
    }
    deprecated_rules = find_deprecated_rules(content)
    for raw_target in prototype_files:
        resolved = resolve_local_target(path, raw_target, repo_root)
        if resolved is None:
            warnings.append(f"[原型关联] 原型文件应填写本地HTML路径：{raw_target}")
            continue
        if not resolved.is_file():
            errors.append(f"原型文件不存在：{raw_target}")
            continue
        if resolved not in top_targets:
            warnings.append(f"[原型关联] 研发快速入口未引用Frontmatter中的原型文件：{raw_target}")
        if status != "已同步" or resolved.suffix.lower() != ".html":
            continue
        prototype_rules = read_prototype_rules(resolved, warnings)
        unknown_rules = sorted(prototype_rules - document_rules)
        uses_derivative_rules = bool(re.search(r"\bSR-\d{3,}\b", content))
        if document_rules and unknown_rules and not uses_derivative_rules:
            warnings.append("[原型关联] 原型引用了本文未登记的规则：" + ", ".join(unknown_rules))
        stale_rules = sorted(prototype_rules & deprecated_rules)
        if stale_rules:
            errors.append("已同步原型仍引用已废弃规则：" + ", ".join(stale_rules))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--require-frontmatter", action="store_true")
    parser.add_argument("--expect-update-date")
    args = parser.parse_args()

    path = args.document.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not path.is_file():
        print(f"ERROR: 文件不存在：{path}")
        return 2
    if path.suffix.lower() != ".md":
        print(f"ERROR: 不是Markdown文件：{path}")
        return 2

    try:
        content = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        print(f"ERROR: 文件不是有效UTF-8：{exc}")
        return 1

    try:
        frontmatter = parse_frontmatter(content)
    except ValueError as exc:
        errors.append(str(exc))
        frontmatter = {}

    if args.require_frontmatter and not frontmatter:
        errors.append("正式需求文档缺少Frontmatter。")
    if frontmatter:
        missing_fields = sorted(required_frontmatter_fields(path, content, frontmatter) - set(frontmatter))
        if missing_fields:
            errors.append("Frontmatter缺少字段：" + ", ".join(missing_fields))
        document_status = scalar_field(frontmatter, "文档状态")
        requirement_stage = scalar_field(frontmatter, "需求阶段")
        version = scalar_field(frontmatter, "版本")
        if document_status and document_status not in VALID_DOC_STATUS:
            errors.append(f"无效文档状态：{document_status}")
        if requirement_stage and requirement_stage not in VALID_REQ_STAGE:
            errors.append(f"无效需求阶段：{requirement_stage}")
        if version and not re.fullmatch(r"V\d+\.\d+(?:\.\d+)?", version):
            errors.append(f"版本格式无效：{version}")

        template_document = is_template_document(path, content)
        parsed_dates = {
            field: None if template_document else parse_date(scalar_field(frontmatter, field), field, errors)
            for field in DATE_FIELDS
        }
        created = parsed_dates.get("创建时间")
        updated = parsed_dates.get("更新时间")
        if created and updated and updated < created:
            errors.append("更新时间不能早于创建时间。")
        actual_update_date = scalar_field(frontmatter, "更新时间")
        if args.expect_update_date and actual_update_date != args.expect_update_date:
            errors.append(f"更新时间应为 {args.expect_update_date}，实际为 {actual_update_date or '空'}")

    uses_derivative_rules = bool(re.search(r"\bSR-\d{3,}\b", content))
    if uses_derivative_rules:
        check_continuity("SR", content, warnings)
        check_continuity("SAC", content, warnings)
        rule_numbers = {int(value) for value in re.findall(r"\bR-(\d{3,})\b", content)}
    else:
        rule_numbers = check_continuity("R", content, warnings)
        check_continuity("AC", content, warnings)
    for line_number, line in enumerate(content.splitlines(), start=1):
        is_quick_acceptance_link = line.lstrip().startswith("| 验收标准 |")
        if (
            re.search(r"\bAC-\d{3,}\b", line)
            and not re.search(r"\bR-\d{3,}\b", line)
            and not is_quick_acceptance_link
        ):
            warnings.append(f"[规则追溯] 第 {line_number} 行的验收编号未在同一行引用规则编号。")

    check_update_record_position(content, warnings)

    repo_root = args.repo_root.resolve() if args.repo_root else path.parent
    check_links(path, content, repo_root, warnings)
    check_prototype_contract(
        path,
        content,
        frontmatter,
        repo_root,
        {f"R-{number:03d}" for number in rule_numbers},
        errors,
        warnings,
    )

    if args.index:
        index_path = args.index.resolve()
        if not index_path.is_file():
            errors.append(f"索引文件不存在：{index_path}")
        else:
            index_content = index_path.read_text(encoding="utf-8-sig")
            if path.name not in index_content and path.stem not in index_content:
                warnings.append(f"[跨资产] 索引中未找到当前文档：{path.name}")

    print(f"Requirement document check: {path}")
    for item in errors:
        print(f"ERROR: {item}")
    for item in dict.fromkeys(warnings):
        print(f"WARN: {item}")
    if not errors and not warnings:
        print("OK: 未发现文档结构问题。")
    elif not errors:
        print("OK: 无阻塞错误，存在需评估的警告。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
