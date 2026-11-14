"""Draft BOM exports from explicit revision data; no example parts or approvals."""
from __future__ import annotations
import csv
import json
import logging
from pathlib import Path
import subprocess
from typing import Any
from uuid import UUID, uuid4
from .evidence import digest
from .service import StudioError
logger = logging.getLogger(__name__)


def build_bom_docx(output_path: Path, items: list[dict], project_code: str, project_name: str,
                   *, revision_id: str, source_sha256: str) -> Path:
    from docx import Document
    document = Document()
    document.add_heading(f"{project_code} ? Draft Bill of Materials", 0)
    document.add_paragraph(project_name)
    document.add_paragraph(f"Revision: {revision_id}")
    document.add_paragraph(f"Source bom.json SHA-256: {source_sha256}")
    document.add_paragraph("Engineering qualification: NOT_EVALUATED. This component list does not authorize procurement, assembly, safety compliance or manufacturing.")
    fields = [('designator','Designator'),('quantity','Quantity'),('description','Description'),
              ('manufacturer','Manufacturer'),('mpn','Part number'),('package','Package'),('source','Source')]
    table = document.add_table(rows=1, cols=len(fields))
    table.style = 'Table Grid'
    for cell, (_, label) in zip(table.rows[0].cells, fields): cell.text = label
    for item in items:
        for cell, (field, _) in zip(table.add_row().cells, fields):
            cell.text = str(item[field]) if item.get(field) not in (None, '') else 'Unknown'
    document.add_paragraph('Ratings, exact ordering codes, derating, footprints, source assertions and model compatibility require independent application review. No automatic verification or approval is asserted.')
    document.save(output_path)
    return output_path


def convert_docx_to_pdf_via_word_com(docx_path: Path, pdf_path: Path) -> bool:
    """Uses Microsoft Word COM automation via PowerShell to export DOCX to PDF."""
    abs_docx = str(docx_path.resolve()).replace("'", "''")
    abs_pdf = str(pdf_path.resolve()).replace("'", "''")

    ps_script = f"""
$docxPath = '{abs_docx}'
$pdfPath = '{abs_pdf}'
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open($docxPath)
    $wdExportFormatPDF = 17
    $doc.ExportAsFixedFormat($pdfPath, $wdExportFormatPDF)
    $doc.Close([ref]$false)
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    exit 0
}} catch {{
    Write-Error $_.Exception.Message
    if ($word) {{
        $word.Quit()
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    }}
    exit 1
}}
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return res.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:
        logger.warning("PowerShell Word COM PDF export failed: %s", exc)
        return False


def generate_bom_deliverables(studio, revision_id: UUID | str) -> dict[str, Any]:
    """Serialize revision freeze/export decisions; never rewrite baseline files."""
    with studio.atomic():
        return _generate_bom_deliverables(studio, revision_id)


def _generate_bom_deliverables(studio, revision_id: UUID | str) -> dict[str, Any]:
    rev_uuid = UUID(str(revision_id))
    rev = studio.get_revision(rev_uuid)
    if rev.lifecycle_status != "draft":
        raise StudioError("IMMUTABLE", "BOM export requires a draft revision; historical files are preserved")
    product = studio.get_product(rev.product_id)
    ws_dir = studio.workspace_path(rev)
    source_path = ws_dir / "bom" / "bom.json"
    if not source_path.resolve().is_relative_to(ws_dir) or not (ws_dir / "bom" / "exports").resolve().is_relative_to(ws_dir):
        raise StudioError("INVALID_INPUT", "BOM paths must remain inside the selected revision")
    try:
        if source_path.stat().st_size > 2 * 1024 * 1024:
            raise StudioError("INVALID_INPUT", "BOM source exceeds 2 MiB")
        source = source_path.read_bytes()
        items = json.loads(source)
    except (OSError, ValueError) as exc:
        raise StudioError("INVALID_INPUT", "Supply an explicit valid revision bom/bom.json; no example parts are assumed") from exc
    if (not isinstance(items, list) or not items or len(items) > 2000
            or any(not isinstance(item, dict) or not isinstance(item.get("designator"), str)
                   or not item["designator"].strip() or not isinstance(item.get("description"), str)
                   or not item["description"].strip() or type(item.get("quantity")) is not int
                   or item["quantity"] <= 0 for item in items)):
        raise StudioError("INVALID_INPUT", "BOM requires explicit designator, description and positive integer quantity for every item")
    # A fresh export preserves source JSON and all previously registered deliverables.
    bom_dir = ws_dir / "bom" / "exports" / uuid4().hex
    bom_dir.mkdir(parents=True, exist_ok=False)
    json_path = bom_dir / "bom.json"
    json_path.write_bytes(source)
    csv_path = bom_dir / "bom.csv"
    docx_path = bom_dir / "Bill_of_Materials.docx"
    pdf_path = bom_dir / "Bill_of_Materials.pdf"

    # 2. Write CSV if not present or update
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Item", "Designator", "Qty", "Description", "Manufacturer", "MPN", "Package", "Voltage_Rating", "Current_Rating", "Primary_Side"])
        for idx, item in enumerate(items, start=1):
            writer.writerow([
                idx,
                item.get("designator", ""),
                item.get("quantity", 1),
                item.get("description", ""),
                item.get("manufacturer", ""),
                item.get("mpn", ""),
                item.get("package", ""),
                item.get("voltage_rating", ""),
                item.get("current_rating", ""),
                item.get("primary_side", ""),
            ])

    # 3. Build Word document
    build_bom_docx(docx_path, items, project_code=product.code, project_name=product.name,
                   revision_id=str(rev_uuid), source_sha256=digest(source))

    # 4. Export PDF via Word COM
    pdf_success = convert_docx_to_pdf_via_word_com(docx_path, pdf_path)

    # 5. Measure files & hashes
    docx_size = docx_path.stat().st_size if docx_path.exists() else 0
    pdf_size = pdf_path.stat().st_size if pdf_path.exists() else 0

    rel_docx = docx_path.relative_to(ws_dir).as_posix()
    rel_pdf = pdf_path.relative_to(ws_dir).as_posix()
    rel_csv = csv_path.relative_to(ws_dir).as_posix()
    rel_json = json_path.relative_to(ws_dir).as_posix()

    return {
        "success": True,
        "docx_path": rel_docx,
        "pdf_path": rel_pdf if pdf_success else None,
        "engineering_status": "NOT_EVALUATED",
        "source_sha256": digest(source),
        "csv_path": rel_csv,
        "json_path": rel_json,
        "pdf_available": pdf_success,
        "items_count": len(items),
        "docx_size_bytes": docx_size,
        "pdf_size_bytes": pdf_size,
        "message": f"Exported draft BOM with {len(items)} supplied items. PDF {'available' if pdf_success else 'unavailable'}. Engineering qualification NOT_EVALUATED.",
    }
