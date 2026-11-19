/* Saved-result presentation only. No sampling, clustering or scoring. */
(function(root){
'use strict';
const PALETTE=['#166da5','#d76934','#338b62','#9456ab','#c8486b','#827724','#248895','#745638','#505ac9','#bd624c','#43778a','#8a448c'];
const need=(ok,message)=>{if(!ok)throw new Error(message);};
const unique=values=>[...new Set(values)];
function path(value){need(typeof value==='string'&&value.length>0&&!/[:%\\?#\u0000-\u0020]/.test(value)&&!value.startsWith('/')&&value.split('/').every(p=>p!=='.'&&p!=='..'&&p!==''),'Expected a local relative asset path.');return value;}
function config(raw){
 need(raw?.schema_version===1&&Array.isArray(raw.datasets)&&raw.datasets.length>0,'Missing saved-cohort configuration.');
 const ids=new Set(),scopes=new Set(),identities=new Set();
 for(const d of raw.datasets){
  need(typeof d.id==='string'&&/^[a-zA-Z0-9_-]+$/.test(d.id)&&!ids.has(d.id),'Duplicate or invalid dataset ID.');ids.add(d.id);
  for(const field of ['target','cohort','residues'])need(d[field]&&typeof d[field].id==='string'&&typeof d[field].label==='string','Missing '+field+' identity.');
  need(Number.isInteger(d.model_count)&&d.model_count>0&&Number.isInteger(d.residues.count)&&d.residues.count>0,'Missing cohort/residue counts.');
  const scope=JSON.stringify([d.target.id,d.cohort.id,d.residues.id]);need(!scopes.has(scope),'Ambiguous target/cohort/residue binding.');scopes.add(scope);
  path(d.data);if(d.asset_base)path(d.asset_base);
  need(/^[a-f0-9]{64}$/.test(d.data_sha256),'Missing saved data identity.');need(!identities.has(d.data_sha256),'One saved result cannot stand for different scientific scopes.');identities.add(d.data_sha256);
 }
 return raw;
}
function data(raw,dataset){
 const n=dataset.model_count;
 if(raw.views)raw={...raw,views:Object.fromEntries(Object.entries(raw.views).map(([id,v])=>{if(v.xy&&!v.umap){need(dataset.legacy_projection==='umap','Legacy xy projection needs an explicit saved UMAP binding.');return [id,{...v,umap:v.xy}];}return [id,v];}))};
 need(Array.isArray(raw.models)&&raw.models.length===n&&raw.models.every(x=>typeof x==='string')&&unique(raw.models).length===n,'Model roster is missing, duplicated or differs from the selected cohort.');
 need(Array.isArray(raw.methods)&&raw.methods.length===n,'Sampling methods do not join to the cohort.');
 need(raw.views&&Object.keys(raw.views).length>0,'No saved clustering views.');
 const ids=new Set(raw.models);
 need(Array.isArray(raw.model_assets)&&raw.model_assets.length===n,'Every model needs its exact native coordinate asset.');
 raw.model_assets.forEach((a,i)=>{need(a.model===raw.models[i]&&/^[a-f0-9]{64}$/.test(a.sha256),'Native model identities do not join.');path(a.file);need(a.chain_map&&typeof a.chain_map==='object'&&(a.residue_numbering==='canonical'||a.residue_map),'Native chain/residue mapping is required.');});
 need(dataset.inspection?.alignment?.residues?.length>=3&&Array.isArray(dataset.inspection.rois),'Explicit display alignment and ROI metadata are required.');
 for(const v of Object.values(raw.views)){
  need(Array.isArray(v.labels)&&v.labels.length===n&&v.labels.every(x=>typeof x==='string'),'Cluster memberships do not join to the cohort.');
  for(const key of ['umap','pca','tsne'])if(v[key])need(v[key].length===n&&v[key].every(x=>Array.isArray(x)&&x.length>=2&&Number.isFinite(x[0])&&Number.isFinite(x[1])),'Invalid saved '+key+' projection.');
  need(['umap','pca','tsne'].some(k=>v[k]),'No saved projection for this view.');
  need(Array.isArray(v.representatives),'Missing representative index.');
  const labels=new Set();for(const r of v.representatives){need(ids.has(r.model)&&v.labels.includes(r.cluster)&&!labels.has(r.cluster),'Invalid representative identity.');labels.add(r.cluster);path(r.file);if(r.ensemble)path(r.ensemble);}
 }
 for(const panel of [...(raw.panels||[]),...(raw.interim_panels||[])]){
  need(Array.isArray(panel.models)&&panel.models.every(id=>ids.has(id)),'Saved panel contains a model outside this cohort.');
  need(raw.views[panel.view]&&['mcmc','disco'].includes(panel.method),'Saved panel has an unknown view or method.');path(panel.file);
 }
 for(const tree of raw.trees||[])path(tree.file);
 for(const report of raw.reports||[])for(const file of Object.values(report.files))path(file);
 if(raw.energy)need(raw.energy.length===n,'Energy values do not join to the cohort.');
 if(raw.state_labels)need(raw.state_labels.length===n,'State memberships do not join to the cohort.');
 return raw;
}
function asset(dataset,file){return (dataset.asset_base?dataset.asset_base+'/':'')+path(file);}
function categorical(values){const keys=unique(values.map(v=>String(v??'Unavailable'))).sort();return Object.fromEntries(keys.map((k,i)=>[k,k==='Unassigned'?'#9ca6b1':PALETTE[i%PALETTE.length]]));}
function panelSelection(atlas,view,settings){
 const empty={mcmc:[],disco:[],panels:[],available:false};
 if(settings.method==='none')return {...empty,note:'Highlighting is off. Plot colors and structure inspection remain independent.'};
 const pool=(settings.origin==='interim'?atlas.interim_panels:atlas.panels)||[];
 const panels=pool.filter(p=>p.view===view&&(settings.state==='all'||p.state===settings.state));
 const index=new Map(atlas.models.map((id,i)=>[id,i]));const out={...empty,panels,available:true};
 for(const method of ['mcmc','disco']){
  const rows=panels.filter(p=>p.method===method);out[method]=unique(rows.flatMap(p=>p.models.map(id=>{need(index.has(id),'Panel identity no longer matches this cohort.');return index.get(id);})));
 }
 const methods=settings.method==='both'?['mcmc','disco']:[settings.method];
 out.available=methods.some(m=>out[m]?.length);
 out.note=(settings.origin==='interim'?'Earlier-cohort comparison · ':'Saved current-cohort panels · ')+methods.map(m=>m.toUpperCase()+': '+(out[m]?.length||0)+' unique models').join(' · ')+'. Highlights use saved panel membership; they do not filter or refit the population.';
 if(!out.available)out.note='No saved '+settings.method.toUpperCase()+' panel for this view and state. No selection is inferred.';
 return out;
}
function traces(atlas,view,projection,color,highlight,method){
 const v=atlas.views[view],xy=v[projection];need(xy,'Projection unavailable.');
 const continuous=color==='energy'||color==='foxs_chi_square_q0p20'||color==='foxs_chi_square_q0p25',metricLabel={energy:'ProteinEBM energy',foxs_chi_square_q0p20:'FoXS χ² · q0.20',foxs_chi_square_q0p25:'FoXS χ² · q0.25'}[color];
 const values=({cluster:v.labels,method:atlas.methods,state:atlas.state_labels,energy:atlas.energy})[color]||atlas[color];need(values,'Color values unavailable.');
 const bins=new Map();values.forEach((value,i)=>{const key=continuous?(Number.isFinite(value)?metricLabel:'Unavailable'):String(value??'Unavailable');if(!bins.has(key))bins.set(key,[]);bins.get(key).push(i);});
 const colors=categorical(values), out=[];
 function trace(indices,name,marker,group){return {type:'scatter',mode:'markers',name,legendgroup:group,x:indices.map(i=>xy[i][0]),y:indices.map(i=>xy[i][1]),customdata:indices,text:indices.map(i=>atlas.models[i]+' · cluster '+v.labels[i]+' · '+(metricLabel||color)+': '+String(values[i]??'Unavailable')),hovertemplate:'%{text}<extra></extra>',marker};}
 for(const [key,indices]of bins){out.push(trace(indices,key,{size:5,opacity:.62,...(continuous&&key===metricLabel?{color:indices.map(i=>values[i]),colorscale:'Viridis',showscale:true,colorbar:{title:{text:metricLabel}}}:{color:continuous?'#9ca6b1':colors[key]})},key));}
 if(highlight?.available)for(const selection of (method==='both'?['mcmc','disco']:[method])){
  const chosen=new Set(highlight[selection]);for(const [key,indices]of bins){const points=indices.filter(i=>chosen.has(i));if(!points.length)continue;const t=trace(points,selection.toUpperCase(),{symbol:selection==='mcmc'?'circle-open':'diamond-open',size:selection==='mcmc'?12:17,color:selection==='mcmc'?'#7a2fa4':'#bb510c',line:{width:2},opacity:1},key);t.showlegend=false;t.meta={savedPanel:selection};out.push(t);}
 }
 return out;
}
function rainbow(position,length){const h=240*(1-position/Math.max(1,length-1)),x=1-Math.abs((h/60)%2-1);const rgb=h<60?[1,x,0]:h<120?[x,1,0]:h<180?[0,1,x]:[0,x,1];return '#'+rgb.map(c=>Math.round(c*255).toString(16).padStart(2,'0')).join('');}
function atomColors(mode,atoms,clusterColor,confidence){
 const residue=a=>String(a.chain??'')+'|'+String(a.resi)+'|'+String(a.icode??'');
 const chains=unique(atoms.filter(a=>a.atom==='CA').map(a=>String(a.chain??''))).sort(),positions=new Map(),chainLengths=new Map();
 for(const a of (mode==='rainbow'?atoms.filter(a=>a.atom==='CA'):[])){const chain=String(a.chain??''),key=residue(a);need(!positions.has(key),'Ambiguous duplicate Cα residue identity.');const i=chainLengths.get(chain)||0;positions.set(key,i);chainLengths.set(chain,i+1);}
 if(mode==='confidence')need(confidence?.kind==='plddt'&&confidence.source==='b_factor'&&confidence.verified===true,'pLDDT coloring requires verified confidence metadata.');
 return a=>{
  if(mode==='chain')return PALETTE[Math.max(0,chains.indexOf(String(a.chain??'')))%PALETTE.length];
  if(mode==='rainbow'){const i=positions.get(residue(a));return i===undefined?'#9ca6b1':rainbow(i,chainLengths.get(String(a.chain??'')));}
  if(mode==='confidence'){const b=a.b;return !Number.isFinite(b)||b<0||b>100?'#9ca6b1':b>=90?'#0053d6':b>=70?'#65cbf3':b>=50?'#ffdb13':'#ff7d45';}
  return mode==='cluster'?clusterColor:'#21849a';
 };
}
const api={path,config,data,asset,categorical,panelSelection,traces,atomColors,rainbow};root.CohortAtlasModel=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
