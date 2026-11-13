const assert = require('node:assert/strict');
const crypto = require('node:crypto');
require('../site/joint_tm_states.js');

const digest = value => crypto.createHash('sha256').update(value).digest('hex');
const models = Array.from({length: 5000}, (_, i) => `m${i}`);
const hashes = models.map((_, i) => i.toString(16).padStart(64, '0'));
const positions = Array.from({length: 413}, (_, i) => i + 1);
const source = 'c'.repeat(64);
const panels = view => Object.fromEntries(['mcmc50', 'disco50'].map(method => [method, {
  indices: Array.from({length: 50}, (_, i) => i),
  models: models.slice(0, 50),
  ensemble: {file: `tm-state-ensembles/CDK2_DOC1/joint/${view === 'primary' ? 'primary' : 'density'}/S1/${method}.pdb`,
    sha256: (view === 'primary' ? 'd' : '2').repeat(64), bytes: 100},
}]));
const views = Object.fromEntries(['primary', 'density', 'eom'].map(view => [view,
  {source_data_sha256: source}]));
const payload = {
  schema_version: 3, kind: 'tm_state_selection_payload', target: 'CDK2_DOC1',
  effective_scope_id: 'joint-full-complex', models, model_sha256: hashes,
  model_order_sha256: digest(JSON.stringify(models)), sequence_sha256: 'e'.repeat(64),
  chain: 'A,B', chains: [{chain: 'A', residues: 298}, {chain: 'B', residues: 115}],
  construct_residues: 413, canonical_positions: positions,
  mask_sha256: digest(JSON.stringify(positions)), tm_threshold: .7,
  ranges: {joint: {effective_scope_id: 'joint-full-complex', views}},
  run: {plan_sha256: 'a'.repeat(64), state_receipt_sha256: 'b'.repeat(64),
    sampling_plan_sha256: 'f'.repeat(64), sampling_receipt_sha256: '1'.repeat(64)},
  selection_prior: {conditioning_t: .1, alpha: .5, tau_iqr_multiplier: 1,
    subset_law: 'product-weight', subset_size: 50, production_chain: 0,
    production_iteration: 10000,
    per_view: {primary: 'UMAP_KNN', density: 'HDBSCAN_leaf', eom: 'HDBSCAN_leaf'}},
  states: [{id: 'S1', representative: {index: 0, model: models[0]},
    members: models.slice(0, 50).map((model, index) => ({index, model, tm_score: .8})),
    selections: {joint: Object.fromEntries(['primary', 'density', 'eom'].map(view =>
      [view, {prior: view === 'primary' ? 'UMAP_KNN' : 'HDBSCAN_leaf', ...panels(view)}]))}}],
  coverage: {assigned_models: 50, unassigned_models: 4950},
  flags: {incomplete_coverage: true, short_core: false},
  membership_coverage: {tm_assigned_models: 50, uncovered_models: 4950,
    unsupported_state_models: 0, unsupported_states: []},
  state_diagnostics: {proxy: {covered_mass: 40, total_mass: 100,
      coverage: .4, status: 'partial_coverage', leaf_unassigned_models: 4900},
    sensitivity: [.6, .7, .8].map(cutoff => ({cutoff, assigned_models: 50,
      below_cutoff_models: 4950, supported_states: 1,
      states: [{id: 'S1', count: 50, supported: true}]})),
    interpretation: 'Proxy mass guided discovery; fixed-anchor sensitivity changes membership cutoff, not the anchors.'},
};
const entry = {effective_scope_id: 'joint-full-complex', source_data_sha256: source,
  state_count: 1, available: true, short_core: false, incomplete_coverage: true};
const target = {model_count: 5000, model_order_sha256: payload.model_order_sha256,
  sequence_sha256: payload.sequence_sha256};
const data = {target: 'CDK2_DOC1', range_id: 'joint', view_id: 'primary',
  residues: 413, models, model_sha256: hashes};
const helpers = {sourceBinding: () => source, sha256: value => digest(value)};
for (const view_id of ['primary', 'density', 'eom']) {
  assert.equal(globalThis.AISJointTMStates.validate(payload, entry, target,
    {...data, view_id}, helpers), payload);
}
assert.notEqual(payload.states[0].selections.joint.primary.mcmc50.ensemble.sha256,
  payload.states[0].selections.joint.density.mcmc50.ensemble.sha256);
assert.equal(payload.states[0].selections.joint.eom.mcmc50.ensemble.sha256,
  payload.states[0].selections.joint.density.mcmc50.ensemble.sha256);
const note = globalThis.AISJointTMStates.coverageNote(payload);
assert.match(note, /Discovery leaf-cluster proxy mass: 40\/100/);
assert.match(note, /these discovery weights are not full-cohort TM assignments/);
assert.match(note, /Fixed-anchor cutoff sensitivity \(no rediscovery\)/);
const badProxy = structuredClone(payload);
badProxy.state_diagnostics.proxy.covered_mass = 60;
assert.throws(() => globalThis.AISJointTMStates.validate(badProxy, entry, target, data, helpers),
  /proxy or sensitivity source/);
const badSensitivity = structuredClone(payload);
badSensitivity.state_diagnostics.sensitivity[1].states[0].count = 49;
assert.throws(() => globalThis.AISJointTMStates.validate(badSensitivity, entry, target, data, helpers),
  /cutoff sensitivity accounting/);
const changed = structuredClone(payload);
changed.states[0].members[0].tm_score = .6;
assert.throws(() => globalThis.AISJointTMStates.validate(changed, entry, target, data, helpers),
  /member or retained TM score/);
console.log('Joint state browser contract passed');
