import { useEffect, useState } from 'react';

/** Serial reads; discard responses after navigation/unmount. Never replay writes. */
export function usePolling<T>(load: () => Promise<T>, interval = 4000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    setData(null);
    const poll = async () => {
      try { const result = await load(); if (!disposed) { setData(result); setError(''); } }
      catch (e) { if (!disposed) setError(String(e)); }
      finally { if (!disposed) timer = setTimeout(poll, interval); }
    };
    poll();
    return () => { disposed = true; clearTimeout(timer); };
  }, [load, interval]);
  return { data, error };
}
