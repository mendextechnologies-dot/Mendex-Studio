path = 'src/mendex_core/engineering_reviews/service.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = """def is_ephemeral_workspace_file(rel: str) -> bool:
    \"\"\"Returns True if the path is an ephemeral cache, auto-generated artifact,
    or interactive UI calculation that should not invalidate human review staleness.\"\"\"
    parts = rel.replace(\"\\\\\", \"/\").split(\"/\")
    ignored_dirs = {
        \".copper\",
        \"tests\",
        \"release_package\",
        \"node_modules\",
        \"__pycache__\",
        \".git\",
        \".pytest_cache\",
        \"scratch\",
        \"exports\",
        \"reports\",
        \"simulations\",
        \"gerbers\",
    }
    if any(p in ignored_dirs for p in parts):
        return True
    fname = parts[-1].lower()
    if (
        fname.endswith((\".lck\", \".tmp\", \".log\", \".raw\", \".ans\", \".db\", \".png\", \".jpg\", \".step\", \".drl\", \".gbr\", \".gbrjob\"))
        or fname.startswith(\"~\")
    ):
        return True
    if fname in (\"drc_report.json\", \"erc_report.json\", \"thermal_analysis.json\", \"wcca_analysis.json\"):
        return True
    return False"""

replacement = """def is_ephemeral_workspace_file(rel: str) -> bool:
    \"\"\"Returns True if the path is an ephemeral cache, auto-generated artifact,
    or interactive UI calculation that should not invalidate human review staleness.\"\"\"
    parts = rel.replace(\"\\\\\", \"/\").split(\"/\")
    ignored_dirs = {
        \".copper\",
        \"copper-out\",
        \"tests\",
        \"release_package\",
        \"node_modules\",
        \"__pycache__\",
        \".git\",
        \".pytest_cache\",
        \"scratch\",
        \"exports\",
        \"reports\",
        \"simulations\",
        \"gerbers\",
        \"svg\",
        \".history\",
    }
    if any(p in ignored_dirs for p in parts):
        return True
    fname = parts[-1].lower()
    if (
        fname.endswith((\".lck\", \".tmp\", \".log\", \".raw\", \".ans\", \".db\", \".png\", \".jpg\", \".svg\", \".step\", \".drl\", \".gbr\", \".gbrjob\", \".zip\", \".rpt\"))
        or fname.startswith(\"~\")
    ):
        return True
    if (
        fname in (\"drc_report.json\", \"erc_report.json\", \"thermal_analysis.json\", \"wcca_analysis.json\")
        or \"drc\" in fname
        or \"erc\" in fname
    ):
        return True
    return False"""

target_crlf = target.replace('\n', '\r\n')
replacement_crlf = replacement.replace('\n', '\r\n')

if target_crlf in text:
    text = text.replace(target_crlf, replacement_crlf, 1)
    print("Replaced with CRLF")
elif target in text:
    text = text.replace(target, replacement, 1)
    print("Replaced with LF")
else:
    print("No match found")

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Saved service.py")
