import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

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
        const preview = trimmed.length > 180 ? `${trimmed.slice(0, 160)}... (${trimmed.length} chars)` : trimmed;
        console.log('[Python Desktop stdout line]:', preview);
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

      // Auto-restart Python desktop backend when src/**/*.py files change
      server.watcher.add(path.resolve(projectRoot, 'src'));
      server.watcher.on('change', (file: string) => {
        if (file.endsWith('.py')) {
          console.log('[Python Desktop Bridge] Python backend file changed, restarting bridge:', file);
          if (pyProc && !pyProc.killed) {
            pyProc.kill();
            pyProc = null;
          }
        }
      });

      // Direct report file access endpoint (PDF viewer, HTML view, ZIP download)
      server.middlewares.use('/api/report-file', (req: any, res: any) => {
        try {
          const url = new URL(req.url, 'http://127.0.0.1:5173');
          const reportId = url.searchParams.get('id');
          const format = (url.searchParams.get('type') || 'html').toLowerCase();

          if (!reportId || !/^[0-9a-fA-F-]+$/.test(reportId)) {
            res.statusCode = 400;
            res.end('Valid report id required');
            return;
          }

          // 1. If export package requested, locate exported ZIP package
          if (format === 'export' || format === 'zip') {
            const expBase = path.resolve(projectRoot, '.mendex', 'engineering-records', 'exports');
            if (fs.existsSync(expBase)) {
              const entries = fs.readdirSync(expBase)
                .map((d: string) => {
                  const fp = path.join(expBase, d, 'report-package.zip');
                  if (fs.existsSync(fp)) {
                    return { fp, mtime: fs.statSync(fp).mtimeMs };
                  }
                  return null;
                })
                .filter(Boolean)
                .sort((a: any, b: any) => b.mtime - a.mtime);

              if (entries.length > 0 && entries[0]) {
                res.setHeader('Content-Type', 'application/zip');
                res.setHeader('Content-Disposition', `attachment; filename="report-package-${reportId.slice(0, 8)}.zip"`);
                fs.createReadStream(entries[0].fp).pipe(res);
                return;
              }
            }
            res.statusCode = 404;
            res.end('Exported package not found');
            return;
          }

          // 2. Locate report directory under products/**/reports/<reportId>
          let foundRepDir: string | null = null;
          const productsDir = path.resolve(projectRoot, 'products');
          if (fs.existsSync(productsDir)) {
            for (const p of fs.readdirSync(productsDir)) {
              const revDir = path.join(productsDir, p, 'revisions');
              if (fs.existsSync(revDir)) {
                for (const r of fs.readdirSync(revDir)) {
                  const repDir = path.join(revDir, r, 'reports', reportId);
                  if (fs.existsSync(repDir)) {
                    foundRepDir = repDir;
                    break;
                  }
                }
              }
              if (foundRepDir) break;
            }
          }

          if (!foundRepDir) {
            res.statusCode = 404;
            res.end('Report not found');
            return;
          }

          if (format === 'pdf') {
            const pdfPath = path.join(foundRepDir, 'report.pdf');
            if (fs.existsSync(pdfPath)) {
              res.setHeader('Content-Type', 'application/pdf');
              res.setHeader('Content-Disposition', `inline; filename="report-${reportId.slice(0, 8)}.pdf"`);
              fs.createReadStream(pdfPath).pipe(res);
              return;
            }
          }

          // Default fallback to HTML
          const htmlPath = path.join(foundRepDir, 'report.html');
          if (fs.existsSync(htmlPath)) {
            res.setHeader('Content-Type', 'text/html; charset=utf-8');
            fs.createReadStream(htmlPath).pipe(res);
            return;
          }

          res.statusCode = 404;
          res.end('Requested report format not available');
        } catch (err: any) {
          res.statusCode = 500;
          res.end(err.message || 'Internal server error');
        }
      });

      // Direct workspace file access endpoint (HTML reports, CSV downloads, etc.)
      server.middlewares.use('/api/workspace-file', (req: any, res: any) => {
        try {
          const url = new URL(req.url, 'http://127.0.0.1:5173');
          const relPath = url.searchParams.get('path');
          if (!relPath || relPath.includes('..')) {
            res.statusCode = 400;
            res.end('Valid relative workspace path required');
            return;
          }

          // Search in products/**/<relPath>
          let targetPath: string | null = null;
          const productsDir = path.resolve(projectRoot, 'products');
          if (fs.existsSync(productsDir)) {
            for (const p of fs.readdirSync(productsDir)) {
              const revDir = path.join(productsDir, p, 'revisions');
              if (fs.existsSync(revDir)) {
                for (const r of fs.readdirSync(revDir)) {
                  const candidate = path.resolve(revDir, r, relPath);
                  if (fs.existsSync(candidate) && candidate.startsWith(productsDir)) {
                    targetPath = candidate;
                    break;
                  }
                }
              }
              if (targetPath) break;
            }
          }

          if (!targetPath || !fs.existsSync(targetPath)) {
            res.statusCode = 404;
            res.end('Workspace file not found');
            return;
          }

          const ext = path.extname(targetPath).toLowerCase();
          if (ext === '.html') res.setHeader('Content-Type', 'text/html; charset=utf-8');
          else if (ext === '.csv') res.setHeader('Content-Type', 'text/csv; charset=utf-8');
          else if (ext === '.json') res.setHeader('Content-Type', 'application/json');
          else if (ext === '.pdf') res.setHeader('Content-Type', 'application/pdf');
          else res.setHeader('Content-Type', 'text/plain; charset=utf-8');

          fs.createReadStream(targetPath).pipe(res);
        } catch (err: any) {
          res.statusCode = 500;
          res.end(err.message || 'Internal server error');
        }
      });

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
                res.end(JSON.stringify({ error: { code: 'TIMEOUT', message: 'Python RPC timeout after 120s' } }));
              }
            }, 120000);

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
