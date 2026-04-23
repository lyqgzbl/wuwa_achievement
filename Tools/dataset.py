"""Assemble hierarchical dataset from decoded models and translated texts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .models import Achievement, Category, Group


def build_dataset(
    locale: str,
    achievements: Sequence[Achievement],
    groups: Sequence[Group],
    categories: Sequence[Category],
    texts: dict[str, str],
) -> dict[str, Any]:
    def t(key: str) -> str:
        if not key:
            return ""
        return texts.get(key, "")

    cat_items: list[dict[str, Any]] = []
    categories_sorted = sorted(categories, key=lambda c: c.id)

    groups_sorted = sorted(groups, key=lambda g: (g.category_id, g.sort, g.id))
    groups_by_category: dict[int, list[Group]] = {}
    for g in groups_sorted:
        groups_by_category.setdefault(g.category_id, []).append(g)

    achievements_sorted = sorted(achievements, key=lambda a: (a.group_id, a.id))
    achievements_by_group: dict[int, list[Achievement]] = {}
    for a in achievements_sorted:
        achievements_by_group.setdefault(a.group_id, []).append(a)

    allowed_category_names_in_order = ["索拉漫行", "长路留迹", "铿锵刃鸣", "诸音声轨"]
    categories_by_name: dict[str, Category] = {}
    for cat in categories_sorted:
        name = t(cat.name_key) or cat.name_key
        if name in allowed_category_names_in_order and name not in categories_by_name:
            categories_by_name[name] = cat

    for cat_name in allowed_category_names_in_order:
        cat = categories_by_name.get(cat_name)
        if not cat:
            continue

        cat_groups = groups_by_category.get(cat.id, [])
        group_items: list[dict[str, Any]] = []
        for g in cat_groups:
            ach_items: list[dict[str, Any]] = []
            for a in achievements_by_group.get(g.id, []):
                ach_items.append(
                    {
                        "id": a.id,
                        "group_id": a.group_id,
                        "level": a.level,
                        "name_key": a.name_key,
                        "desc_key": a.desc_key,
                        "name": t(a.name_key),
                        "desc": t(a.desc_key),
                    }
                )

            group_items.append(
                {
                    "id": g.id,
                    "category_id": g.category_id,
                    "sort": g.sort,
                    "name_key": g.name_key,
                    "name": t(g.name_key) or g.name_key,
                    "achievements": ach_items,
                }
            )

        cat_items.append(
            {
                "id": cat.id,
                "name_key": cat.name_key,
                "name": cat_name,
                "groups": group_items,
            }
        )

    return {"locale": locale, "categories": cat_items}
