(function(root){
'use strict';
const M=root.CohortAtlasModel;
function start(env={}){
 const doc=env.document||root.document,$=id=>doc.getElementById(id),P=env.Plotly||root.Plotly,mol=env.$3Dmol||root.$3Dmol;
 const request=env.fetch||root.fetch.bind(root),count=n=>n.toLocaleString('en-US');
 let conf,atlas,dataset,viewer,model,representative,body='',format='',panel,loadSerial=0,structureSerial=0,treeSerial=0,redrawSerial=0,destroyed=false;
 const trees=new Map(),listeners=[],state={dataset:null,view:null,projection:'umap',color:'cluster',highlight:'none',state:'all',origin:'current',structureColor:'uniform'};
 function listen(node,event,fn){node.addEventListener(event,fn);listeners.push(()=>node.removeEventListener(event,fn));}
 function fail(e){$('error').hidden=false;$('error').textContent=e.message||String(e);}
 const handle=fn=>(...args)=>Promise.resolve().then(()=>fn(...args)).catch(fail);
 function options(id,items,value){const node=$(id);node.replaceChildren(...items.map(x=>new Option(x.label,x.id)));node.value=items.some(x=>x.id===value)?value:items[0]?.id||'';return node.value;}
 function cell(value){const node=doc.createElement('td');node.textContent=String(value);return node;}
 function link(file,text){const a=doc.createElement('a');a.href=M.asset(dataset,file);a.download='';a.textContent=text;return a;}
 function selected(){if(!atlas)throw Error('A saved cohort must finish loading first.');return atlas.views[state.view];}
 function loading(on){for(const id of ['view','projection','color','highlight','state','origin','clear-highlight','cluster','structure-color','reset-camera','tree'])$(id).disabled=on;}
 function saveRoute(){if(env.route===false||!root.history)return;const params=new URLSearchParams(state);root.history.replaceState(null,'','#'+params);}
 function route(){try{return Object.fromEntries(new URLSearchParams(root.location?.hash.slice(1)||''));}catch{return {};}}
 function selection(){return M.panelSelection(atlas,state.view,{method:state.highlight,state:state.state,origin:state.origin});}
 function configurePanels(){
  const pool=(state.origin==='interim'?atlas.interim_panels:atlas.panels)||[];
  const states=[...new Set(pool.filter(p=>p.view===state.view).map(p=>p.state))];
  state.state=options('state',[{id:'all',label:'All saved states'},...states.map(id=>({id,label:id}))],state.state);
  $('state').disabled=state.highlight==='none'||!states.length;
  $('origin-label').hidden=!(atlas.interim_panels||[]).length;
  if($('origin-label').hidden){state.origin='current';$('origin').value='current';}
  $('highlight').disabled=!(atlas.panels||[]).length&&!(atlas.interim_panels||[]).length;
  $('clear-highlight').disabled=state.highlight==='none';
 }
 function configureDatasets(){
  const targets=[...new Map(conf.datasets.map(d=>[d.target.id,d.target])).values()];options('target',targets,dataset.target.id);$('target-label').hidden=targets.length<2;
  const rows=conf.datasets.filter(d=>d.target.id===dataset.target.id),cohorts=[...new Map(rows.map(d=>[d.cohort.id,d.cohort])).values()];options('cohort',cohorts,dataset.cohort.id);$('cohort-label').hidden=cohorts.length<2;
  const ranges=rows.filter(d=>d.cohort.id===dataset.cohort.id).map(d=>d.residues);options('range',ranges,dataset.residues.id);$('range-label').hidden=ranges.length<2;
  $('dataset-controls').hidden=targets.length<2&&cohorts.length<2&&ranges.length<2;
 }
 function confidenceFor(rep){const c=dataset.confidence;return c?.kind==='plddt'&&c.source==='b_factor'&&c.verified===true&&Array.isArray(c.model_ids)&&c.model_ids.includes(rep?.model)?c:null;}
 function colorNote(){
  const notes={uniform:'Uniform teal.',cluster:'Color follows the saved cluster label.',chain:'Chains have distinct colors.',rainbow:'Blue at each chain’s N terminus → red at its C terminus, following saved Cα order.',confidence:'pLDDT: blue ≥90; light blue 70–90; yellow 50–70; orange <50. Missing values are gray.'};
  $('structure-color-note').textContent=notes[state.structureColor]+' Display colors preserve coordinates and camera orientation.';
 }
 function drawFallback(){
  const atoms=mol?.Parsers?.[format]?.(body,{})?.[0]?.filter(a=>a.atom==='CA');if(!atoms?.length)return false;
  const ns='http://www.w3.org/2000/svg',svg=doc.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 400 280');svg.setAttribute('aria-label','Two-dimensional Cα trace');svg.setAttribute('class','trace');
  const xs=atoms.map(a=>a.x),ys=atoms.map(a=>a.y),xmin=Math.min(...xs),ymin=Math.min(...ys),scale=Math.min(352/(Math.max(...xs)-xmin||1),240/(Math.max(...ys)-ymin||1));
  const colors=M.atomColors(state.structureColor,atoms,M.categorical(selected().labels)[representative.cluster],confidenceFor(representative));
  for(let i=1;i<atoms.length;i++){const a=atoms[i-1],b=atoms[i];if(a.chain!==b.chain)continue;const line=doc.createElementNS(ns,'line');for(const [k,v]of Object.entries({x1:24+(a.x-xmin)*scale,y1:260-(a.y-ymin)*scale,x2:24+(b.x-xmin)*scale,y2:260-(b.y-ymin)*scale,stroke:colors(b),'stroke-width':2,'stroke-linecap':'round'}))line.setAttribute(k,v);svg.append(line);}
  $('viewer').replaceChildren(svg);return true;
 }
 function restyle(reset=false){
  const option=[...$('structure-color').options].find(x=>x.value==='confidence'),eligible=!!confidenceFor(representative);
  option.disabled=!eligible;option.textContent=eligible?'pLDDT':'pLDDT — unavailable';
  if(state.structureColor==='confidence'&&!eligible){state.structureColor='uniform';$('structure-color').value='uniform';}
  colorNote();if(!representative||!body)return;
  if(viewer&&model){let colors;try{colors=M.atomColors(state.structureColor,model.selectedAtoms({}),M.categorical(selected().labels)[representative.cluster],confidenceFor(representative));}catch(e){state.structureColor='uniform';$('structure-color').value='uniform';colors=()=> '#21849a';colorNote();$('structure-color-note').textContent+=' Requested color unavailable: '+e.message;}model.setStyle({},{cartoon:{colorfunc:colors}});if(reset)viewer.zoomTo();viewer.render();}
  else drawFallback();
  saveRoute();
 }
 async function choose(label,clickedIndex=null){
  const token=++structureSerial,rep=selected().representatives.find(r=>r.cluster===label),bound=dataset.id;
  representative=null;body='';model=null;$('coordinate').hidden=true;$('ensemble').hidden=true;
  if(viewer){viewer.removeAllModels();viewer.render();}else $('viewer').replaceChildren();
  if(!rep){$('structure-status').textContent='Unassigned point: no saved cluster representative. Coordinates are not inferred.';return;}
  $('cluster').value=label;$('structure-status').textContent='Loading representative '+rep.model+'…';
  const response=await request(M.asset(dataset,rep.file));if(!response.ok)throw Error('Representative coordinates could not be loaded.');const text=await response.text();
  if(token!==structureSerial||bound!==dataset.id||destroyed)return;
  representative=rep;body=text;format=rep.format||rep.file.split('.').pop();let fallback=false;
  try{if(!viewer)viewer=mol.createViewer($('viewer'),{backgroundColor:'white'});viewer.removeAllModels();model=viewer.addModel(body,format);restyle(true);}
  catch(e){viewer=null;model=null;fallback=drawFallback();}
  const click=clickedIndex===null?'':'Selected point '+atlas.models[clickedIndex]+' · ';
  $('structure-status').textContent=click+'Representative '+rep.model+' · '+count(rep.count)+' models in '+label+(viewer?'':fallback?' · Cα trace (2D)':' · 3D unavailable; download coordinates');
  $('coordinate').href=M.asset(dataset,rep.file);$('coordinate').hidden=false;
  if(rep.ensemble){$('ensemble').href=M.asset(dataset,rep.ensemble);$('ensemble').hidden=false;}
  restyle();
 }
 async function drawTree(){
  const serial=++treeSerial,entry=(atlas.trees||[]).find(t=>t.view===state.view&&t.kind===$('tree').value);
  if(!entry){if(panel){panel.clear();panel=null;}$('tree-note').textContent='No saved Bonsai tree for this view.';return;}
  const file=M.asset(dataset,entry.file);if(!trees.has(file)){const response=await request(file);if(!response.ok)throw Error('Saved Bonsai tree unavailable.');trees.set(file,await response.json());}
  if(serial!==treeSerial||destroyed)return;
  const v=selected(),values={cluster:v.labels,method:atlas.methods,state:atlas.state_labels,energy:atlas.energy}[state.color],scheme={type:state.color==='energy'?'continuous':'categorical',name:$('color').selectedOptions[0].textContent,values,colors:state.color==='energy'?{}:M.categorical(values)};
  if(!root.BonsaiEnsemble){$('tree-note').textContent='Bonsai renderer unavailable; use the saved tree download.';return;}
  if(!panel)panel=root.BonsaiEnsemble.create($('bonsai'),{onChoose:label=>choose(label).catch(fail)});
  const h=selection(),marked=h.available?[...new Set((state.highlight==='both'?['mcmc','disco']:[state.highlight]).flatMap(k=>h[k]))].map(i=>atlas.models[i]):null;
  panel.update({target:dataset.target.id,view_id:state.view,models:atlas.models,clusters:v.labels,methods:atlas.methods,representatives:v.representatives},trees.get(file),scheme,$('plot'),[],marked);
  const a=link(entry.file,'Download saved tree');$('tree-note').textContent=(entry.model_ids?.length||0)+' accepted leaves. Native branch distances are exploratory. ';$('tree-note').append(a);
 }
 function refreshTables(){
  $('panels').replaceChildren();$('interim').replaceChildren();$('reports').replaceChildren();
  for(const row of atlas.panels||[]){const tr=doc.createElement('tr'),inspect=cell(''),download=cell(''),button=doc.createElement('button');button.type='button';button.textContent='Highlight';button.setAttribute('aria-label','Highlight '+row.method.toUpperCase()+' '+row.state+' '+row.view+' panel');button.onclick=handle(()=>setSelection({method:row.method,state:row.state,origin:'current',view:row.view}));inspect.append(button);download.append(link(row.file,'Download PDB'));tr.append(cell(row.state),cell(row.view),cell(row.method.toUpperCase()),cell(row.models.length),inspect,download);$('panels').append(tr);}
  for(const row of atlas.interim_panels||[]){const li=doc.createElement('li'),button=doc.createElement('button');button.type='button';button.textContent='Highlight comparison';button.onclick=handle(()=>setSelection({method:row.method,state:row.state,origin:'interim',view:row.view}));li.append(link(row.file,row.view+' '+row.method.toUpperCase()+' · '+row.state+' · '+row.models.length+' models'),' ',button);$('interim').append(li);}
  $('interim-details').hidden=!(atlas.interim_panels||[]).length;
  for(const report of atlas.reports||[]){const li=doc.createElement('li');li.textContent='Volume '+report.volume+' · '+report.pages+' pages · ';for(const [kind,file]of Object.entries(report.files))li.append(link(file,kind.toUpperCase()),' ');$('reports').append(li);}
  $('coverage').textContent=(atlas.states||[]).map(s=>s.id+': '+count(s.models)+' models').join(' · ')+(Number.isInteger(atlas.unassigned_states)?' · '+count(atlas.unassigned_states)+' unassigned':'');
 }
 async function redraw(viewChange=false){
  const bound=loadSerial,revision=++redrawSerial,v=selected(),current=()=>bound===loadSerial&&revision===redrawSerial&&!destroyed;
  if(!v[state.projection])state.projection=['umap','pca','tsne'].find(k=>v[k]);$('projection').value=state.projection;
  for(const option of $('projection').options)option.disabled=!v[option.value];
  for(const option of $('color').options)option.disabled=option.value==='energy'?!atlas.energy:option.value==='state'?!atlas.state_labels:false;
  if((state.color==='energy'&&!atlas.energy)||(state.color==='state'&&!atlas.state_labels))state.color='cluster';$('color').value=state.color;
  if(viewChange){
   options('cluster',v.representatives.map(r=>({id:r.cluster,label:r.cluster+' · '+count(r.count)})),$('cluster').value);
   options('tree',(atlas.trees||[]).filter(t=>t.view===state.view).map(t=>({id:t.kind,label:t.kind.toUpperCase()})),$('tree').value);
   if(v.tm){await P.react('tm',[{type:'heatmap',z:v.tm.values,x:v.tm.labels,y:v.tm.labels,zmin:0,zmax:1,colorscale:'Viridis'}],{margin:{l:54,r:15,t:10,b:54},yaxis:{autorange:'reversed'}},{responsive:true,displaylogo:false});$('tm-note').textContent='Saved representative TM similarity.';}else{P.purge('tm');$('tm-note').textContent='No saved representative TM matrix for this view.';}
  }
  if(!current())return;
  configurePanels();const highlight=selection();$('selection-note').textContent=highlight.note;
  $('scope').textContent=(dataset.projection_notes?.[state.view]?.[state.projection]||'Saved '+state.projection.toUpperCase()+' projection.')+(state.projection==='pca'&&atlas.pca_variance?' Explained variance: '+atlas.pca_variance.map(x=>(100*x).toFixed(2)+'%').join(' / '):'');
  await P.react('plot',M.traces(atlas,state.view,state.projection,state.color,highlight,state.highlight),{margin:{l:40,r:20,t:12,b:45},paper_bgcolor:'white',xaxis:{title:state.projection.toUpperCase()+' 1'},yaxis:{title:state.projection.toUpperCase()+' 2'},showlegend:state.color!=='energy'&&new Set({cluster:v.labels,method:atlas.methods,state:atlas.state_labels}[state.color]).size<=14,legend:{groupclick:'togglegroup'},uirevision:dataset.id+'|'+state.view+'|'+state.projection},{responsive:true,displaylogo:false});
  if(!current())return;
  const graph=$('plot');graph.removeAllListeners('plotly_click');graph.on('plotly_click',handle(e=>{const i=e.points?.[0]?.customdata;if(Number.isInteger(i)&&i>=0&&i<atlas.models.length)return choose(selected().labels[i],i);}));
  if(viewChange){if(v.representatives.length)await choose($('cluster').value);else await choose(null);}
  await drawTree();saveRoute();
 }
 async function load(id,restore={}){
  const chosen=conf.datasets.find(d=>d.id===id);if(!chosen)throw Error('Unknown saved cohort.');
  const serial=++loadSerial;++structureSerial;++treeSerial;++redrawSerial;dataset=chosen;state.dataset=id;representative=null;body='';model=null;$('cluster').value='';
  atlas=null;loading(true);$('error').hidden=true;$('summary').textContent='Loading saved cohort…';$('coordinate').hidden=true;$('ensemble').hidden=true;if(viewer){viewer.removeAllModels();viewer.render();}else $('viewer').replaceChildren();
  if(panel){panel.clear();panel=null;}P.purge('plot');P.purge('tm');configureDatasets();
  const response=await request(chosen.data);if(!response.ok)throw Error('Saved cohort data could not be loaded.');const text=await response.text();
  if(serial!==loadSerial||destroyed)return;
  if(root.crypto?.subtle){const digest=await root.crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));if([...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('')!==chosen.data_sha256)throw Error('Saved data hash differs from the configured cohort.');}
  if(serial!==loadSerial||destroyed)return;atlas=M.data(JSON.parse(text),chosen);loading(false);
  for(const [key,allowed]of Object.entries({projection:['umap','pca','tsne'],color:['cluster','method','energy','state'],highlight:['none','mcmc','disco','both'],origin:['current','interim'],structureColor:['uniform','cluster','chain','rainbow','confidence']}))if(allowed.includes(restore[key]))state[key]=restore[key];
  if(typeof restore.state==='string')state.state=restore.state;
  state.view=options('view',Object.keys(atlas.views).map(id=>({id,label:id[0].toUpperCase()+id.slice(1)})),restore.view||state.view);
  for(const [id,key]of [['highlight','highlight'],['origin','origin'],['structure-color','structureColor']])$(id).value=state[key];
  $('title').textContent=chosen.target.label;doc.title=chosen.target.label+' · Structure Atlas';$('cohort-badge').textContent=chosen.cohort.label;
  $('summary').textContent=count(atlas.models.length)+' models · '+new Set(atlas.methods).size+' methods · '+chosen.residues.label+' ('+chosen.residues.count+' residues)';
  $('scope-description').textContent=chosen.scope_note||atlas.scope||'Scope metadata unavailable.';$('energy-description').textContent=chosen.energy_note||'Energy provenance is not declared in this display configuration.';$('data-download').href=chosen.data;refreshTables();
  await redraw(true);if(serial===loadSerial){doc.documentElement.dataset.ready='true';doc.documentElement.dataset.cohort=id;}
 }
 async function setSelection(value){if(!['none','mcmc','disco','both'].includes(value.method))throw Error('Unknown panel highlight.');const changed=!!(value.view&&atlas.views[value.view]&&value.view!==state.view);if(changed){++structureSerial;state.view=value.view;$('view').value=value.view;}state.highlight=value.method;state.state=value.state||'all';state.origin=value.origin==='interim'?'interim':'current';$('highlight').value=state.highlight;$('origin').value=state.origin;await redraw(changed);}
 function switchDataset(){const d=conf.datasets.find(d=>d.target.id===$('target').value&&d.cohort.id===$('cohort').value&&d.residues.id===$('range').value)||conf.datasets.find(d=>d.target.id===$('target').value&&d.cohort.id===$('cohort').value)||conf.datasets.find(d=>d.target.id===$('target').value);return load(d.id);}
 const ready=(async()=>{const response=await request('atlas-config.json');if(!response.ok)throw Error('Saved cohort configuration unavailable.');conf=M.config(await response.json());const saved=route();await load(conf.datasets.some(d=>d.id===saved.dataset)?saved.dataset:conf.datasets[0].id,saved);
  for(const id of ['target','cohort','range'])listen($(id),'change',handle(switchDataset));
  for(const id of ['projection','color'])listen($(id),'change',handle(()=>{state[id]=$(id).value;return redraw();}));
  listen($('view'),'change',handle(()=>{++structureSerial;state.view=$('view').value;return redraw(true);}));listen($('tree'),'change',handle(drawTree));listen($('cluster'),'change',handle(()=>choose($('cluster').value)));
  for(const id of ['highlight','state','origin'])listen($(id),'change',handle(()=>{state[id]=$(id).value;return redraw();}));listen($('clear-highlight'),'click',handle(()=>setSelection({method:'none'})));
  listen($('structure-color'),'change',handle(()=>{state.structureColor=$('structure-color').value;restyle();}));listen($('reset-camera'),'click',handle(()=>{restyle(true);}));
  if(root.addEventListener){listen(root,'hashchange',handle(()=>{const desired=route();return load(desired.dataset||dataset.id,desired);}));}
 })();ready.catch(fail);
 const api={ready,state:()=>({...state,model:representative?.model||null,source_sha256:dataset?.data_sha256,selection:atlas?selection():null}),selectDataset:load,setSelection,inspectCluster:choose,setStructureColor:mode=>{if(!['uniform','cluster','chain','rainbow','confidence'].includes(mode))throw Error('Unknown structure color.');state.structureColor=mode;$('structure-color').value=mode;restyle();},destroy:()=>{destroyed=true;++loadSerial;++structureSerial;++treeSerial;for(const off of listeners)off();$('plot').removeAllListeners('plotly_click');P.purge('plot');P.purge('tm');if(panel)panel.clear();if(viewer)viewer.removeAllModels();}};
 return api;
}
root.CohortAtlas={start};if(typeof module!=='undefined'&&module.exports)module.exports={start};
if(root.document&&!root.COHORT_ATLAS_NO_AUTOSTART)root.AtlasInspection=start();
})(typeof window!=='undefined'?window:globalThis);
