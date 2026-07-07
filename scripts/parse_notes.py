#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
解析 9 份 markdown 面经文件，生成 cards.json。

支持的格式变体：
  - 格式1a: ### Q1：问题（带答案）
  - 格式1b: Q1：问题（无 ### 前缀，通常无答案）
  - 格式1c: ### 1. 问题（带答案）
  - 格式2:  数字. 问题（编号列表，按 ## 一面 等分轮次）
  - 格式3:  数字. 问题（混合格式，部分有段落答案）
"""

import os
import re
import json
from collections import Counter

SOURCE_DIR = r"F:\BaiduNetdiskDownload\找工作-找实习的资料在这里\agent开发岗"
OUTPUT_FILE = r"F:\project\Flashinterview\data\cards.json"

FILES = [
    "美团 AI 应用开发一面面试整理.md",
    "美团 AI 应用开发二面（时长 70 分钟）.md",
    "蚂蚁AI应用开发二面面经整理.md",
    "蚂蚁 AI 应用开发三面.md",
    "腾讯 AI 应用面试题整理.md",
    "阿里千问 AI Agent 三轮技术面面经整理.md",
    "宇树科技AI Agent开发三轮技术面试题整理.md",
    "成都xx智信面经.md",
    "agent面经.md",
]

# (关键词, 显示名, 拼音)
COMPANY_KEYWORDS = [
    ("美团", "美团", "meituan"),
    ("蚂蚁", "蚂蚁", "mayi"),
    ("腾讯", "腾讯", "tencent"),
    ("阿里", "阿里", "ali"),
    ("宇树", "宇树", "yushu"),
    ("智信", "成都智信", "chengdu-zhixin"),
]

# 需要跳过的章节关键词
SKIP_KEYWORDS = ["自我介绍", "笔试", "反问", "感受", "总结", "基本信息"]

# 轮次映射
ROUND_MAP = {
    "一面": ("一面", "r1"),
    "二面": ("二面", "r2"),
    "三面": ("三面", "r3"),
    "四面": ("四面", "r4"),
    "HR面": ("HR面", "hr"),
    "HR 面": ("HR面", "hr"),
}


def extract_company(filename, content):
    """从文件名或内容中提取公司名。"""
    if "agent面经" in filename.lower():
        return "综合面经", "zonghe"

    lines = content.split("\n")
    # 先看前 10 行中的 # 标题
    for line in lines[:10]:
        if line.startswith("#"):
            for keyword, name, pinyin in COMPANY_KEYWORDS:
                if keyword in line:
                    return name, pinyin

    # 回退到文件名
    for keyword, name, pinyin in COMPANY_KEYWORDS:
        if keyword in filename:
            return name, pinyin

    # 回退到正文
    for keyword, name, pinyin in COMPANY_KEYWORDS:
        if keyword in content:
            return name, pinyin

    return "未知", "unknown"


def extract_round_from_text(text):
    """从单行文本中提取轮次。"""
    if re.search(r"HR\s*面", text, re.IGNORECASE):
        return "HR面", "hr"
    for cn in ["一面", "二面", "三面", "四面"]:
        if cn in text:
            return ROUND_MAP[cn]
    num_map = {"1": ("一面", "r1"), "2": ("二面", "r2"), "3": ("三面", "r3"), "4": ("四面", "r4")}
    m = re.search(r"(\d)\s*面", text)
    if m and m.group(1) in num_map:
        return num_map[m.group(1)]
    return None, None


def find_round_sections(content):
    """查找多轮次文件中的轮次分段。返回 [(round_name, round_code, lines), ...]"""
    sections = []
    current_round = None
    current_lines = []

    for line in content.split("\n"):
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            header_text = header_match.group(2).strip()
            if header_text in ROUND_MAP:
                if current_round:
                    sections.append((current_round[0], current_round[1], current_lines))
                current_round = ROUND_MAP[header_text]
                current_lines = []
                continue
        if current_round:
            current_lines.append(line)

    if current_round:
        sections.append((current_round[0], current_round[1], current_lines))

    return sections


def extract_round(content, filename):
    """单轮次文件提取轮次。"""
    lines = content.split("\n")
    # 先看前 10 行的 # 标题
    for line in lines[:10]:
        if line.startswith("#"):
            rn, rc = extract_round_from_text(line)
            if rn:
                return rn, rc
            break
    # 再看前 20 行正文
    for line in lines[:20]:
        rn, rc = extract_round_from_text(line)
        if rn:
            return rn, rc
    return "综合", "all"


def determine_question_pattern(content):
    """根据内容判定问题匹配模式。"""
    if re.search(r"^###\s*Q\d+[：:]", content, re.MULTILINE):
        return re.compile(r"^###\s*Q(\d+)[：:]\s*(.+)$")
    if re.search(r"^Q\d+[：:]", content, re.MULTILINE):
        return re.compile(r"^Q(\d+)[：:]\s*(.+)$")
    if re.search(r"^###\s*\d+\.", content, re.MULTILINE):
        return re.compile(r"^###\s*(\d+)\.\s*(.+)$")
    return re.compile(r"^(\d+)\.\s*(.+)$")


def should_skip_section(header_text):
    """判断章节是否应跳过。"""
    return any(kw in header_text for kw in SKIP_KEYWORDS)


def infer_type(question):
    """推断题目类型。"""
    if any(kw in question for kw in ["手写算法", "实现一个", "算法"]):
        return "algorithm"
    if any(kw in question for kw in ["设计", "架构", "方案", "规划"]):
        return "system"
    if any(kw in question for kw in ["为什么选择", "职业规划", "优点缺点", "团队氛围", "如何评价自己", "薪资"]):
        return "behavioral"
    return "technical"


def strip_empty_lines(text):
    """去除前后空白行，保留内部格式。"""
    # 同时清除零宽空格等不可见字符的判断
    def is_blank(line):
        cleaned = line.replace("\u200b", "").replace("\u00a0", "").replace("\ufeff", "")
        return not cleaned.strip()

    lines = text.split("\n")
    while lines and is_blank(lines[0]):
        lines.pop(0)
    while lines and is_blank(lines[-1]):
        lines.pop()
    return "\n".join(lines)


def parse_lines(lines, question_pattern, company, company_pinyin,
                round_name, round_code, company_counters):
    """逐行解析，提取卡片。"""
    cards = []
    current_question = None
    current_answer = []
    in_skip_section = False
    skip_level = None

    def save_current():
        nonlocal current_question, current_answer
        if current_question is not None and not in_skip_section:
            answer_text = strip_empty_lines("\n".join(current_answer))
            card = {
                "id": f"{company_pinyin}-{round_code}-q{company_counters[company_pinyin]}",
                "question": current_question.strip(),
                "answer": answer_text,
                "company": company,
                "round": round_name,
                "type": infer_type(current_question),
                "tags": [],
            }
            cards.append(card)
        current_question = None
        current_answer = []

    for line in lines:
        # 1. 先检查问题模式（### Q1：... 和 ### 1. ... 等以 # 开头的问题行）
        q_match = question_pattern.match(line)
        if q_match:
            if in_skip_section:
                continue
            save_current()
            q_text = q_match.group(2).strip()
            if "自我介绍" in q_text:
                current_question = None
                continue
            company_counters[company_pinyin] += 1
            current_question = q_text
            current_answer = []
            continue

        # 2. 章节标题
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            header_level = len(header_match.group(1))
            header_text = header_match.group(2).strip()

            # 轮次标题（在单轮次文件中可能出现，当作普通边界处理）
            if header_text in ROUND_MAP:
                save_current()
                in_skip_section = False
                skip_level = None
                continue

            if should_skip_section(header_text):
                save_current()
                in_skip_section = True
                skip_level = header_level
                continue

            if in_skip_section:
                # 同级或更高级标题 -> 退出跳过
                if header_level <= skip_level:
                    save_current()
                    in_skip_section = False
                    skip_level = None
                # 更深级标题 -> 仍在跳过章节内
                continue
            else:
                save_current()
                continue

        # 3. 分隔线 ------
        if re.match(r"^-{3,}$", line.strip()):
            save_current()
            continue

        # 4. 跳过章节内的内容
        if in_skip_section:
            continue

        # 5. 答案行
        if current_question is not None:
            current_answer.append(line)

    save_current()
    return cards


def parse_file(filepath, filename, company_counters):
    """解析单个文件。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    company, company_pinyin = extract_company(filename, content)
    if company_pinyin not in company_counters:
        company_counters[company_pinyin] = 0

    question_pattern = determine_question_pattern(content)
    round_sections = find_round_sections(content)

    cards = []
    if round_sections:
        for round_name, round_code, section_lines in round_sections:
            section_cards = parse_lines(
                section_lines, question_pattern,
                company, company_pinyin,
                round_name, round_code, company_counters,
            )
            cards.extend(section_cards)
    else:
        round_name, round_code = extract_round(content, filename)
        cards = parse_lines(
            content.split("\n"), question_pattern,
            company, company_pinyin,
            round_name, round_code, company_counters,
        )

    return cards, company


def main():
    all_cards = []
    company_counters = {}
    file_stats = []

    for filename in FILES:
        filepath = os.path.join(SOURCE_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[警告] 文件不存在: {filepath}")
            continue

        cards, company = parse_file(filepath, filename, company_counters)
        all_cards.extend(cards)
        file_stats.append((filename, len(cards), company))

    # 写出 JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"cards": all_cards}, f, ensure_ascii=False, indent=2)

    # 统计信息
    print("=" * 60)
    print("解析统计信息")
    print("=" * 60)
    for filename, count, company in file_stats:
        print(f"  [{company}] {filename} -> {count} 张卡片")
    print("-" * 60)
    print(f"总卡片数: {len(all_cards)}")
    print()

    type_counts = Counter(card["type"] for card in all_cards)
    print("各类型卡片数:")
    for t in ["technical", "system", "algorithm", "behavioral"]:
        print(f"  {t}: {type_counts.get(t, 0)}")
    print()

    company_counts = Counter(card["company"] for card in all_cards)
    print("各公司卡片数:")
    for c, n in company_counts.items():
        print(f"  {c}: {n}")
    print("=" * 60)
    print(f"输出文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
