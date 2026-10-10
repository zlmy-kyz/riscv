"""Check local Markdown links to documentation after moving files."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
files = [ROOT / "README.md", ROOT / "AGENTS.md", *((ROOT / "doc").rglob("*.md"))]
for base in ("tests", "sim", "tools", "MyCpu_test"):
    files += [p for p in (ROOT / base).rglob("*.md") if "build" not in p.parts]
pattern = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
broken = []
for file in files:
    for lineno, line in enumerate(file.read_text(encoding="utf-8-sig").splitlines(), 1):
        for match in pattern.finditer(line):
            raw = match.group(1).split("#", 1)[0]
            if not raw or re.match(r"[a-z]+://|mailto:", raw, re.I):
                continue
            if raw.startswith("/D:/riscv/RISCV/"):
                target = ROOT / raw.removeprefix("/D:/riscv/RISCV/")
            elif raw.startswith("D:/riscv/RISCV/"):
                target = ROOT / raw.removeprefix("D:/riscv/RISCV/")
            elif raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
                continue
            else:
                target = file.parent / raw
            if not target.exists():
                broken.append((file.relative_to(ROOT), lineno, raw))
for file, lineno, target in broken:
    print(f"{file}:{lineno}: {target}")
print(f"Checked {len(files)} Markdown files; broken links: {len(broken)}")
