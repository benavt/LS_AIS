/* Receipt-backed joint 1:1 state payload validation; no browser-side science. */
(function(root){'use strict';
const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const need=(ok,message)=>{if(!ok)throw Error(message)};
const unique=(values,n,count)=>Array.isArray(values)&&values.length===count&&
 values.every(i=>Number.isInteger(i)&&i>=0&&i<n)&&new Set(values).size===count;
function validate(p,entry,target,data,helpers){
 const n=data.models.length,source=helpers.sourceBinding(data),range=data.range_id||'all';
 need(p?.schema_version===3&&p.kind==='tm_state_selection_payload'&&
  p.target===data.target&&p.effective_scope_id==='joint-full-complex'&&
  range==='joint'&&entry.effective_scope_id===p.effective_scope_id,
  'Joint state target or scope differs.');
 need(n===5000&&target.model_count===n&&hash(target.model_order_sha256)&&
  p.model_order_sha256===target.model_order_sha256&&
  p.sequence_sha256===target.sequence_sha256&&hash(p.sequence_sha256)&&
  Array.isArray(p.models)&&p.models.length===n&&
  p.models.every((model,i)=>model===data.models[i])&&
  helpers.sha256(new TextEncoder().encode(JSON.stringify(p.models)))===p.model_order_sha256&&
  Array.isArray(p.model_sha256)&&p.model_sha256.length===n&&
  Array.isArray(data.model_sha256)&&p.model_sha256.every((sha,i)=>
   hash(sha)&&sha===data.model_sha256[i]),
  'Joint state model order or original-coordinate hashes differ.');
 const lengths=data.target==='CDK2_DOC1'?[298,115]:data.target==='CDK2_DOC1t'?[298,55]:null;
 need(lengths&&p.chain==='A,B'&&p.construct_residues===lengths[0]+lengths[1]&&
  p.construct_residues===data.residues&&
  JSON.stringify(p.chains)===JSON.stringify(lengths.map((residues,i)=>
   ({chain:'AB'[i],residues})))&&p.tm_threshold===.7&&
  Array.isArray(p.canonical_positions)&&p.canonical_positions.length===data.residues&&
  p.canonical_positions.every((position,i)=>position===i+1)&&
  helpers.sha256(new TextEncoder().encode(JSON.stringify(p.canonical_positions)))===p.mask_sha256,
  'Joint state fixed-chain construct or canonical positions differ.');
 const binding=p.ranges?.joint?.views?.[data.view_id];
 need(binding?.source_data_sha256===source&&entry.source_data_sha256===source&&
  p.ranges.joint.effective_scope_id===p.effective_scope_id&&
  Object.keys(p.ranges).length===1&&
  ['primary','density','eom'].every(v=>hash(p.ranges.joint.views?.[v]?.source_data_sha256))&&
  hash(p.run?.plan_sha256)&&hash(p.run?.state_receipt_sha256)&&
  hash(p.run?.sampling_plan_sha256)&&hash(p.run?.sampling_receipt_sha256),
  'Joint state source-view or accepted-run binding differs.');
 need(p.selection_prior?.conditioning_t===.1&&p.selection_prior.alpha===.5&&
  p.selection_prior.tau_iqr_multiplier===1&&
  p.selection_prior.subset_law==='product-weight'&&
  p.selection_prior.subset_size===50&&
  p.selection_prior.production_chain===0&&
  p.selection_prior.production_iteration===10000&&
  p.selection_prior.per_view?.primary==='UMAP_KNN'&&
  p.selection_prior.per_view?.density==='HDBSCAN_leaf'&&
  p.selection_prior.per_view?.eom==='HDBSCAN_leaf',
  'Joint state sampling policy differs.');
 need(Array.isArray(p.states)&&p.states.length>=1&&p.states.length<=3,
  'Joint states exceed the approved count.');
 const used=new Set(),stateIds=new Set();
 for(const state of p.states){
  need(/^S[123]$/.test(state.id)&&!stateIds.has(state.id)&&
   Array.isArray(state.members)&&state.members.length>=50,
   'Joint state identity or support differs.');stateIds.add(state.id);
  for(const member of state.members){
   need(Number.isInteger(member.index)&&member.index>=0&&member.index<n&&
    !used.has(member.index)&&member.model===p.models[member.index]&&
    Number.isFinite(member.tm_score)&&member.tm_score>=.7&&member.tm_score<=1,
    'Joint state member or retained TM score differs.');used.add(member.index);
  }
  need(state.representative?.model===p.models[state.representative?.index]&&
   state.members.some(member=>member.index===state.representative.index),
   'Joint state representative is not a member.');
  for(const view of ['primary','density','eom']){
   const choice=state.selections?.joint?.[view];
   need(choice?.prior===p.selection_prior.per_view[view],
    'Joint state fine-view prior differs.');
   const diagnostic=choice.diagnostics;
   const directory=view==='primary'?'primary':'density';
   need(diagnostic?.file===`tm-state-diagnostics/${p.target}/joint/${directory}/${state.id}.json`&&
    hash(diagnostic.sha256)&&Number.isInteger(diagnostic.bytes)&&
    diagnostic.bytes>0&&diagnostic.bytes<=1048576&&
    diagnostic.exact_control_panels===20&&
    diagnostic.retained_panels===36000&&
    Number.isFinite(diagnostic.inclusion_rmse)&&
    diagnostic.inclusion_rmse>=0&&diagnostic.inclusion_rmse<=1&&
    Number.isFinite(diagnostic.expected_panel_mean_energy)&&
    Number.isInteger(diagnostic.physicality_rejected_in_pool)&&
    diagnostic.physicality_rejected_in_pool>=0&&
    diagnostic.physicality_rejected_in_pool<=state.members.length&&
    diagnostic.completion_is_not_convergence===true&&
    diagnostic.poor_mixing_extension===false&&
    ['panel_mean_energy','panel_log_weight'].every(key=>{
     const metric=diagnostic[key];return metric?.status==='computed'&&
      metric.n_chains===4&&metric.n_draws===9000&&
      Number.isFinite(metric.rhat)&&metric.rhat>=1&&
      Number.isFinite(metric.ess_bulk)&&metric.ess_bulk>0;
    }),
    'Joint state MCMC diagnostic differs.');
   for(const method of ['mcmc50','disco50']){
    const panel=choice[method];
    need(unique(panel?.indices,n,50)&&
     panel.indices.every(index=>state.members.some(member=>member.index===index))&&
     Array.isArray(panel.models)&&panel.models.every((model,i)=>
      model===p.models[panel.indices[i]])&&
     panel.ensemble?.file===`tm-state-ensembles/${p.target}/joint/${view==='primary'?'primary':'density'}/${state.id}/${method}.pdb`&&
     hash(panel.ensemble.sha256)&&Number.isInteger(panel.ensemble.bytes)&&
     panel.ensemble.bytes>0&&panel.ensemble.bytes<=67108864,
     'Joint state panel or coordinate artifact differs.');
   }
  }
 }
 need(p.coverage?.assigned_models===used.size&&
  p.coverage?.unassigned_models===n-used.size&&
  p.flags?.incomplete_coverage===(used.size<n)&&p.flags?.short_core===false&&
  entry.state_count===p.states.length&&entry.available===true&&
  entry.short_core===false&&entry.incomplete_coverage===p.flags.incomplete_coverage,
  'Joint state coverage or catalog summary differs.');
 const m=p.membership_coverage;
 need(Number.isInteger(m?.tm_assigned_models)&&
  Number.isInteger(m?.uncovered_models)&&
  Number.isInteger(m?.unsupported_state_models)&&
  m.tm_assigned_models+m.uncovered_models===n&&
  m.tm_assigned_models===used.size+m.unsupported_state_models&&
  Array.isArray(m.unsupported_states)&&
  m.unsupported_states.length+p.states.length<=3,
  'Joint state unsupported or uncovered membership accounting differs.');
 const d=p.state_diagnostics,proxy=d?.proxy,levels=d?.sensitivity;
 need(proxy&&Number.isFinite(proxy.covered_mass)&&
  Number.isFinite(proxy.total_mass)&&proxy.total_mass>0&&
  proxy.covered_mass>=0&&proxy.covered_mass<=proxy.total_mass&&
  Number.isInteger(proxy.leaf_unassigned_models)&&
  proxy.total_mass+proxy.leaf_unassigned_models===n&&
  Math.abs(proxy.coverage-proxy.covered_mass/proxy.total_mass)<1e-12&&
  ['coverage_target_reached','partial_coverage'].includes(proxy.status)&&
  Array.isArray(levels)&&levels.length===3&&
  JSON.stringify(levels.map(row=>row.cutoff))===JSON.stringify([.6,.7,.8])&&
  typeof d.interpretation==='string'&&d.interpretation.includes('not the anchors'),
  'Joint proxy or sensitivity source differs.');
 const stateCounts=new Map([...p.states.map(row=>[row.id,row.members.length]),
  ...m.unsupported_states.map(row=>[row.id,row.count])]);
 for(const row of levels){
  need(Number.isInteger(row.assigned_models)&&Number.isInteger(row.below_cutoff_models)&&
   row.assigned_models+row.below_cutoff_models===n&&
   Array.isArray(row.states)&&row.states.length===stateCounts.size&&
   row.states.every((state,i)=>state.id==='S'+(i+1)&&
    Number.isInteger(state.count)&&state.count>=0&&
    state.supported===(state.count>=50))&&
   row.states.reduce((sum,state)=>sum+state.count,0)===row.assigned_models&&
   row.supported_states===row.states.filter(state=>state.supported).length,
   'Joint cutoff sensitivity accounting differs.');
 }
 const nominal=levels[1];
 need(nominal.assigned_models===m.tm_assigned_models&&
  nominal.below_cutoff_models===m.uncovered_models&&
  nominal.states.every(state=>stateCounts.get(state.id)===state.count),
  'Joint nominal-cutoff sensitivity differs from saved states.');
 return p;
}
function coverageNote(p){
 const d=p.state_diagnostics,proxy=d.proxy,levels=d.sensitivity;
 const m=p.membership_coverage;
 const cutoff=levels.map(row=>
  `TM ≥ ${row.cutoff.toFixed(2)}: ${row.assigned_models.toLocaleString()}/5,000 assigned, ${row.supported_states} supported`).join('; ');
 return `${p.states.length} supported full-cohort states at TM ≥ 0.70: ${p.coverage.assigned_models.toLocaleString()}/5,000 models in supported states; ${m.unsupported_state_models.toLocaleString()} in undersized states; ${m.uncovered_models.toLocaleString()} below cutoff. `+
  `Discovery leaf-cluster proxy mass: ${proxy.covered_mass.toLocaleString()}/${proxy.total_mass.toLocaleString()} (${(100*proxy.coverage).toFixed(1)}%) covered; these discovery weights are not full-cohort TM assignments. `+
  `Fixed-anchor cutoff sensitivity (no rediscovery): ${cutoff}.`;
}
root.AISJointTMStates={validate,coverageNote};
})(typeof window!=='undefined'?window:globalThis);
