#!/usr/bin/env python3
"""Shared net parsing for both KiCad file dialects.

The generator writes KiCad 9 style, where every pad, track and via carries a
numeric net id plus a name, and the board declares a `(net N "name")` table.
KiCad 10 rewrites the file on save with names only and no table at all.

Every checker here matched the numeric form, so the moment a board had been
through KiCad they parsed *nothing* -- and a checker that finds no copper
reports no violations. Nets are therefore identified by name, with ids handed
out on demand so existing numeric code keeps working.
"""
from __future__ import annotations

import re

# pads and vias: (net 5 "/STEP")  or  (net "/STEP")
PAD_NET_RE = re.compile(r'\(net\s+(?:(\d+)\s+)?"([^"]*)"\)')
# tracks: (net 5)  or  (net "/STEP")
SEG_NET_RE = re.compile(r'\(net\s+(?:(\d+)|"([^"]*)")\s*\)')


class NetTable:
    """Name <-> id map, seeded from the board's declaration if it has one."""

    def __init__(self, text: str) -> None:
        self.by_name: dict[str, int] = {}
        self.by_id: dict[int, str] = {}
        for m in re.finditer(r'^\t\(net\s+(\d+)\s+"([^"]*)"\)', text, re.M):
            nid, name = int(m.group(1)), m.group(2)
            self.by_name[name] = nid
            self.by_id[nid] = name
        self._next = max(self.by_id, default=0) + 1
        if not self.by_id:
            # KiCad 10 drops the net table and names nets inline. Ids then get
            # handed out on first sight, so a table built while scanning pads
            # numbered a net differently from one built while scanning tracks
            # — and any checker matching pads to tracks by id compared
            # unrelated nets. Seed every name up front, in sorted order, so all
            # tables built from the same file agree.
            for name in sorted(set(re.findall(r'\(net\s+"([^"]*)"\)', text))):
                self.id_of(name)

    def id_of(self, name: str) -> int:
        if name not in self.by_name:
            self.by_name[name] = self._next
            self.by_id[self._next] = name
            self._next += 1
        return self.by_name[name]

    def name_of(self, nid: int) -> str:
        return self.by_id.get(nid, "")

    def resolve(self, m: re.Match | None, numeric_first: bool = False) -> tuple[int, str]:
        """(id, name) for a matched net clause of either dialect."""
        if m is None:
            return 0, ""
        num, name = (m.group(1), m.group(2))
        if name:
            return self.id_of(name), name
        if num is not None:
            nid = int(num)
            return nid, self.name_of(nid)
        return 0, ""


def pad_net(chunk: str, table: NetTable) -> tuple[int, str]:
    return table.resolve(PAD_NET_RE.search(chunk))


def seg_net(chunk: str, table: NetTable) -> tuple[int, str]:
    m = SEG_NET_RE.search(chunk)
    if m is None:
        return 0, ""
    if m.group(2):
        return table.id_of(m.group(2)), m.group(2)
    nid = int(m.group(1))
    return nid, table.name_of(nid)
