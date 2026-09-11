"""Render REPORT.md to a submission-ready PDF.

    .venv/Scripts/python.exe scripts/build_report_pdf.py

Markdown -> styled HTML (figures inlined as base64 so the file is portable)
-> headless Chrome --print-to-pdf. Chrome is used because it is already on the
machine, renders the rupee glyph correctly, and gives real control over page
breaks; there is no LaTeX or pandoc dependency.
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "REPORT.md"
BUILD = ROOT / "build"
HTML_OUT = BUILD / "report.html"
PDF_OUT = BUILD / "Parametric_Solar_Cover_380006.pdf"

BROWSERS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]

CSS = """
@page { size: A4; margin: 15mm 14mm 15mm 14mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Nirmala UI", system-ui, sans-serif;
  font-size: 9.6pt; line-height: 1.42; color: #1f2933; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 17pt; line-height: 1.2; margin: 0 0 2px; letter-spacing: -0.2px; }
h2 {
  font-size: 12.2pt; margin: 17px 0 7px; padding-top: 7px;
  border-top: 2px solid #1f2933; break-after: avoid;
}
h3 { font-size: 10.4pt; margin: 13px 0 5px; color: #2f6f9f; break-after: avoid; }
h1 + p { color: #52606d; font-size: 9pt; margin: 0 0 4px; }
p { margin: 0 0 7px; }
hr { display: none; }
strong { font-weight: 600; }
a { color: #2f6f9f; text-decoration: none; }
code {
  font-family: Consolas, "Courier New", monospace; font-size: 8.6pt;
  background: #f0f3f6; padding: 0.5px 3px; border-radius: 2px;
}

table {
  border-collapse: collapse; width: 100%; margin: 8px 0 11px;
  font-size: 8.7pt; break-inside: avoid;
}
th, td { border-bottom: 1px solid #dde3e9; padding: 3.6px 6px; text-align: left; }
th {
  background: #eef2f6; border-bottom: 1.5px solid #b8c2cc;
  font-weight: 600; font-size: 8.4pt;
}
/* alignment is assigned per column by build_report_pdf.py, not by position */
td.num, th.num { text-align: right; }
tr:last-child td { border-bottom: 1.5px solid #b8c2cc; }
table td:empty { border-bottom: none; }
table.long { break-inside: auto; }
table.long tr { break-inside: avoid; }

img { width: 100%; max-width: 510px; display: block; margin: 9px auto 3px; }
figure { break-inside: avoid; margin: 0; }
figure em {
  display: block; text-align: center; font-size: 8.2pt;
  color: #52606d; margin: 0 auto 11px; max-width: 510px; line-height: 1.35;
}

ul { margin: 0 0 7px; padding-left: 17px; }
li { margin-bottom: 2px; }
h2, h3 { break-inside: avoid; }
"""


def inline_images(html: str) -> str:
    """Replace figure src paths with base64 data URIs."""

    def repl(match: re.Match) -> str:
        src = match.group(1)
        path = ROOT / src
        if not path.exists():
            print(f"  ! missing figure: {src}", file=sys.stderr)
            return match.group(0)
        b64 = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:image/png;base64,{b64}"'

    return re.sub(r'src="([^"]+\.png)"', repl, html)


CELL_RE = re.compile(r"<(t[hd])([^>]*)>(.*?)</\1>", re.DOTALL)
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
NUMERIC_RE = re.compile(r"^[₹\d\s.,%+\-–→×()=<>a-z]*\d[^A-Za-z]*$")


def align_table_columns(html: str) -> str:
    """Right-align only columns whose data cells are actually numeric.

    Positional CSS ("every column but the first") wrecks two-column definition
    tables, of which this report has several.
    """

    def fix_table(match: re.Match) -> str:
        table = match.group(0)
        rows = [CELL_RE.findall(r) for r in ROW_RE.findall(table)]
        body = [r for r in rows if r and r[0][0] == "td"]
        if not body:
            return table

        width = max(len(r) for r in rows)
        numeric = []
        for col in range(width):
            vals = [TAG_RE.sub("", r[col][2]).strip() for r in body if len(r) > col]
            vals = [v for v in vals if v]
            numeric.append(
                bool(vals) and sum(bool(NUMERIC_RE.match(v)) for v in vals) >= 0.6 * len(vals)
            )

        def rewrite_row(row_match: re.Match) -> str:
            col = -1

            def rewrite_cell(cell: re.Match) -> str:
                nonlocal col
                col += 1
                cls = ' class="num"' if col < width and numeric[col] else ""
                return f"<{cell.group(1)}{cell.group(2)}{cls}>{cell.group(3)}</{cell.group(1)}>"

            return "<tr>" + CELL_RE.sub(rewrite_cell, row_match.group(1)) + "</tr>"

        table = ROW_RE.sub(rewrite_row, table)
        if len(body) > 8:
            table = table.replace("<table>", '<table class="long">', 1)
        return table

    return re.sub(r"<table>.*?</table>", fix_table, html, flags=re.DOTALL)


def find_browser() -> Path:
    for path in BROWSERS:
        if path.exists():
            return path
    found = shutil.which("chrome") or shutil.which("msedge")
    if found:
        return Path(found)
    raise SystemExit("No Chrome or Edge found to render the PDF.")


def main() -> None:
    BUILD.mkdir(exist_ok=True)

    body = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"),
        extensions=["tables", "attr_list", "sane_lists"],
    )
    # keep each figure with its caption on one page
    body = re.sub(
        r"(<p><img[^>]+></p>)\s*(<p><em>.*?</em></p>)",
        r"<figure>\1\2</figure>",
        body,
        flags=re.DOTALL,
    )
    body = align_table_columns(body)
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Parametric Cover for Rooftop Solar Generation Shortfall</title>"
        f"<style>{CSS}</style></head><body>{inline_images(body)}</body></html>"
    )
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"HTML  -> {HTML_OUT}  ({len(html)/1_000_000:.1f} MB)")

    browser = find_browser()
    PDF_OUT.unlink(missing_ok=True)
    subprocess.run(
        [
            str(browser), "--headless=new", "--disable-gpu",
            "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000",
            f"--print-to-pdf={PDF_OUT}", HTML_OUT.as_uri(),
        ],
        check=True, capture_output=True, timeout=180,
    )
    if not PDF_OUT.exists():
        raise SystemExit("Chrome ran but produced no PDF.")
    print(f"PDF   -> {PDF_OUT}  ({PDF_OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
