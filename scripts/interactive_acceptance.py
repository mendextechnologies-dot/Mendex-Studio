"""Primary-workstation acceptance. Opens real windows; never runs engineering tools.

Run manually with --launch to check actual VS Code and Windows native handoff.
The script verifies matching top-level window titles, not engineering correctness.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import time
from pathlib import Path

from mendex_core.evidence import ManualCheck
from mendex_core.models import Specification
from mendex_core.service import StudioService


def window_titles(window_class=None):
    titles = []
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    @callback_type
    def callback(hwnd, parameter):
        if window_class:
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if class_name.value != window_class:
                return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            text = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, text, length + 1)
            titles.append(text.value)
        return True
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows(callback, 0)
    return titles


def wait_for_title(fragment, timeout=20, required_text=None, window_class=None):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        matches = [title for title in window_titles(window_class) if fragment.lower() in title.lower() and (required_text is None or required_text.lower() in title.lower())]
        if matches:
            return matches
        time.sleep(0.25)
    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch", action="store_true", required=True, help="Explicitly request real editor/File Explorer windows")
    args = parser.parse_args()
    root = Path(".mendex/qa/primary-acceptance").resolve()
    service = StudioService(root)
    code = f"ACCEPT-{int(time.time())}"
    product = service.create_product(code, "Mendex software acceptance fixture", "transformer", "Automated local acceptance (not an independent engineer)")
    service.update_specification(product.active_revision_id, Specification(vin_nom_v=24, source="Illustrative software fixture; not an approved engineering requirement"))
    revision = service.create_revision(product.product_id, "Mendex-v0-1-Acceptance")
    workspace = service.workspace_path(revision)
    fixture = workspace / "requirements" / f"Mendex-acceptance-{revision.revision_id.hex[:8]}.txt"
    fixture.write_text("Mendex software acceptance fixture only.\nNo actual measurement, simulation or approved design is represented.\n", encoding="utf-8")
    service.export_specification(revision.revision_id)
    editor_launch = service.open_in_vscode(revision.revision_id)
    editor_titles = wait_for_title(str(revision.revision_id), required_text="Visual Studio Code")
    service.open_project_file(revision.revision_id)
    explorer_titles = wait_for_title(str(revision.revision_id), window_class="CabinetWClass")
    service.open_project_file(revision.revision_id, str(fixture.relative_to(workspace)))
    document_titles = wait_for_title(fixture.stem)
    check = ManualCheck(check_id="DELIBERATE-SOFTWARE-FAILURE", status="fail", reviewer="Software acceptance script", notes="Numeric fixture only; no actual engineering value is asserted", evidence_kind="MANUAL", measured_value=30, unit="V", maximum=20)
    service.record_validation(revision.revision_id, check, fixture)
    report = service.generate_report(revision.revision_id)
    outcome = {"test_type": "PRIMARY_WORKSTATION_SOFTWARE_ACCEPTANCE", "product_id": str(product.product_id), "revision_id": str(revision.revision_id), "vscode_launch": editor_launch, "editor_window_observed": bool(editor_titles), "native_document_window_observed": bool(document_titles), "workspace_handoff_requested": True, "workspace_matching_window_observed": bool(explorer_titles), "diagnostics": service.diagnostics(), "effective_validation": [entry["effective_status"] for entry in service.validation_summary(revision.revision_id)], "report_path": report.report_path, "independent_engineer_acceptance": "NOT_PERFORMED"}
    destination = root / f"acceptance-{revision.revision_id}.json"
    destination.write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    print(json.dumps({"acceptance_record": str(destination), "editor_window_observed": bool(editor_titles), "native_document_window_observed": bool(document_titles)}, indent=2))
    if not editor_titles or not document_titles or not explorer_titles:
        raise SystemExit("A window was not observed; inspect the retained acceptance record. Do not mark the handoff verified.")


if __name__ == "__main__":
    main()
