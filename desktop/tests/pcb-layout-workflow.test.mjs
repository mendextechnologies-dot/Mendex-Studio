// React interaction logic + real Python RPC on a disposable root. No browser or visual claims.
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { mkdir, readFile, writeFile, unlink } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash, randomUUID } from 'node:crypto';
import { build } from 'esbuild';
import React from 'react';
import TestRenderer, { act } from 'react-test-renderer';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

test('PCB layout React controls use the real shared service', { timeout: 30000 }, async t => {
  const evidence = path.join(projectRoot, '.mendex/qa', `pcb-layout-constraints-ui-${randomUUID()}`);
  const bundleDirectory = path.join(projectRoot, 'desktop/node_modules/.cache/pcb-layout-tests');
  await mkdir(evidence, { recursive: true });
  await mkdir(bundleDirectory, { recursive: true });
  const bundle = path.join(bundleDirectory, `${randomUUID()}.mjs`);
  const pending = new Map();
  let stderr = '';
  let renderer;
  const python = path.join(projectRoot, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const child = spawn(python, ['-u', 'scripts/pcb_layout_ui_fixture.py', '--root', path.join(evidence, 'studio')], {
    cwd: projectRoot, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
  });
  child.stderr.on('data', chunk => { stderr += chunk.toString(); });
  const lines = createInterface({ input: child.stdout });
  let setup;
  const ready = new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', code => { if (!setup) reject(new Error(`Fixture exited ${code}: ${stderr}`)); });
    lines.on('line', line => {
      try {
        const data = JSON.parse(line);
        if (data.revision_id && !data.id) { setup = data; resolve(data); return; }
        const entry = pending.get(data.id);
        if (entry) { pending.delete(data.id); entry.resolve(JSON.stringify(data)); }
      } catch (error) { reject(error); }
    });
  });
  function invoke(method, { request }) {
    assert.equal(method, 'rpc_dispatch');
    const payload = JSON.parse(request);
    return new Promise((resolve, reject) => {
      pending.set(payload.id, { resolve, reject });
      child.stdin.write(request + '\n');
    });
  }
  async function drain() {
    let quiet = 0;
    const deadline = Date.now() + 8000;
    while (quiet < 3) {
      if (Date.now() > deadline) throw new Error(`RPC did not settle: ${stderr}`);
      await pause(10);
      quiet = pending.size ? 0 : quiet + 1;
    }
  }
  function button(label) {
    return renderer.root.findAllByType('button').find(b => b.children.join('') === label);
  }
  const byLabel = label => renderer.root.findByProps({ 'aria-label': label });
  function change(label, value) {
    act(() => byLabel(label).props.onChange({ target: { value } }));
  }
  async function click(label) {
    const b = button(label);
    assert.ok(b, `Missing button: ${label}`);
    assert.equal(b.props.disabled || false, false, `Button disabled: ${label}`);
    await act(async () => { b.props.onClick(); await drain(); });
  }
  const text = () => JSON.stringify(renderer.toJSON());
  try {
    setup = await ready;
    globalThis.window = { __TAURI__: { core: { invoke } } };
    await build({ entryPoints: [path.join(projectRoot, 'desktop/src/components/PCBLayoutCard.tsx')],
      outfile: bundle, bundle: true, format: 'esm', platform: 'node', packages: 'external' });
    const { PCBLayoutCard } = await import(pathToFileURL(bundle).href);
    await act(async () => {
      renderer = TestRenderer.create(React.createElement(PCBLayoutCard, { revisionId: setup.revision_id, key: setup.revision_id }));
      await drain();
    });
    await t.test('select and analyze a real fixture through desktop RPC', async () => {
      assert.equal(byLabel('Layout board').props.value, 'pcb/fixture.kicad_pcb');
      await click('Analyze board');
      assert.match(text(), /Current board placement checks/);
      assert.match(text(), /Placement drawings: .*CLEAR/);
      assert.equal(byLabel('Keep J1 fixed').props.checked, true);
      assert.equal(byLabel('Keep J1 fixed').props.disabled, true);
      change('Layout experiment rationale', 'Synthetic UI placement regression');
    });
    await t.test('outside-board move is blocked by the real geometry report', async () => {
      change('Component to move', 'R1');
      change('Target X in mm', '-10');
      await click('Add / replace move');
      assert.equal(button('Create moved candidate').props.disabled, true);
      await click('Check placement plan');
      assert.match(text(), /OUTSIDE_BOARD_OR_TOUCHING_EDGE/);
      assert.equal(button('Create moved candidate').props.disabled, true);
    });
    await t.test('explicit fixed references and a valid move produce an intact candidate', async () => {
      change('Target X in mm', '15');
      await click('Add / replace move');
      act(() => byLabel('Keep R1 fixed').props.onChange({ target: { checked: true } }));
      assert.ok(button('Create snapshot candidate')); // Fixing a component removes its queued move.
      assert.ok(!byLabel('Component to move').findAllByType('option').some(o => o.props.value === 'R1' || o.children.join('') === 'R1'));
      act(() => byLabel('Keep R1 fixed').props.onChange({ target: { checked: false } }));
      change('Component to move', 'R1');
      change('Target X in mm', '15');
      await click('Add / replace move');
      act(() => byLabel('Keep U1 fixed').props.onChange({ target: { checked: true } }));
      await click('Check placement plan');
      assert.equal(button('Create moved candidate').props.disabled, false);
      await click('Create moved candidate');
      assert.match(text(), /Candidate created:/);
      assert.match(text(), /DRAFT_CANDIDATE/);
      assert.match(text(), /Current placement result: .*CLEAR/);
      const response = JSON.parse(await invoke('rpc_dispatch', { request: JSON.stringify({
        protocol_version: '3.1.0', id: 'test-history', method: 'pcb_layout_candidates', params: { revision_id: setup.revision_id },
      }) }));
      assert.equal(response.result.length, 1);
      const candidate = response.result[0];
      assert.equal(candidate.integrity, true);
      assert.equal(candidate.evaluation_status, 'NOT_EVALUATED');
      assert.deepEqual(candidate.plan.fixed_references, ['U1']);
      assert.equal(candidate.analysis.components.find(c => c.reference === 'R1').x_m, .015);
      assert.equal(createHash('sha256').update(await readFile(setup.board_path)).digest('hex'), setup.source_sha256);
      await writeFile(path.join(evidence, 'candidate-readback.json'), JSON.stringify(candidate, null, 2));
    });
    await t.test('changed source context invalidates the preview and historical geometry result', async () => {
      await writeFile(path.join(path.dirname(setup.board_path), 'fixture.kicad_pro'), '{"synthetic_change":true}');
      await click('Check placement plan');
      assert.match(text(), /Board context changed/);
      assert.equal(button('Create moved candidate').props.disabled, true);
      await click('Refresh');
      assert.match(text(), /Current placement result: .*NOT_EVALUATED/);
      assert.match(text(), /historical, source changed/);
    });
    await t.test('switching revisions clears source data and disables actions for an empty board inventory', async () => {
      await act(async () => {
        renderer.update(React.createElement(PCBLayoutCard, { revisionId: setup.empty_revision_id, key: setup.empty_revision_id }));
        await drain();
      });
      assert.equal(button('Analyze board').props.disabled, true);
      assert.equal(renderer.root.findAllByProps({ 'aria-label': 'Layout experiment rationale' }).length, 0);
      assert.doesNotMatch(text(), /DRAFT_CANDIDATE/);
    });
    await writeFile(path.join(evidence, 'workflow.json'), JSON.stringify({
      fixture: setup, method: 'React test renderer + real desktop stdio RPC',
      source_unchanged: createHash('sha256').update(await readFile(setup.board_path)).digest('hex') === setup.source_sha256,
      browser_visual_verification: 'NOT_EVALUATED',
      evaluation_status: 'NOT_EVALUATED',
    }, null, 2));
    console.log(`Workflow evidence: ${evidence}`);
  } finally {
    if (renderer) act(() => renderer.unmount());
    child.stdin.end();
    const exited = await Promise.race([new Promise(resolve => child.once('exit', () => resolve(true))), pause(1000).then(() => false)]);
    if (!exited) child.kill();
    for (const p of pending.values()) p.reject(new Error('Fixture closed'));
    lines.close();
    await writeFile(path.join(evidence, 'bridge-stderr.log'), stderr);
    await unlink(bundle).catch(() => {});
    delete globalThis.window;
  }
});
