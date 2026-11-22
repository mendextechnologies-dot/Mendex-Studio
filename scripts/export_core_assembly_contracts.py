"""Export/check additive mechanical-workflow contracts; preserve legacy schemas."""
import argparse
import json
from pathlib import Path
from mendex_core.core_assembly import AssemblyDimension, AssemblyPart, AssemblyIssue, AssemblyDesign, AssemblyWrite, AssemblyRevision, lifecycle_definition
from mendex_core.models import Specification


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    folder=Path(__file__).resolve().parents[1]/'contracts/core-assembly'
    payloads={model.__name__+'.schema.json':model.model_json_schema() for model in
        (AssemblyDimension,AssemblyPart,AssemblyIssue,AssemblyDesign,AssemblyWrite,AssemblyRevision,Specification)}
    payloads['lifecycle-1.0.0.json']=lifecycle_definition().model_dump(mode='json')
    for name,data in payloads.items():
        text=json.dumps(data,indent=2)+'\n'
        path=folder/name
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8')!=text:
                raise SystemExit('Contract differs: '+str(path))
        else:
            folder.mkdir(exist_ok=True)
            path.write_text(text,encoding='utf-8')
    print(('Verified' if args.check else 'Exported')+f' {len(payloads)} core assembly contracts')


if __name__=='__main__':main()
