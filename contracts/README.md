# Application service contract v0.1

Canonical Pydantic models: `src/mendex_core/models.py`. Generated JSON schemas and an illustrative payload live here. UI and CLI use `StudioService(root)`.

Day 1 operations: create_product(code, name, category, owner, description), list_products(), get_product(id), get_revision(id), list_revisions(product_id), update_specification(revision_id, Specification), create_revision(product_id, label), create_workspace(revision_id), update_product(id, name, owner, description).

Errors: `StudioError.code` is INVALID_INPUT, NOT_FOUND, CONFLICT, IMMUTABLE or STORAGE_ERROR. Pydantic rejects unknown fields and non-finite quantities. Future operations from the guide are pending; they must not be advertised as implemented.
