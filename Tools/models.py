"""Data models for achievements, groups and categories."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Achievement:
    id: int
    group_id: int
    level: int
    name_key: str
    desc_key: str


@dataclass(frozen=True)
class Group:
    id: int
    category_id: int
    sort: int
    name_key: str


@dataclass(frozen=True)
class Category:
    id: int
    name_key: str
