// Render the real React views against a shared-core payload; no browser or live writes.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const data = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const server = await createServer({ configFile: false, server: { middlewareMode: true }, appType: 'custom' });
try {
  const { ComponentLibraryView, quantity } = await server.ssrLoadModule('/src/pages/ComponentLibrary.tsx');
  const render = props => renderToStaticMarkup(React.createElement(ComponentLibraryView, props));
  assert.equal(quantity(null, 'T'), 'Unknown');
  assert.equal(quantity(0, 'A'), '0 A');
  const parts = render({ data });
  for (const value of ['BSC026N08NS5', 'UCC21520', 'NRND', 'Product family', 'Manufacturer source', 'NOT_EVALUATED', 'Conditions &amp; models']) {
    assert.ok(parts.includes(value), `Missing part/reference content: ${value}`);
  }
  assert.ok(!parts.includes('undefined'));
  const materials = render({ data, initialTab: 'materials' });
  for (const value of ['MnZn ferrite', '2,200', '2,300', '0.49', '0.51', '&gt;210', 'Unknown', '100 degrees C']) {
    assert.ok(materials.includes(value), `Missing material content: ${value}`);
  }
  assert.ok(!materials.includes('undefined'));
  const cores = render({ data, initialTab: 'cores' });
  assert.ok(cores.includes('Unknown') && cores.includes('Source required'));
  assert.ok(!cores.includes('78.5') && !cores.includes('2470'));
  assert.ok(render({ data: { ...data, components: [] } }).includes('No references match'));
  assert.ok(render({ data: null, error: 'Bridge offline' }).includes('role="alert"'));
  assert.ok(render({ data, error: 'Bridge offline' }).includes('records may be stale'));
  console.log('PASS: all three React library views, real wire fields, unknowns, source/status labels, empty/error/stale states.');
} finally {
  await server.close();
}
