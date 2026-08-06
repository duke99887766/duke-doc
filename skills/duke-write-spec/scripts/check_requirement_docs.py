#!/usr/bin/env python3
"""Validate requirement Markdown structure, traceability, links, and index registration."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote


FRONTMATTER_REQUIRED = {"文档类型", "文档状态", "需求阶段", "版本", "创建时间", "更新时间"}
VALID_DOC_STATUS = {"草稿", "评审中", "生效中", "待更新", "已归档"}
VALID_REQ_STAGE = {"需求中", "待开发", "开发中", "联调中", "验收中", "已上线", "已取消"}
DATE_FIELDS = {"创建时间", "更新时间", "计划上线"}


def parse_frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---", 4)
    if end < 0:
        raise ValueError("Frontmatter缺少结束分隔符。")
    fields: dict[str, str] = {}
    for line in content[4:end].splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def parse_date(value: str, field: str, errors: list[str]) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} 必须使用 YYYY-MM-DD：{value}")
        return None


def check_continuity(prefix: str, content: str, warnings: list[str]) -> set[int]:
    numbers = {int(value) for value in re.findall(rf"\b{prefix}-(\d{{3,}})\b", content)}
    if numbers:
        missing = sorted(set(range(min(numbers), max(numbers) + 1)) - numbers)
        if missing:
            warnings.append(f"{prefix}编号存在缺口：" + ", ".join(f"{prefix}-{n:03d}" for n in missing))
    return numbers


def clean_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0]
    target = re.sub(r":\d+$", "", target)
    return unquote(target)


def check_links(path: Path, content: str, repo_root: Path, warnings: list[str]) -> None:
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
        target = clean_link_target(raw_target)
        if not target or re.match(r"^(https?://|mailto:|tel:)", target, re.I):
            continue
        if re.match(r"^[A-Za-z]:[\\/]", target):
            resolved = Path(target)
        elif target.startswith("/"):
            resolved = repo_root / target.lstrip("/")
        else:
            resolved = path.parent / target
        if not resolved.exists():
            warnings.append(f"本地链接目标不存在：{raw_target}")


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
        missing_fields = sorted(FRONTMATTER_REQUIRED - set(frontmatter))
        if missing_fields:
            errors.append("Frontmatter缺少字段：" + ", ".join(missing_fields))
        if frontmatter.get("文档状态") and frontmatter["文档状态"] not in VALID_DOC_STATUS:
            errors.append(f"无效文档状态：{frontmatter['文档状态']}")
        if frontmatter.get("需求阶段") and frontmatter["需求阶段"] not in VALID_REQ_STAGE:
            errors.append(f"无效需求阶段：{frontmatter['需求阶段']}")
        if frontmatter.get("版本") and not re.fullmatch(r"V\d+\.\d+(?:\.\d+)?", frontmatter["版本"]):
            errors.append(f"版本格式无效：{frontmatter['版本']}")

        parsed_dates = {field: parse_date(frontmatter.get(field, ""), field, errors) for field in DATE_FIELDS}
        created = parsed_dates.get("创建时间")
        updated = parsed_dates.get("更新时间")
        if created and updated and updated < created:
            errors.append("更新时间不能早于创建时间。")
        if args.expect_update_date and frontmatter.get("更新时间") != args.expect_update_date:
            errors.append(f"更新时间应为 {args.expect_update_date}，实际为 {frontmatter.get('更新时间', '空')}")

    check_continuity("R", content, warnings)
    check_continuity("AC", content, warnings)
    for line_number, line in enumerate(content.splitlines(), start=1):
        if re.search(r"\bAC-\d{3,}\b", line) and not re.search(r"\bR-\d{3,}\b", line):
            warnings.append(f"第 {line_number} 行的验收编号未在同一行引用规则编号。")

    repo_root = args.repo_root.resolve() if args.repo_root else path.parent
    check_links(path, content, repo_root, warnings)

    if args.index:
        index_path = args.index.resolve()
        if not index_path.is_file():
            errors.append(f"索引文件不存在：{index_path}")
        else:
            index_content = index_path.read_text(encoding="utf-8-sig")
            if path.name not in index_content and path.stem not in index_content:
                warnings.append(f"索引中未找到当前文档：{path.name}")

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
