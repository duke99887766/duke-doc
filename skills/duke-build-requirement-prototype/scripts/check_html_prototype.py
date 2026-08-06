#!/usr/bin/env python3
"""Perform dependency-free structural checks for an HTML requirement prototype."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


class PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.label_targets: list[str] = []
        self.requirement_ids: list[str] = []
        self.missing_alt = 0
        self.buttons_without_type = 0
        self.empty_accessible_buttons = 0
        self._button_stack: list[dict[str, object]] = []
        self._script_stack: list[list[str]] = []
        self.inline_scripts: list[str] = []
        self.tags: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {key.lower(): value for key, value in attrs}
        self.tags[tag] += 1

        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "label" and values.get("for"):
            self.label_targets.append(str(values["for"]))
        if values.get("data-requirement-id"):
            self.requirement_ids.extend(str(values["data-requirement-id"]).split())
        if tag == "img" and not values.get("alt"):
            self.missing_alt += 1
        if tag == "button":
            if not values.get("type"):
                self.buttons_without_type += 1
            self._button_stack.append(
                {
                    "text": [],
                    "has_name": bool(values.get("aria-label") or values.get("title")),
                }
            )
        if tag == "script" and not values.get("src") and values.get("type") not in {
            "application/json",
            "application/ld+json",
        }:
            self._script_stack.append([])

    def handle_data(self, data: str) -> None:
        if self._button_stack:
            text_parts = self._button_stack[-1]["text"]
            assert isinstance(text_parts, list)
            text_parts.append(data)
        if self._script_stack:
            self._script_stack[-1].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "button" and self._button_stack:
            button = self._button_stack.pop()
            text_parts = button["text"]
            assert isinstance(text_parts, list)
            if not "".join(text_parts).strip() and not button["has_name"]:
                self.empty_accessible_buttons += 1
        if tag == "script" and self._script_stack:
            self.inline_scripts.append("".join(self._script_stack.pop()))


def check_javascript(scripts: list[str]) -> list[str]:
    node = shutil.which("node")
    if not node:
        return ["未找到 Node.js，跳过内联JavaScript语法检查。"] if scripts else []

    errors: list[str] = []
    for index, script in enumerate(scripts, start=1):
        if not script.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write(script)
            temp_path = Path(handle.name)
        try:
            result = subprocess.run(
                [node, "--check", str(temp_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                errors.append(f"第 {index} 段内联JavaScript语法错误：{detail}")
        finally:
            temp_path.unlink(missing_ok=True)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file", type=Path)
    args = parser.parse_args()
    path = args.html_file.resolve()

    if not path.is_file():
        print(f"ERROR: 文件不存在：{path}")
        return 2
    if path.suffix.lower() not in {".html", ".htm"}:
        print(f"ERROR: 不是HTML文件：{path}")
        return 2

    content = path.read_text(encoding="utf-8-sig")
    html_parser = PrototypeParser()
    try:
        html_parser.feed(content)
        html_parser.close()
    except Exception as exc:  # HTMLParser exposes malformed parser states as exceptions.
        print(f"ERROR: HTML解析失败：{exc}")
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    for required in ("html", "head", "body", "title"):
        if not html_parser.tags[required]:
            errors.append(f"缺少 <{required}> 元素。")

    duplicate_ids = sorted(key for key, count in Counter(html_parser.ids).items() if count > 1)
    if duplicate_ids:
        errors.append("存在重复 id：" + ", ".join(duplicate_ids))

    known_ids = set(html_parser.ids)
    broken_labels = sorted(set(html_parser.label_targets) - known_ids)
    if broken_labels:
        errors.append("label 的 for 未找到对应 id：" + ", ".join(broken_labels))

    invalid_requirement_ids = sorted(
        set(value for value in html_parser.requirement_ids if not re.fullmatch(r"R-\d{3,}", value))
    )
    if invalid_requirement_ids:
        warnings.append("非标准需求编号：" + ", ".join(invalid_requirement_ids))
    if not html_parser.requirement_ids:
        warnings.append("未发现 data-requirement-id，无法建立规则到组件追溯。")
    if html_parser.missing_alt:
        warnings.append(f"有 {html_parser.missing_alt} 个图片缺少 alt。")
    if html_parser.buttons_without_type:
        warnings.append(f"有 {html_parser.buttons_without_type} 个按钮缺少 type。")
    if html_parser.empty_accessible_buttons:
        warnings.append(f"有 {html_parser.empty_accessible_buttons} 个无文本按钮缺少 aria-label 或 title。")

    errors.extend(check_javascript(html_parser.inline_scripts))

    print(f"HTML prototype check: {path}")
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    if not errors and not warnings:
        print("OK: 未发现结构问题。")
    elif not errors:
        print("OK: 无阻塞错误，存在需评估的警告。")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
