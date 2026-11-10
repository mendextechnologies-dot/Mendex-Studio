# Versioned framework configuration

Built-in tool definitions and engineering check definitions ship inside `src/mendex_core/config/` so they work from both editable source and an installed wheel. Schemas live in contracts/.

For a local discovery extension, create `<data-root>/.mendex/plugins/`, copy and adapt `templates/plugins/example-discovery.json`, then restart Studio. Only JSON data is accepted. Every plugin reports its ID, version and content hash. Invalid or conflicting manifests are rejected atomically and remain visible in Knowledge Center / Plugins. Plugins cannot add solver execution, approve results or execute Python code.

Native tool locations and versions do not imply qualification. The registry's engineering rules describe required evidence; they contain no invented numerical safety thresholds. Physical verification remains outstanding until genuinely supplied.
