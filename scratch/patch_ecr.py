from pathlib import Path

p = Path('src/mendex_core/lifecycle/ecr.py')
text = p.read_text(encoding='utf-8')

target = """        if not ecr.schematic_ops:
            raise ValueError(f"ECR {ecr.ecr_number} has no schematic operations defined")"""

replacement = """        if not ecr.schematic_ops:
            return {
                "success": False,
                "ecr_id": str(ecr.ecr_id),
                "ecr_number": ecr.ecr_number,
                "error": (
                    f"ECR {ecr.ecr_number} has no schematic operations defined. "
                    "For administrative, documentation, or manual hardware changes, "
                    "complete sign-off via 'Review / Sign-off'."
                ),
                "ops_applied": 0,
            }"""

text_norm = text.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in text_norm:
    new_text = text_norm.replace(target_norm, replacement_norm)
    p.write_text(new_text, encoding='utf-8')
    print('Successfully patched src/mendex_core/lifecycle/ecr.py')
else:
    print('Target not found in ecr.py')
