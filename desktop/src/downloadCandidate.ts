/** Validate payload bytes before asking the browser to save a candidate archive. */
export async function downloadCandidate(result: {data_uri:string;sha256:string;filename:string}) {
  const bytes=Uint8Array.from(atob(result.data_uri.split(',')[1]), c=>c.charCodeAt(0));
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)), b=>b.toString(16).padStart(2,'0')).join('');
  if (!result.sha256 || hash!==result.sha256) throw new Error('Download checksum mismatch');
  const url=URL.createObjectURL(new Blob([bytes],{type:'application/zip'}));
  const link=document.createElement('a');link.href=url;link.download=result.filename;document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
}
