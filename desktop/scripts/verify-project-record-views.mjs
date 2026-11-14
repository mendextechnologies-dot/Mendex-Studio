import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const fixtures = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const server = await createServer({ configFile: false, server: { middlewareMode: true }, appType: 'custom' });
try {
  const { ProjectDetailView } = await server.ssrLoadModule('/src/pages/ProjectDetail.tsx');
  const { effectiveStageStatus, validationStatus } = await server.ssrLoadModule('/src/components/RevisionEngineeringPanel.tsx');
  const render = (data, tab) => {
    globalThis.location = { search: `?tab=${tab}` };
    return renderToStaticMarkup(React.createElement(ProjectDetailView, { projectId: data.product.product_id, data, onBack() {} }));
  };
  const tabs = ['overview', 'lifecycle', 'specifications', 'calculations', 'simulations', 'designs', 'files', 'validation', 'revisions', 'reports'];
  for (const data of Object.values(fixtures)) {
    for (const tab of tabs) {
      const html = render(data, tab);
      assert.ok(html.includes(data.product.code), `Project identity missing: ${tab}`);
      for (const forbidden of ['SV1000', 'SV-1000', '1000.31', '474.4', '3 CAD Models Verified', '4 Calculations Recorded', 'Gates Verified', 'Solvers Configured &amp; Qualified']) {
        assert.ok(!html.includes(forbidden), `Unattributed claim ${forbidden} on ${tab}`);
      }
    }
  }
  assert.ok(render(fixtures.empty, 'specifications').includes('Unknown'));
  const low = render(fixtures.different, 'specifications');
  assert.ok(low.includes('7.25') && low.includes('3.3'));
  assert.ok(render(fixtures.empty, 'calculations').includes('No calculation runs recorded'));
  assert.ok(render(fixtures.empty, 'simulations').includes('No simulation jobs explicitly linked'));
  const stale = structuredClone(fixtures.empty);
  stale.lifecycle.stages[0].status = 'COMPLETED';
  stale.lifecycle.stages[0].effective_status = 'BLOCKED';
  stale.lifecycle.stages[0].blockers = ['Stale fixture review'];
  assert.equal(effectiveStageStatus(stale.lifecycle.stages[0]), 'BLOCKED');
  assert.ok(render(stale, 'overview').includes('0 / 9'));
  assert.ok(render(stale, 'lifecycle').includes('Stale fixture review'));
  for (const entry of [{ effective_status: 'fail' }, { effective_status: 'pass', stale: true }, { effective_status: 'pass', evidence_integrity: false }]) {
    stale.validation = { results: [{ ...entry, record: { record_id: 'fixture', check: { check_id: 'CHECK', status: 'pass' } } }] };
    const html = render(stale, 'validation');
    assert.ok(html.includes(validationStatus(entry)));
    assert.ok(!html.includes('>PASS</span>'), 'Historical pass leaked into effective verdict');
  }
  assert.equal(validationStatus({ effective_status: 'pass', evidence_integrity: true }), 'PASS');
  console.log('PASS: 10 project tabs on two distinct core payloads; unknown/empty states, stale lifecycle and effective validation verdicts.');
} finally {
  delete globalThis.location;
  await server.close();
}
