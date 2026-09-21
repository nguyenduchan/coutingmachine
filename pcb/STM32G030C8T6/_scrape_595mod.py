#!/usr/bin/env python3
"""Scrape thegioimodule 74HC595-24 IO product for images/pin text."""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "_595mod_scrape"
OUT.mkdir(exist_ok=True)

u = "https://thegioimodule.com/mach-mo-rong-i-o-24-chan-74hc595"
req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    t = r.read().decode("utf-8", "replace")

(OUT / "page.html").write_text(t, encoding="utf-8")

imgs = re.findall(r'(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']', t)
imgs = [i for i in imgs if any(x in i.lower() for x in ("upload", "product", "595", "wp-content"))]
print("images:", len(imgs))
for i, url in enumerate(dict.fromkeys(imgs)):
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = "https://thegioimodule.com" + url
    print(i, url)
    try:
        req2 = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=30) as r2:
            data = r2.read()
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".webp" in url.lower():
            ext = ".webp"
        p = OUT / f"img_{i}{ext}"
        p.write_bytes(data)
        print("  saved", p, len(data))
    except Exception as e:
        print("  fail", e)

# strip tags snippets
plain = re.sub(r"<script[\s\S]*?</script>", " ", t, flags=re.I)
plain = re.sub(r"<style[\s\S]*?</style>", " ", plain, flags=re.I)
plain = re.sub(r"<[^>]+>", " ", plain)
plain = re.sub(r"\s+", " ", plain)
(OUT / "plain.txt").write_text(plain, encoding="utf-8")
for key in ("DS", "SH_CP", "ST_CP", "OE", "kích thước", "mm", "VCC", "GND"):
    idx = plain.lower().find(key.lower())
    if idx >= 0:
        print("---", key, "---")
        print(plain[max(0, idx - 100) : idx + 200])
