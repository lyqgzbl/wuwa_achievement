"""Low-level FlatBuffers binary parser.

Decodes FlatBuffers tables from raw bytes without requiring the FlatBuffers
library or generated code.
"""

from __future__ import annotations

from collections.abc import Sequence


def _u16(b: bytes, pos: int) -> int:
    return int.from_bytes(b[pos : pos + 2], "little")


def _i32(b: bytes, pos: int) -> int:
    return int.from_bytes(b[pos : pos + 4], "little", signed=True)


def _u32(b: bytes, pos: int) -> int:
    return int.from_bytes(b[pos : pos + 4], "little", signed=False)


def _read_string(b: bytes, table_start: int, field_off: int) -> str:
    if field_off == 0:
        return ""
    p = table_start + field_off
    rel = _i32(b, p)
    s0 = p + rel
    if s0 < 0 or s0 + 4 > len(b):
        return ""
    n = _i32(b, s0)
    if n < 0 or s0 + 4 + n > len(b):
        return ""
    return b[s0 + 4 : s0 + 4 + n].decode("utf-8", errors="replace")


def _parse_table(blob: bytes) -> tuple[int, list[int]]:
    """Return (table_start, field_offsets[]) for a FlatBuffers table."""

    if len(blob) < 8:
        raise ValueError("blob too small")

    table_start = _u32(blob, 0)
    if table_start >= len(blob):
        raise ValueError("invalid root/table_start")

    vtable_off = _i32(blob, table_start)
    vtable_start = table_start - vtable_off
    if vtable_start < 0 or vtable_start + 4 > len(blob):
        raise ValueError("invalid vtable_start")

    vtable_len = _u16(blob, vtable_start)
    if vtable_start + vtable_len > len(blob):
        raise ValueError("invalid vtable_len")

    field_count = (vtable_len - 4) // 2
    offs = [_u16(blob, vtable_start + 4 + i * 2) for i in range(field_count)]
    return table_start, offs


def _get_i32(
    blob: bytes, table_start: int, offs: Sequence[int], idx: int, default: int = 0
) -> int:
    if idx >= len(offs):
        return default
    off = offs[idx]
    if off == 0:
        return default
    return _i32(blob, table_start + off)


def _get_str(
    blob: bytes, table_start: int, offs: Sequence[int], idx: int, default: str = ""
) -> str:
    if idx >= len(offs):
        return default
    off = offs[idx]
    if off == 0:
        return default
    return _read_string(blob, table_start, off)
