import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { spawn } from 'child_process';
import path from 'path';

// Vite plugin to bridge /api/rpc to Python DesktopService stdio
function pythonDesktopBridgePlugin() {
  let pyProc: any = null;
  const projectRoot = path.resolve(__dirname, '..');
  const pythonExe = path.resolve(projectRoot, '.venv', 'Scripts', 'python.exe');
  const pendingRequests = new Map<string, { res: any; timer: any }>();
  let stdoutBuffer = '';

  function ensurePython(): any {
    if (pyProc && pyProc.exitCode === null && !pyProc.killed) {
      return pyProc;
    }

    console.log('[Python Desktop] Spawning stdio bridge...');
    stdoutBuffer = '';
    pyProc = spawn(pythonExe, ['-u', '-m', 'mendex_core.desktop'], {
      cwd: projectRoot,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    pyProc.stdout.on('data', (chunk: Buffer) => {
      stdoutBuffer += chunk.toString();
      const lines = stdoutBuffer.split('\n');
      stdoutBuffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        console.log('[Python Desktop stdout line]:', trimmed);
        try {
          const parsed = JSON.parse(trimmed);
          const reqId = parsed.id;
          if (reqId && pendingRequests.has(reqId)) {
            const entry = pendingRequests.get(reqId)!;
            pendingRequests.delete(reqId);
            clearTimeout(entry.timer);
            entry.res.setHeader('Content-Type', 'application/json');
            entry.res.end(trimmed);
          }
        } catch {
          // Ignore non-json logging
        }
      }
    });

    pyProc.stderr.on('data', (d: Buffer) => {
      console.error('[Python Desktop stderr]:', d.toString());
    });

    pyProc.stdin.on('error', (err: any) => {
      console.warn('[Python Desktop stdin error]:', err.message);
    });

    pyProc.on('exit', (code: number) => {
      console.warn(`[Python Desktop] exited with code ${code}`);
      const failedEntries = Array.from(pendingRequests.entries());
      pendingRequests.clear();
      for (const [, entry] of failedEntries) {
        clearTimeout(entry.timer);
        entry.res.statusCode = 503;
        entry.res.end(JSON.stringify({ error: { code: 'BRIDGE_RESTARTING', message: 'Bridge restarted' } }));
      }
      pyProc = null;
    });

    return pyProc;
  }

  return {
    name: 'python-desktop-bridge',
    configureServer(server: any) {
      ensurePython();

      server.middlewares.use('/api/rpc', async (req: any, res: any) => {
        const allowedHosts = new Set(['127.0.0.1:5173', 'localhost:5173', '[::1]:5173']);
        const host = req.headers.host;
        const origin = req.headers.origin ? String(req.headers.origin).replace(/^https?:\/\//, '') : null;
        if (!host || !allowedHosts.has(host) || (origin && !allowedHosts.has(origin))) {
          res.statusCode = 403;
          res.end(JSON.stringify({ error: 'Local loopback same-origin requests required' }));
          return;
        }
        if (req.method !== 'POST') {
          res.statusCode = 405;
          res.end(JSON.stringify({ error: 'Method not allowed' }));
          return;
        }

        let body = '';
        let bytes = 0;
        let oversized = false;
        req.on('data', (chunk: any) => {
          bytes += chunk.length;
          if (bytes > 256 * 1024) {
            if (!oversized) { res.statusCode = 413; res.end('Request exceeds 256 KiB'); }
            oversized = true;
            return;
          }
          body += chunk;
        });

        req.on('end', () => {
          if (oversized) return;
          try {
            const trimmed = body.trim();
            const proc = ensurePython();
            if (!proc || !proc.stdin || !proc.stdin.writable) {
              res.statusCode = 500;
              res.end(JSON.stringify({ error: { code: 'NOT_RUNNING', message: 'Python bridge not writable' } }));
              return;
            }

            const parsed = JSON.parse(trimmed);
            const reqId = parsed.id;
            if (typeof reqId !== 'string' || !reqId || reqId.length > 128 || pendingRequests.has(reqId) || pendingRequests.size >= 16) {
              res.statusCode = 400;
              res.end(JSON.stringify({ error: 'Invalid, duplicate or excessive request IDs' }));
              return;
            }

            const timer = setTimeout(() => {
              if (pendingRequests.has(reqId)) {
                pendingRequests.delete(reqId);
                res.statusCode = 504;
                res.end(JSON.stringify({ error: { code: 'TIMEOUT', message: 'Python RPC timeout after 30s' } }));
              }
            }, 30000);

            pendingRequests.set(reqId, { res, timer });
            console.log('[RPC in]:', parsed.method, reqId);
            proc.stdin.write(JSON.stringify(parsed) + '\n');
          } catch (err: any) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: { code: 'INTERNAL_ERROR', message: err.message } }));
          }
        });
      });
    },
    buildEnd() {
      if (pyProc && !pyProc.killed) {
        pyProc.kill();
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), pythonDesktopBridgePlugin()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
});
