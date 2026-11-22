/** Validate payload bytes before asking the browser to save a candidate archive or PDF. */
export async function downloadCandidate(result: {data_uri: string; sha256?: string; filename: string}) {
  const parts = result.data_uri.split(',');
  const b64 = parts.length > 1 ? parts[1] : parts[0];
  const mimeMatch = parts[0].match(/:(.*?);/);
  const inferredMime = result.filename.toLowerCase().endsWith('.pdf')
    ? 'application/pdf'
    : (result.filename.toLowerCase().endsWith('.png') ? 'image/png' : 'application/zip');
  const mimeType = mimeMatch ? mimeMatch[1] : inferredMime;
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  if (result.sha256) {
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
    if (hash !== result.sha256) throw new Error('Download checksum mismatch');
  }
  const url = URL.createObjectURL(new Blob([bytes], { type: mimeType }));
  const link = document.createElement('a');
  link.href = url;
  link.download = result.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
