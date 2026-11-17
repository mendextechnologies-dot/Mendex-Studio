from pathlib import Path

p = Path('desktop/src/api/client.ts')
text = p.read_text(encoding='utf-8')

target = """  reviewECR: (params: {
    ecr_id: string;
    reviewer: string;
    status: 'APPROVED' | 'REJECTED' | 'UNDER_REVIEW' | 'DRAFT';
    review_notes?: string;
  }) => rpcCall<any>('review_ecr', params),"""

replacement = """  reviewECR: (params: {
    ecr_id: string;
    reviewer: string;
    status: 'APPROVED' | 'REJECTED' | 'UNDER_REVIEW' | 'DRAFT' | 'IMPLEMENTED';
    review_notes?: string;
  }) => rpcCall<any>('review_ecr', params),"""

text_norm = text.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in text_norm:
    new_text = text_norm.replace(target_norm, replacement_norm)
    p.write_text(new_text, encoding='utf-8')
    print('Successfully patched client.ts')
else:
    print('Target not found in client.ts')
