const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert');
const root=process.argv[2],read=n=>JSON.parse(fs.readFileSync(path.join(root,n))),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const api=require(path.join(root,'tm_states.js'));const target='HSPH1_12757_homodimer';
const catalog=read('tm-states.json'),t=catalog.targets[target],r=read('residue-ranges.json').targets[target].residue_ranges[0];
const entry=t.ranges.all.views.density,payload=read(entry.file);let panels=0;
for(const view of ['primary','density']){
 const raw=fs.readFileSync(path.join(root,target,view+'.json')),d=JSON.parse(raw);
 Object.assign(d,{range_id:'all',visible_view_policy:true,policy_view_id:view,views:r.views,_source_sha:hash(raw)});
 api.validatePayload(payload,{...t.ranges.all.views[view],effective_scope_id:'full-dimer'},t,d);
 for(const state of payload.states)for(const method of ['mcmc50','disco50']){
  const a=state.selections.all[view][method].ensemble,b=fs.readFileSync(path.join(root,a.file));assert.equal(b.length,a.bytes);assert.equal(hash(b),a.sha256);assert.equal((b.toString().match(/^MODEL /gm)||[]).length,50);panels++;
 }
 if(view==='density'){
  for(const mutate of [p=>{p.chains[1].residues=116},p=>{p.model_sha256=[]},p=>{p.model_sha256[0]='0'.repeat(64)}]){
   const bad=structuredClone(payload);mutate(bad);assert.throws(()=>api.validatePayload(bad,{...entry,effective_scope_id:'full-dimer'},t,d));
  }
 }
 assert.equal(d.projections.pca.xy.length,4006);assert.equal(d.projections.umap.xy.length,4006);assert.equal(d.projections.tsne.xy.length,4006);
 const energy=d.schemes.find(s=>s.key==='protein_ebm_energy_t10');assert.equal(energy.values.length,4006);assert(energy.values.every(Number.isFinite));
}
console.log(JSON.stringify({status:'validated',views:2,models:4006,panels,dimer_negative_checks:3,scientific_execution:false}));
