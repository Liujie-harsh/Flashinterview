#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
FlashInterview 手写断言测试脚本。

不依赖任何测试框架，仅使用手写的 assert_true / assert_equal 函数，
对 data/cards.json 的数据特征进行校验。

运行方式：
    python F:\project\Flashinterview\scripts\test.py
"""

import json
import os
import re
import random
from collections import Counter

# ============================================================
# 全局状态
# ============================================================
CARDS_FILE = r"F:\project\Flashinterview\data\cards.json"

passes = 0
failures = 0

# 期望覆盖的公司列表（与 parse_notes.py 中的公司映射一致）
EXPECTED_COMPANIES = [
    "美团", "蚂蚁", "腾讯", "阿里", "宇树", "成都智信", "综合面经"
]

# 合法的 ID 前缀（company-pinyin）；custom 前缀用于 localStorage 自定义卡片，
# 不会出现在 cards.json 中，这里一并校验前缀白名单的完整性。
VALID_ID_PREFIXES = [
    "meituan", "mayi", "tencent", "ali", "yushu",
    "chengdu-zhixin", "zonghe", "custom"
]

# 合法的卡片类型枚举
VALID_TYPES = ["technical", "behavioral", "system", "algorithm"]

# ID 格式正则：{company-pinyin}-{round-code}-q{序号}
# round-code 取值：r1/r2/r3/r4/hr/all
ID_PATTERN = re.compile(
    r"^(meituan|mayi|tencent|ali|yushu|chengdu-zhixin|zonghe)"
    r"-(r[1-4]|hr|all)-q\d+$"
)


# ============================================================
# 手写断言函数
# ============================================================
def assert_true(condition, message):
    global passes, failures
    if condition:
        print(f"  ✓ {message}")
        passes += 1
    else:
        print(f"  ✗ FAIL: {message}")
        failures += 1


def assert_equal(actual, expected, message):
    global passes, failures
    if actual == expected:
        print(f"  ✓ {message}")
        passes += 1
    else:
        print(f"  ✗ FAIL: {message} (expected {expected}, got {actual})")
        failures += 1


# ============================================================
# 加载数据
# ============================================================
def load_cards():
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# ============================================================
# 测试 8.1: 预处理脚本输出
# ============================================================
def test_8_1_preprocess_output(data):
    print("\n--- 测试 8.1: 预处理脚本输出 ---")
    cards = data.get("cards", [])

    # 1. 顶层结构为 { "cards": [...] }
    assert_true(isinstance(data, dict) and "cards" in data,
                "顶层结构为 { cards: [...] }")
    assert_true(isinstance(cards, list),
                "cards 字段为列表")

    # 2. cards 数组长度 > 0（实际应为 180 左右）
    assert_true(len(cards) > 0, f"cards 数组长度 > 0 ({len(cards)})")

    # 3. 每张卡片都有必填字段
    valid_types_set = set(VALID_TYPES)
    field_ok = True
    type_enum_ok = True
    for i, card in enumerate(cards):
        if not isinstance(card.get("id"), str) or not card["id"].strip():
            print(f"    卡片 #{i} id 缺失或为空")
            field_ok = False
            break
        if not isinstance(card.get("question"), str) or not card["question"].strip():
            print(f"    卡片 #{i} ({card.get('id')}) question 缺失或为空")
            field_ok = False
            break
        if not isinstance(card.get("answer"), str):
            print(f"    卡片 #{i} ({card.get('id')}) answer 不是字符串")
            field_ok = False
            break
        if not isinstance(card.get("company"), str) or not card["company"].strip():
            print(f"    卡片 #{i} ({card.get('id')}) company 缺失或为空")
            field_ok = False
            break
        if not isinstance(card.get("round"), str) or not card["round"].strip():
            print(f"    卡片 #{i} ({card.get('id')}) round 缺失或为空")
            field_ok = False
            break
        if card.get("type") not in valid_types_set:
            print(f"    卡片 #{i} ({card.get('id')}) type 非法: {card.get('type')}")
            type_enum_ok = False
            break
    assert_true(field_ok, "所有卡片包含必填字段 (id/question/answer/company/round)")
    assert_true(type_enum_ok, "所有卡片 type 属于合法枚举 (technical/behavioral/system/algorithm)")

    # 4. 所有 id 唯一
    all_ids = [card["id"] for card in cards]
    assert_equal(len(set(all_ids)), len(all_ids),
                 f"所有 id 唯一 ({len(set(all_ids))} / {len(all_ids)})")

    # 5. 覆盖全部公司（7 个：美团/蚂蚁/腾讯/阿里/宇树/成都智信/综合面经）
    actual_companies = set(card["company"] for card in cards)
    missing = set(EXPECTED_COMPANIES) - actual_companies
    assert_true(len(missing) == 0,
                f"覆盖全部公司 (缺失: {sorted(missing) if missing else '无'})")

    # 6. 每个公司至少有 1 张卡片
    company_counts = Counter(card["company"] for card in cards)
    each_has_card = all(company_counts[c] >= 1 for c in EXPECTED_COMPANIES)
    assert_true(each_has_card, "每个公司至少有 1 张卡片")

    # 7. 打印统计信息
    print("\n  [统计] 总卡片数: %d" % len(cards))
    print("  [统计] 各公司卡片数:")
    for c in EXPECTED_COMPANIES:
        print(f"    - {c}: {company_counts.get(c, 0)}")
    type_counts = Counter(card["type"] for card in cards)
    print("  [统计] 各类型卡片数:")
    for t in VALID_TYPES:
        print(f"    - {t}: {type_counts.get(t, 0)}")


# ============================================================
# 测试 8.2: 筛选数据特征
# ============================================================
def test_8_2_filter_features(data):
    print("\n--- 测试 8.2: 筛选数据特征 ---")
    cards = data.get("cards", [])

    # 1. 按 company 分组，验证每个公司都有卡片
    by_company = {}
    for card in cards:
        by_company.setdefault(card["company"], []).append(card)
    all_companies_have_cards = all(
        len(by_company.get(c, [])) > 0 for c in EXPECTED_COMPANIES
    )
    assert_true(all_companies_have_cards, "按 company 分组，每个公司都有卡片")

    # 2. 按 type 分组，验证 technical 类型卡片数最多
    type_counts = Counter(card["type"] for card in cards)
    max_type = max(type_counts, key=lambda t: type_counts[t])
    assert_equal(max_type, "technical",
                 f"technical 类型卡片数最多 ({type_counts['technical']} 张)")

    # 3. 验证 "美团" + "technical" 组合有卡片（交集非空）
    meituan_tech = [
        c for c in cards
        if c["company"] == "美团" and c["type"] == "technical"
    ]
    assert_true(len(meituan_tech) > 0,
                f"美团 + technical 交集非空 ({len(meituan_tech)} 张)")

    # 4. 验证 "综合面经" + "algorithm" 组合可能为空也不报错
    zonghe_algo = [
        c for c in cards
        if c["company"] == "综合面经" and c["type"] == "algorithm"
    ]
    assert_true(len(zonghe_algo) >= 0,
                f"综合面经 + algorithm 组合查询不报错 (共 {len(zonghe_algo)} 张，允许为 0)")

    # 5. 验证存在 answer 为空的卡片（宇树/agent面经的纯问题列表）
    empty_answer_cards = [
        c for c in cards if not c.get("answer", "").strip()
    ]
    assert_true(len(empty_answer_cards) > 0,
                f"存在 answer 为空的卡片 ({len(empty_answer_cards)} 张)")

    yushu_empty = [
        c for c in empty_answer_cards if c["company"] == "宇树"
    ]
    assert_true(len(yushu_empty) > 0,
                f"宇树公司存在 answer 为空的卡片 ({len(yushu_empty)} 张)")


# ============================================================
# 测试 8.3: 抽认卡引擎数据基础
# ============================================================
def test_8_3_engine_data(data):
    print("\n--- 测试 8.3: 抽认卡引擎数据基础 ---")
    cards = data.get("cards", [])

    # 1. 统计有答案 / 无答案的卡片数
    with_answer = sum(1 for c in cards if c.get("answer", "").strip())
    without_answer = len(cards) - with_answer
    assert_true(with_answer > 0, f"有答案的卡片数 > 0 ({with_answer} 张)")
    assert_true(without_answer > 0, f"无答案的卡片数 > 0 ({without_answer} 张)")
    assert_equal(with_answer + without_answer, len(cards),
                 "有答案 + 无答案 = 总卡片数")

    # 2. 验证所有卡片都有有效 type
    valid_types_set = set(VALID_TYPES)
    all_valid_type = all(c.get("type") in valid_types_set for c in cards)
    assert_true(all_valid_type, "所有卡片都有有效 type")

    # 3. 验证 id 格式符合 {company-pinyin}-{round-code}-q{序号} 模式
    bad_ids = [c["id"] for c in cards if not ID_PATTERN.match(c["id"])]
    assert_equal(len(bad_ids), 0,
                 f"所有 id 符合 {{pinyin}}-{{round}}-q{{n}} 模式 (非法: {len(bad_ids)})")

    # 4. 抽取 10 个 id 样本，验证格式正确
    sample_size = min(10, len(cards))
    random.seed(42)  # 固定种子保证可复现
    sample = random.sample(cards, sample_size)
    sample_all_valid = all(ID_PATTERN.match(c["id"]) for c in sample)
    assert_true(sample_all_valid,
                f"抽取 {sample_size} 个 id 样本格式全部正确")
    print("    样本 ID:")
    for c in sample:
        print(f"      - {c['id']}")


# ============================================================
# 测试 8.4: 进度持久化设计
# ============================================================
def test_8_4_persistence_design(data):
    print("\n--- 测试 8.4: 进度持久化设计 ---")
    cards = data.get("cards", [])

    # localStorage key 格式：flashcard-progress-{cardId}
    # 要求 card.id 不包含会破坏 key 结构的特殊字符（空格、引号、冒号等）
    # 允许字符：字母、数字、连字符
    id_safe_pattern = re.compile(r"^[A-Za-z0-9\-]+$")

    # 1. 验证 card.id 不包含特殊字符（确保可作为 localStorage key 的一部分）
    unsafe_ids = [c["id"] for c in cards if not id_safe_pattern.match(c["id"])]
    assert_equal(len(unsafe_ids), 0,
                 f"所有 card.id 不含特殊字符 (不安全: {len(unsafe_ids)})")

    # 2. 验证所有 id 都以合法前缀开头
    #    cards.json 中只可能出现前 7 个前缀；custom 用于 localStorage 自定义卡片
    valid_prefixes_for_json = VALID_ID_PREFIXES  # 包含 custom 以校验白名单完整性
    bad_prefix_ids = []
    for c in cards:
        matched = False
        for prefix in valid_prefixes_for_json:
            if c["id"] == prefix or c["id"].startswith(prefix + "-"):
                matched = True
                break
        if not matched:
            bad_prefix_ids.append(c["id"])
    assert_equal(len(bad_prefix_ids), 0,
                 f"所有 id 以合法前缀开头 (非法前缀: {len(bad_prefix_ids)})")

    # 额外验证：cards.json 中的前缀确实属于 7 个解析来源（不含 custom）
    json_prefixes = set()
    for c in cards:
        for prefix in VALID_ID_PREFIXES:
            if c["id"].startswith(prefix + "-") or c["id"] == prefix:
                json_prefixes.add(prefix)
                break
    assert_true("custom" not in json_prefixes,
                "cards.json 不包含 custom 前缀 (custom 仅用于 localStorage)")
    print(f"    cards.json 中出现的 ID 前缀: {sorted(json_prefixes)}")


# ============================================================
# 主入口
# ============================================================
def main():
    global passes, failures

    print("=" * 40)
    print("FlashInterview 测试套件")
    print("=" * 40)

    if not os.path.exists(CARDS_FILE):
        print(f"\n[错误] 找不到数据文件: {CARDS_FILE}")
        print("=" * 40)
        print(f"结果: 0 通过, 1 失败")
        print("=" * 40)
        return

    data = load_cards()

    test_8_1_preprocess_output(data)
    test_8_2_filter_features(data)
    test_8_3_engine_data(data)
    test_8_4_persistence_design(data)

    print("\n" + "=" * 40)
    print(f"结果: {passes} 通过, {failures} 失败")
    print("=" * 40)


if __name__ == "__main__":
    main()
