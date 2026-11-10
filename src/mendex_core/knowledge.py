"""Versioned guidance shipped with the application; no calculation implementations."""

GUIDELINES_REVISION = "0.2"
GUIDELINES = [
    ("Specifications and provenance", "Use SI units. Record the requirement source and assumptions. Illustrative inputs are not approved designs."),
    ("Transformer and magnetics", "Collect core geometry, material datasheet and temperature range, winding construction, duty limits, insulation requirements and applicable standards before design execution."),
    ("DC–DC converters", "Record topology, control mode, input and load corners, switching frequency, ripple limits, efficiency targets and startup/stress acceptance criteria."),
    ("Power semiconductors", "MOSFET, IGBT and BJT review requires manufacturer datasheets, voltage/current/SOA limits, gate-drive conditions and justified thermal assumptions."),
    ("PCB review", "Preserve native board revision and ERC/DRC evidence. DRC does not establish HV insulation integrity or safety compliance."),
    ("Manual validation", "Values, criteria, reviewer identity and evidence origin are manually supplied and are not independently authenticated. A numerical PASS is not product approval. Missing or stale evidence is not evaluated."),
    ("Physical verification", "Simulation does not establish compliance, isolation integrity or suitability for high-voltage hardware. Qualified review, a separately authorized test plan and physical testing remain necessary."),
    ("Release boundary", "Manufacturing approval, automatic hardware control and certification are unavailable in v0.1. Preserve raw evidence and create a new revision when the design changes."),
]
