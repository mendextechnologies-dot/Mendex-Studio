"""Build styled Word document (.docx) from docs/MENDEX_PRODUCT_DESIGN_HANDBOOK.md."""
import os
import re
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

MD_PATH = r"docs\MENDEX_PRODUCT_DESIGN_HANDBOOK.md"
DOCX_OUT_PATH = r"docs\Mendex_Product_Design_Handbook.docx"
ARTIFACT_DIR = r"C:\Users\Sagar\.gemini\antigravity\brain\0a1dae9f-d647-4c88-987e-ccfaaa950d01"

NAVY_BLUE = RGBColor(0x1E, 0x3A, 0x8A)
ROYAL_BLUE = RGBColor(0x25, 0x63, 0xEB)
SLATE_DARK = RGBColor(0x0F, 0x17, 0x2A)
TEXT_DARK = RGBColor(0x33, 0x41, 0x55)
MUTED_GRAY = RGBColor(0x64, 0x74, 0x8B)


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>'
    )
    tcPr.append(tcMar)


def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}><w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/><w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/><w:left w:val="none"/><w:right w:val="none"/><w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/><w:insideV w:val="none"/></w:tblBorders>'
    )
    tblPr.append(borders)


def add_code_block(doc, code_text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F8FAFC")
    set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:left w:val="single" w:sz="24" w:space="0" w:color="2563EB"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:right w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/></w:tcBorders>'
    )
    tcPr.append(borders)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(code_text.strip())
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(4)


def add_formatted_text(p, text, font_name="Segoe UI", font_size=10.0, color=TEXT_DARK, bold=False, italic=False):
    # Parses inline markdown **bold**, *italic*, `code`, math $...$
    pattern = re.compile(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\$.*?\$|[^\*`\$]+)')
    for part in pattern.findall(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = p.add_run(part[2:-2])
            run.font.bold = True
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.color.rgb = color
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = p.add_run(part[1:-1])
            run.font.italic = True
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.color.rgb = color
        elif part.startswith("`") and part.endswith("`"):
            run = p.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(font_size * 0.92)
            run.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)
            run.font.bold = True
        elif part.startswith("$") and part.endswith("$") and len(part) > 1:
            clean_math = part[1:-1].replace(r"\text{", "").replace(r"}", "").replace(r"\approx", "≈").replace(r"\le", "≤").replace(r"\ge", "≥").replace(r"\times", "×").replace(r"\mu", "µ").replace(r"\cdot", "·").replace(r"\Delta", "Δ")
            run = p.add_run(clean_math)
            run.font.italic = True
            run.font.name = "Cambria Math"
            run.font.size = Pt(font_size * 0.98)
            run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
        else:
            run = p.add_run(part)
            run.font.name = font_name
            run.font.size = Pt(font_size)
            run.font.color.rgb = color
            run.font.bold = bold
            run.font.italic = italic


def build_docx():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f]

    doc = docx.Document()

    # Configure Margins: 1 inch (72 pt) all around
    sections = doc.sections
    for sec in sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Document Header / Banner
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("MENDEX ENGINEERING STUDIO v3.1")
    run_title.font.name = "Segoe UI"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = NAVY_BLUE

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    run_sub = p_sub.add_run("The Complete End-to-End Product Design Handbook\nAutonomous Power Electronics Engineering with Codex, Open-Source Solvers & React Command Center")
    run_sub.font.name = "Segoe UI"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = ROYAL_BLUE

    # Meta card / Callout
    tbl_meta = doc.add_table(rows=1, cols=1)
    tbl_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_meta = tbl_meta.cell(0, 0)
    cell_meta.width = Inches(6.5)
    set_cell_background(cell_meta, "F1F5F9")
    set_cell_margins(cell_meta, top=100, bottom=100, left=150, right=150)
    tcPr = cell_meta._tc.get_or_add_tcPr()
    borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="none"/><w:left w:val="single" w:sz="24" w:space="0" w:color="1E3A8A"/><w:bottom w:val="none"/><w:right w:val="none"/></w:tcBorders>')
    tcPr.append(borders)
    p_meta = cell_meta.paragraphs[0]
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(0)
    p_meta.paragraph_format.line_spacing = 1.15
    add_formatted_text(p_meta, "**Version**: 3.1.0 · **Target Architecture**: Codex-First Engineering Architecture · **Command Center**: `http://localhost:5173`\n**Authoritative Core**: Python Mendex Engineering Core (`src/mendex_core/`) · **Open Solvers**: LTspice XVII, FEMM 4.2, KiCad 10, FreeCAD", font_size=9.5)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(6)
    p_spacer.paragraph_format.space_after = Pt(6)

    # State Machine for Parsing Markdown Lines
    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        # Parse table rows into cell text
        parsed_rows = []
        for r_str in table_rows:
            # Skip separator row like |---|---|
            if re.match(r'^\s*\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)+\|?\s*$', r_str):
                continue
            cells = [c.strip() for c in r_str.strip().strip('|').split('|')]
            if cells:
                parsed_rows.append(cells)
        if parsed_rows:
            num_cols = max(len(r) for r in parsed_rows)
            tbl = doc.add_table(rows=len(parsed_rows), cols=num_cols)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            set_table_borders(tbl)
            for row_idx, r_cells in enumerate(parsed_rows):
                is_header = (row_idx == 0)
                row = tbl.rows[row_idx]
                for col_idx in range(num_cols):
                    cell = row.cells[col_idx]
                    val = r_cells[col_idx] if col_idx < len(r_cells) else ""
                    set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
                    if is_header:
                        set_cell_background(cell, "1E3A8A")
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(0)
                        add_formatted_text(p, val, font_size=9.0, color=RGBColor(0xFF, 0xFF, 0xFF), bold=True)
                    else:
                        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
                        set_cell_background(cell, bg_color)
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(0)
                        add_formatted_text(p, val, font_size=8.5, color=TEXT_DARK)
            p_sp = doc.add_paragraph()
            p_sp.paragraph_format.space_before = Pt(0)
            p_sp.paragraph_format.space_after = Pt(4)
        table_rows = []
        in_table = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check Code Block Toggle
        if line.startswith("```"):
            if in_code_block:
                add_code_block(doc, "\n".join(code_lines))
                code_lines = []
                in_code_block = False
            else:
                if in_table:
                    flush_table()
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Check Table Line
        if line.strip().startswith("|") and line.strip().endswith("|"):
            in_table = True
            table_rows.append(line)
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        # Check Headings
        if line.startswith("# "):
            # Skip primary title since we already made an executive banner
            if i > 2:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(16)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.keep_with_next = True
                run = p.add_run(line[2:].strip())
                run.font.name = "Segoe UI"
                run.font.size = Pt(18)
                run.font.bold = True
                run.font.color.rgb = NAVY_BLUE
            i += 1
            continue
        elif line.startswith("## "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[3:].strip())
            run.font.name = "Segoe UI"
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = ROYAL_BLUE
            i += 1
            continue
        elif line.startswith("### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[4:].strip())
            run.font.name = "Segoe UI"
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = SLATE_DARK
            i += 1
            continue
        elif line.startswith("#### "):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[5:].strip())
            run.font.name = "Segoe UI"
            run.font.size = Pt(10.5)
            run.font.bold = True
            run.font.color.rgb = ROYAL_BLUE
            i += 1
            continue

        # Check Horizontal Rule
        if line.strip() in ("---", "***", "___"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            pPr = p._p.get_or_add_pPr()
            pbdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="CBD5E1"/></w:pBdr>')
            pPr.append(pbdr)
            i += 1
            continue

        # Check Bullet Lists
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            content = line.strip()[2:]
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_text(p, content, font_size=10.0)
            i += 1
            continue

        # Check Numbered Lists (e.g. 1. )
        m_num = re.match(r'^\s*(\d+)\.\s+(.*)$', line)
        if m_num:
            num = m_num.group(1)
            content = m_num.group(2)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            r_num = p.add_run(f"{num}. ")
            r_num.font.bold = True
            r_num.font.color.rgb = ROYAL_BLUE
            add_formatted_text(p, content, font_size=10.0)
            i += 1
            continue

        # Regular Paragraph
        if line.strip():
            # Check for LaTeX display math on standalone line $$...$$
            if line.strip().startswith("$$") and line.strip().endswith("$$") and len(line.strip()) > 4:
                math_text = line.strip()[2:-2].strip().replace(r"\text{", "").replace(r"}", "").replace(r"\approx", "≈").replace(r"\le", "≤").replace(r"\ge", "≥").replace(r"\times", "×").replace(r"\mu", "µ").replace(r"\cdot", "·").replace(r"\Delta", "Δ")
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(math_text)
                run.font.name = "Cambria Math"
                run.font.size = Pt(11.0)
                run.font.italic = True
                run.font.color.rgb = NAVY_BLUE
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.line_spacing = 1.15
                add_formatted_text(p, line, font_size=10.0)

        i += 1

    if in_table:
        flush_table()

    # Save to target file
    doc.save(DOCX_OUT_PATH)
    print(f"Successfully generated: {DOCX_OUT_PATH}")

    # Copy to Artifact directory
    if os.path.isdir(ARTIFACT_DIR):
        artifact_dest = os.path.join(ARTIFACT_DIR, "Mendex_Product_Design_Handbook.docx")
        shutil.copy2(DOCX_OUT_PATH, artifact_dest)
        print(f"Copied to Artifacts: {artifact_dest}")


if __name__ == "__main__":
    build_docx()
