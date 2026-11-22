param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$DesktopShortcut
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).Path.TrimEnd('\')
$python = Join-Path $workspace '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Use the existing Mendex project Python environment.' }
$hub = Join-Path $workspace 'Product Documents'
$marker = Join-Path $hub '.mendex-document-hub.json'
if ((Test-Path -LiteralPath $hub) -and -not (Test-Path -LiteralPath $marker) -and (Get-ChildItem -LiteralPath $hub -Force | Select-Object -First 1)) {
    throw 'Product Documents already exists without the generated-hub marker; existing documents were not changed.'
}

# Read authoritative identity and revision paths through the shared core only.
$reader = @'
import json, sys
from pathlib import Path
from mendex_core.service import StudioService
s = StudioService(Path(sys.argv[1]))
products = []
for p in s.list_products():
    revisions = s.list_revisions(p.product_id)
    products.append({"code": p.code, "name": p.name, "product_id": str(p.product_id),
        "active_revision_id": str(p.active_revision_id), "revisions": [
        {"id": str(r.revision_id), "label": r.revision_label, "state": str(r.lifecycle_status),
         "path": str(s.workspace_path(r))} for r in revisions]})
print(json.dumps(products, ensure_ascii=True))
'@
$payload = $reader | & $python - $workspace
if ($LASTEXITCODE -ne 0) { throw 'Core product discovery failed; no document hub was generated.' }
$products = ConvertFrom-Json -InputObject ($payload -join "`n")
$previous = if (Test-Path -LiteralPath $marker) { Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json } else { $null }
if ($previous -and $previous.workspace -ne $workspace) { throw 'Hub belongs to a different data root.' }
New-Item -ItemType Directory -Path $hub -Force | Out-Null
if (-not (Test-Path -LiteralPath $marker)) {
    [pscustomobject]@{format_version='1.0';workspace=$workspace;products=@();links=@();state='INITIALIZING'} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $marker -Encoding UTF8
}
$shell = New-Object -ComObject WScript.Shell
$links = [Collections.Generic.List[object]]::new()
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'

function New-HubLink([string]$Path, [string]$Target, [string]$Description) {
    $resolved = (Resolve-Path -LiteralPath $Target).Path
    $shortcut = $shell.CreateShortcut($Path)
    if (Test-Path -LiteralPath $Path) {
        if ($shortcut.TargetPath.TrimEnd('\') -ne $resolved.TrimEnd('\')) {
            throw "Existing shortcut has another target; preserved: $Path"
        }
    } else {
        $shortcut.TargetPath = $resolved
        $shortcut.WorkingDirectory = $resolved
        $shortcut.Description = $Description
        $shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,3"
        $shortcut.Save()
    }
    $links.Add([pscustomobject]@{path=$Path;target=$resolved})
}

function Write-HubGuide([string]$Path, [string]$Body) {
    $banner = 'MENDEX PRODUCT DOCUMENT HUB - GENERATED GUIDE'
    if ((Test-Path -LiteralPath $Path) -and -not ((Get-Content -LiteralPath $Path -TotalCount 1) -eq $banner)) {
        throw "User-authored guide already exists; preserved: $Path"
    }
    ($banner + "`r`nUpdated: $stamp`r`n`r`n" + $Body) | Set-Content -LiteralPath $Path -Encoding UTF8
}

# Folder names stay readable; identity remains the core UUID, never inferred from a filename.
$folders = @{}
$productRecords = [Collections.Generic.List[object]]::new()
$previousProducts = if ($previous -and $previous.products.value) { $previous.products.value } elseif ($previous) { $previous.products } else { @() }
foreach ($product in $products) {
    $productRecords.Add($product)
    $name = $product.code
    if ($name -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$' -or $name -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$') {
        $name = 'Product-' + $product.product_id
    }
    if ($folders.ContainsKey($name.ToLowerInvariant())) { throw 'Product code folder collision.' }
    $folders[$name.ToLowerInvariant()] = $product.product_id
    $productFolder = Join-Path $hub $name
    if ($previous) {
        $prior = @($previousProducts | Where-Object code -eq $product.code)
        if ($prior.Count -gt 0 -and $prior[0].product_id -ne $product.product_id) { throw 'Product identity changed; preserve the existing hub and review manually.' }
    }
    foreach ($sub in @('', '00_Inbox', '01_Customer_and_Project_Documents', '02_Revision_Files', '03_Customer_Deliverables')) {
        New-Item -ItemType Directory -Path (Join-Path $productFolder $sub) -Force | Out-Null
    }
    $revisionNotes = @()
    foreach ($revision in $product.revisions) {
        if ($revision.label -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$') { throw 'Revision label is unsafe for a navigation folder.' }
        $revisionFolder = Join-Path (Join-Path $productFolder '02_Revision_Files') $revision.label
        New-Item -ItemType Directory -Path $revisionFolder -Force | Out-Null
        $native = [IO.Path]::GetFullPath($revision.path)
        if (-not $native.StartsWith(($workspace + '\products\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Core revision path is outside product storage.' }
        if (Test-Path -LiteralPath $native -PathType Container) {
            New-HubLink (Join-Path $revisionFolder '00_Open_Revision_Files.lnk') $native 'Managed revision files; check editability in Mendex first.'
            $categories = [ordered]@{
                '01_Requirements'='requirements'; '02_Calculations'='calculations'; '03_Circuit'='circuit';
                '04_PCB'='pcb'; '05_Magnetics'='magnetics'; '06_Mechanical'='mechanical';
                '07_Bill_of_Materials'='bom'; '08_Simulations'='simulations'; '09_Test_Plans'='tests';
                '10_Measurements'='measurements'; '11_Verification'='validation'; '12_Reports'='reports';
                '13_Assembly'='assembly'; '14_Package_Candidates'='release_package'
            }
            foreach ($entry in $categories.GetEnumerator()) {
                $target = Join-Path $native $entry.Value
                if (Test-Path -LiteralPath $target -PathType Container) {
                    New-HubLink (Join-Path $revisionFolder ($entry.Key + '.lnk')) $target 'Navigation only; folder presence is not evidence of approval.'
                }
            }
        }
        $active = if ($revision.id -eq $product.active_revision_id) { ' (active when this guide was refreshed)' } else { '' }
        $revisionNotes += "$($revision.label): $($revision.state)$active; $native"
        Write-HubGuide (Join-Path $revisionFolder 'READ_ME.txt') @"
Product: $($product.code) - $($product.name)
Revision: $($revision.label)
State at refresh: $($revision.state)
Managed revision ID: $($revision.id)

The numbered items are shortcuts to original files, not copied working folders.
Do not save documents beside these shortcuts: use the product Inbox or the editable
revision through Mendex. Do not modify archived revisions or raw evidence.
State is a snapshot. Confirm the current state in Mendex before editing.
Missing categories are not created in managed storage merely to fill the menu.
Calculated records may live in Mendex's database rather than a calculations folder.
Package candidates and folder names never establish engineering/manufacturing approval.
"@
    }
    Write-HubGuide (Join-Path $productFolder 'READ_ME.txt') @"
Product: $($product.code) - $($product.name)
Product ID: $($product.product_id)

00_Inbox: new, unclassified customer files, drawings and datasheets. Start here.
01_Customer_and_Project_Documents: correspondence, quotations, schedules and project administration.
02_Revision_Files: numbered shortcuts into Mendex-managed requirements, designs,
    simulations, BOM, test evidence and reports. Use Mendex for revision-controlled work.
03_Customer_Deliverables: deliberately exported copies for sharing, grouped by revision
    and issue date. These copies do not replace the managed originals or imply approval.

Use product-code + revision + document type + document version + date for named documents.
Example pattern: CODE_R002_Requirements_v01_YYYY-MM-DD.docx
Use the actual revision. Do not call a draft 'approved' or create 'final_final' copies.
When Inbox material becomes an engineering input, import/register it through Mendex.
Keep the original filename/source and checksum for incoming evidence.

Revision snapshot:
$($revisionNotes -join "`r`n")

After creating products/revisions, run scripts\sync_product_document_hub.ps1 again.
This updates navigation only; it does not migrate, move or edit product data.
"@
}

$references = Join-Path $workspace 'Engineering References'
if (Test-Path -LiteralPath $references -PathType Container) {
    New-HubLink (Join-Path $hub '90_Engineering_References.lnk') $references 'Consolidated reference and previous product material; not an engineering approval.'
}
Write-HubGuide (Join-Path $hub 'START_HERE.txt') @"
ONE DAILY STARTING POINT: $hub

Choose your product-code folder. Put incoming product files in its 00_Inbox.
Use its 02_Revision_Files links for existing engineering documents.

Existing products:
$(($products | ForEach-Object { $_.code + ' - ' + $_.name }) -join "`r`n")

APPLICATION: $workspace
PRODUCT DOCUMENTS: this hub
MANAGED ENGINEERING DATA: $workspace\products (internal IDs; do not rename)
APP DOCUMENTATION: $workspace\docs (software instructions, not product specifications)
ENGINEERING REFERENCES: $references (consolidated reference and previous product material)
OLD WORKSPACES: $workspace\.mendex-archives (recovery only, not daily work)

This hub is a navigation/intake standard, not a second engineering database.
Do not move or rename managed product/revision folders. Use the Mendex app for edits,
new revisions, evidence registration and controlled exports. Archived baselines stay intact.
Shortcuts are not read-only access controls. Check editability in Mendex before editing.
Refresh this hub after product/revision changes using:
  powershell -File "$workspace\scripts\sync_product_document_hub.ps1"
"@
if ($DesktopShortcut) {
    $desktop = [Environment]::GetFolderPath('DesktopDirectory')
    New-HubLink (Join-Path $desktop 'Mendex Products.lnk') $hub 'Start here for product documents, incoming files and revision navigation.'
}
[pscustomobject]@{format_version='1.0';workspace=$workspace;updated=$stamp;products=@($productRecords.ToArray());links=@($links.ToArray())} |
    ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $marker -Encoding UTF8
Write-Output "Product Documents hub refreshed: $hub"
Write-Output "Products: $($products.Count); verified shortcut targets: $($links.Count)"
