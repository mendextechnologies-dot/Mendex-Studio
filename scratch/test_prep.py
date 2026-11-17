from pathlib import Path
from src.mendex_core.service import StudioService
studio = StudioService(Path.cwd())
rid = '9b7c1396-64da-41f8-8649-77dc0f24e103'
pkg = studio.reviews.prepare_package(rid, 'verification')
print('Stage:', pkg.get('stage', {}).get('stage_id'), pkg.get('stage', {}).get('attempt'))
print('Safety items:', len(pkg.get('safety_items', [])))
print('Requirements digest:', pkg.get('requirements_package', {}).get('digest'))
print('Spec hash:', pkg.get('revision', {}).get('specification_hash'))
print('Doc count:', len(pkg.get('document_hashes', {})))
print('Evidence count:', len(pkg.get('evidence_hashes', {})))
