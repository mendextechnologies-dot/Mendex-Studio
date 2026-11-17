import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from mendex_core.service import StudioService
from mendex_core.lifecycle.ecr import EngineeringChangeRequest, ECRStatus

studio = StudioService(Path('.').resolve())
ecr = studio.ecr.get_ecr('df07c7c4-683e-486c-aaeb-75853387655f')
print('Found ECR:', ecr.ecr_number, 'Status:', ecr.status)

# Test updating schematic_ops in memory
ecr.schematic_ops = [
    {"op": "set_field", "ref": "RGATE", "field": "Value", "value": "15R"},
    {"op": "set_field", "ref": "RSNUB", "field": "Value", "value": "47k 2W"}
]

with studio.connection() as db:
    db.execute(
        "UPDATE engineering_change_requests SET payload=? WHERE ecr_id=?",
        (ecr.model_dump_json(), str(ecr.ecr_id))
    )
print('Updated ECR with schematic_ops in database.')

# Test applying ECR
res = studio.ecr.apply_schematic_change(
    ecr_id=ecr.ecr_id,
    implemented_by="Lead Power Systems Engineer (Human Reviewer)",
    forward_annotate=True,
)
print('Apply result success:', res.get('success'))
print('Ops applied:', res.get('ops_applied'))
print('Status now:', res.get('status'))
print('Changed:', res.get('changed'))
print('Error if any:', res.get('error'))
