/* Exact native model inspection and per-cohort manual comparisons. */
(function(root){'use strict';
function create(env){
 const {document:doc,mol,request}=env,M=root.AISManualModels,G=root.CohortGeometry;
 const $=id=>doc.getElementById(id),node=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n};
 const cache=new Map(),sessions=new Map();let dataset,atlas,labels,key,session,viewer,frames=[],serial=0,busy=false,mode='preview',single=null,attempted=null,style='uniform',fallbackBounds=null;
 const host=$('viewer'),status=$('structure-status'),source=$('coordinate');let storage;try{storage=root.sessionStorage}catch{}
 function fresh(){return {members:[],reference:null,hidden:[],overlay:false,single:null,camera:null,highlight:true,only:false}}
 function persist(){if(!session||!key)return;session.camera=viewer?.getView?.()||session.camera;try{storage?.setItem('atlas-inspection-v1|'+root.location.pathname+'|'+key,JSON.stringify(session))}catch{}}
 function restore(k){let s=sessions.get(k);if(!s){try{s=JSON.parse(storage?.getItem('atlas-inspection-v1|'+root.location.pathname+'|'+k)||'null')}catch{}s={...fresh(),...s};if(!Array.isArray(s.members)||s.members.some(x=>typeof x!=='string')||s.members.length>50)s=fresh();sessions.set(k,s)}return s}
 function asset(id){const i=atlas.models.indexOf(id),a=atlas.model_assets[i];if(i<0||!a||a.model!==id)throw Error('Exact model is absent from this cohort');return {...a,...M.descriptor(a),file:env.asset(dataset,a.file)}}
 function roiFor(a,d){const identity=G.atomKey(a,d);if(!identity)return null;return dataset.inspection.rois.find(r=>r.residues.includes(identity))||null}
 function contextColor(d){const base=G.modelColor(M.key(d));return session.highlight?'#'+base.slice(1).match(/../g).map(v=>Math.round(parseInt(v,16)*.3+255*.7).toString(16).padStart(2,'0')).join(''):base}
 function colorFor(f){const base=contextColor(f.descriptor),others=env.atomColors?.(style,f.atoms,env.clusterColor?.(f.descriptor.model),env.confidence?.(f.descriptor.model));return a=>{const roi=roiFor(a,f.descriptor);if(session.highlight&&roi)return roi.color;if(session.highlight)return frames.length===1?'#b8c1c9':base;return style==='uniform'?base:others?others(a):base}}
 function clearGeometry(){if(viewer){viewer.removeAllModels();viewer.render()}else host.replaceChildren();frames=[];source.hidden=true;$('ensemble').hidden=true;host.dataset.modelIds='[]';host.dataset.sourceHashes='[]'}
 function showError(e,clear=false){if(clear)clearGeometry();status.textContent=e.message||String(e);status.dataset.error='true';update()}
 function mount(){if($('inspection-controls'))return;
  const controls=node('div');controls.id='inspection-controls';controls.className='inspection-controls';
  const actions=node('div');actions.className='inspection-actions';
  for(const [id,text,action]of [['inspection-toggle','Add displayed model',()=>single&&toggle(single)],['inspection-show','View selection',()=>showSet()],['inspection-clear','Clear selection',()=>clearSet()]]){const b=node('button',text);b.type='button';b.id=id;b.onclick=()=>run(action);actions.append(b)}
  const options=node('div');options.className='inspection-options';
  for(const [id,text,field]of [['inspection-highlight','Highlight ROIs','highlight'],['inspection-only','Show ROIs only','only']]){const label=node('label'),input=node('input');input.type='checkbox';input.id=id;input.onchange=()=>{session[field]=input.checked;restyle();persist();update()};label.append(input,' '+text);options.append(label)}
  const legend=node('div');legend.id='inspection-roi-legend';legend.setAttribute('aria-label','ROI color legend');
  const referenceLabel=node('label','Alignment reference '),reference=node('select');reference.id='inspection-reference';reference.onchange=()=>run(()=>renderSet([...session.members],reference.value));referenceLabel.append(reference);
  const note=node('p');note.id='inspection-alignment';note.className='detail';
  const details=node('details');details.id='inspection-members';const summary=node('summary','Models in comparison');details.append(summary);const list=node('ul');list.id='inspection-model-list';details.append(list);
  const help=node('p','Ctrl/Command-click adds or removes models. Ordinary clicks preview one model and retain the comparison.');help.className='detail';
  const message=node('p');message.id='inspection-collection-status';message.setAttribute('role','status');message.setAttribute('aria-live','polite');
  host.before(controls);controls.append(actions,options,legend,host,referenceLabel,note,details,help,message);
 }
 function update(){mount();if(!session||!atlas)return;
  $('inspection-highlight').checked=session.highlight;$('inspection-only').checked=session.only;
  for(const id of ['inspection-highlight','inspection-only'])$(id).disabled=!dataset.inspection.rois.length;
  const included=single&&session.members.includes(single);$('inspection-toggle').textContent=included?'Remove displayed model':'Add displayed model';$('inspection-toggle').disabled=busy||mode==='overlay'||!single;
  $('inspection-show').disabled=busy||!session.members.length;$('inspection-clear').disabled=busy||!session.members.length;
  const legend=$('inspection-roi-legend');legend.replaceChildren();legend.append(node('strong','ROIs '));
  for(const r of dataset.inspection.rois){const item=node('span'),swatch=node('i');swatch.style.background=session.highlight?r.color:'#b8c1c9';item.className='inspection-key';item.append(swatch,r.label);legend.append(item)}
  if(!session.highlight)legend.append(node('span',' Highlighting off · model colors shown'));
  const select=$('inspection-reference');select.replaceChildren(...session.members.map(id=>new Option(id,id)));select.value=session.reference||session.members[0]||'';select.disabled=busy||session.members.length<2;
  $('inspection-alignment').textContent='Display alignment: '+dataset.inspection.alignment.label+' · '+dataset.inspection.alignment.residues.length+' Cα residues. Native downloads retain original coordinates.';
  const list=$('inspection-model-list');list.replaceChildren();
  for(const id of session.members){const row=node('li'),visibility=node('input');visibility.type='checkbox';visibility.checked=!session.hidden.includes(id);visibility.setAttribute('aria-label','Show '+id);visibility.onchange=()=>{session.hidden=session.hidden.filter(x=>x!==id);if(!visibility.checked)session.hidden.push(id);restyle();persist();update()};const label=node('label'),swatch=node('i');swatch.style.background=contextColor(asset(id));swatch.className='inspection-swatch';label.append(visibility,swatch,id+(id===session.reference?' · reference':''));const remove=node('button','Remove');remove.type='button';remove.disabled=busy;remove.setAttribute('aria-label','Remove '+id);remove.onclick=()=>run(()=>removeMember(id));row.append(label,remove);list.append(row)}
  const atoms=frames.reduce((n,f)=>n+f.atoms.length,0);$('inspection-collection-status').textContent=session.members.length+'/50 selected · '+atoms.toLocaleString()+'/250,000 displayed atoms · '+(mode==='overlay'?'comparison overlay':'single-model preview')+(busy?' · loading…':'');
  $('inspection-members').querySelector('summary').textContent='Models in comparison ('+session.members.length+')';if(!busy&&status.dataset.error!=='true'&&frames.length){status.textContent=(mode==='overlay'?'Comparison: '+frames.length+' models · reference '+session.reference:'Selected model '+frames[0].descriptor.model+' · native SHA256 '+frames[0].descriptor.sha256.slice(0,12))+(viewer?'':' · Cα trace (2D)')}
 }
 async function run(action){try{await action()}catch(e){showError(e)}}
 async function loadFrame(id){const d=asset(id),k=M.key(d);let f=cache.get(k);if(!f){const text=await M.readCoordinate(d,request),parsed=M.parse(text,d.format);f={descriptor:d,text,parsed};cache.set(k,f)}return {...f,descriptor:d,atoms:f.parsed.atoms.map(a=>({...a,atom:a.name})),fit:M.identityFit(),gl:null}}
 function fallback(reset=false){const visible=frames.filter(f=>mode!=='overlay'||!session.hidden.includes(f.descriptor.model)),all=visible.flatMap(f=>f.atoms.filter(a=>a.name==='CA'&&(!session.only||roiFor(a,f.descriptor))));if(!all.length){host.replaceChildren(node('p','No visible residues. Enable a model or disable ROIs-only.'));return}
  if(reset||!fallbackBounds){const xs=all.map(a=>a.x),ys=all.map(a=>a.y),xmin=Math.min(...xs),ymin=Math.min(...ys),scale=Math.min(352/(Math.max(...xs)-xmin||1),240/(Math.max(...ys)-ymin||1));fallbackBounds={xmin,ymin,scale}}
  const {xmin,ymin,scale}=fallbackBounds,ns='http://www.w3.org/2000/svg',svg=doc.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 400 280');svg.setAttribute('aria-label','Two-dimensional Cα comparison trace');svg.classList.add('trace');
  for(const f of visible){const ca=f.atoms.filter(a=>a.name==='CA'),colors=colorFor(f);for(let i=1;i<ca.length;i++){const a=ca[i-1],b=ca[i];if(a.chain!==b.chain||Number(b.resi)!==Number(a.resi)+1||session.only&&(!roiFor(a,f.descriptor)||!roiFor(b,f.descriptor)))continue;const line=doc.createElementNS(ns,'line');for(const [k,v]of Object.entries({x1:24+(a.x-xmin)*scale,y1:260-(a.y-ymin)*scale,x2:24+(b.x-xmin)*scale,y2:260-(b.y-ymin)*scale,stroke:colors(b),'stroke-width':1.7}))line.setAttribute(k,v);svg.append(line)}}host.replaceChildren(svg);
 }
 function restyle(reset=false){if(!session)return;for(const f of frames){if(!f.gl)continue;const colors=colorFor(f);f.gl.setStyle({},{});f.gl.setStyle({predicate:a=>!session.only||!!roiFor(a,f.descriptor)},{cartoon:{colorfunc:colors}});if(mode==='overlay'&&session.hidden.includes(f.descriptor.model))f.gl.hide();else f.gl.show()}
  if(viewer){if(reset)viewer.zoomTo();viewer.render()}else if(frames.length)fallback(reset);persist();update();
 }
 async function prepared(ids,reference,revision){if(ids.length>50)throw Error('Selection limit: 50 models. Current selection retained.');const fs=[];for(const id of ids){fs.push(await loadFrame(id));if(revision!==serial)throw Error('Superseded selection');M.validateLimits(fs)}
  if(ids.length>1){const ref=fs.find(f=>f.descriptor.model===reference)||fs[0],mask=dataset.inspection.alignment.residues,points=G.fitPoints(ref.atoms,ref.descriptor,mask);for(const f of fs){f.fit=G.rigidFit(G.fitPoints(f.atoms,f.descriptor,mask),points);for(const a of f.atoms)[a.x,a.y,a.z]=M.point([a.x,a.y,a.z],f.fit)}}return fs;
 }
 function commit(fs,nextMode,revision){if(revision!==serial)return false;const camera=viewer?.getView?.()||session.camera;mode=nextMode;const staged=[];
  try{if(new URLSearchParams(root.location.search).get('render')==='cpu')throw Error('CPU fallback requested');if(!viewer)viewer=mol.createViewer(host,{backgroundColor:'white'});for(const f of fs){f.gl=viewer.addModel(f.text,f.descriptor.format);staged.push(f.gl);for(const a of f.gl.selectedAtoms({}))[a.x,a.y,a.z]=M.point([a.x,a.y,a.z],f.fit)}}catch(e){if(viewer){for(const m of staged)viewer.removeModel(m);viewer.removeAllModels();try{viewer.clear()}catch{}}viewer=null;for(const f of fs)f.gl=null}
  if(viewer)for(const f of frames)if(f.gl)viewer.removeModel(f.gl);frames=fs;status.dataset.error='false';
  host.dataset.modelIds=JSON.stringify(frames.map(f=>f.descriptor.model));host.dataset.sourceHashes=JSON.stringify(frames.map(f=>f.descriptor.sha256));
  if(viewer){if(camera)viewer.setView(camera);else viewer.zoomTo()}restyle();
  status.textContent=nextMode==='overlay'?'Comparison: '+frames.length+' models · reference '+session.reference:'Selected model '+frames[0].descriptor.model+' · native SHA256 '+frames[0].descriptor.sha256.slice(0,12);if(!viewer)status.textContent+=' · Cα trace (2D)';
  source.hidden=nextMode==='overlay';if(nextMode!=='overlay'){source.href=frames[0].descriptor.file;source.dataset.modelId=frames[0].descriptor.model;source.dataset.sha256=frames[0].descriptor.sha256}
  $('ensemble').hidden=true;return true;
 }
 async function preview(id){const revision=++serial;attempted=id;busy=true;status.textContent='Loading exact model '+id+'…';update();try{const fs=await prepared([id],id,revision);if(revision!==serial)return;single=id;session.single=id;session.overlay=false;commit(fs,'preview',revision);persist()}catch(e){if(revision===serial)showError(new Error('Model '+id+' could not be loaded: '+(e.message||String(e))),true)}finally{if(revision===serial){busy=false;update()}}}
 async function renderSet(ids,reference){const revision=++serial;busy=true;update();try{const fs=await prepared(ids,reference,revision);if(revision!==serial)return false;session.members=[...ids];session.reference=ids.includes(reference)?reference:ids[0]||null;session.hidden=session.hidden.filter(id=>ids.includes(id));session.overlay=true;commit(fs,'overlay',revision);persist();return true}finally{if(revision===serial){busy=false;update()}}}
 async function showSet(){if(session.members.length)return renderSet(session.members,session.reference||session.members[0])}
 async function toggle(id){let members=[...session.members];if(members.includes(id))return removeMember(id);if(!members.length&&mode==='preview'&&single&&single!==id)members.push(single);members.push(id);return renderSet(members,session.reference||members[0])}
 async function removeMember(id){const ids=session.members.filter(x=>x!==id);if(!ids.length)return clearSet();return renderSet(ids,ids.includes(session.reference)?session.reference:ids[0])}
 function clearSet(){++serial;busy=false;session.members=[];session.reference=null;session.hidden=[];session.overlay=false;if(mode==='overlay'){clearGeometry();single=null;session.single=null;mode='preview';status.textContent='Comparison cleared. Select a model.'}persist();update()}
 function begin(d){persist();++serial;busy=true;if(dataset&&(dataset.target.id!==d.target.id||dataset.cohort.id!==d.cohort.id))clearGeometry();status.textContent='Loading model cohort…';update()}
 async function scope(d,a,l){persist();const changed=JSON.stringify(dataset?.inspection?.alignment)!==JSON.stringify(d.inspection.alignment);++serial;busy=false;dataset=d;atlas=a;labels=l;key=JSON.stringify([d.target.id,d.cohort.id,M.sha256(new TextEncoder().encode(a.model_assets.map(x=>M.key(x)).sort().join('\n')))]);const next=restore(key),same=session===next;session=next;single=a.models.includes(session.single)?session.single:null;session.members=session.members.filter(id=>a.models.includes(id));session.reference=session.members.includes(session.reference)?session.reference:session.members[0]||null;mount();update();if(same&&frames.length&&!changed){restyle();return}clearGeometry();fallbackBounds=null;if(session.overlay&&session.members.length)await showSet();else if(single)await preview(single);else if(a.models.length)await preview(a.models[0]);}
 async function pick(index,event={}){const id=atlas.models[index];if(!id)return;try{if(event.ctrlKey||event.metaKey){event.preventDefault?.();return await toggle(id)}return await preview(id)}catch(e){if(e.message!=='Superseded selection')showError(e);return false}}
 function state(){return {mode,single_model:single,requested_model:attempted,members:[...(session?.members||[])],reference:session?.reference,roi_highlight:session?.highlight,roi_only:session?.only,camera:viewer?.getView?.()||session?.camera||null,renderer:viewer?'webgl':'cpu',rendered:frames.map(f=>({model:f.descriptor.model,sha256:f.descriptor.sha256,atoms:f.gl?f.gl.selectedAtoms({}).length:f.atoms.length,visible:mode!=='overlay'||!session.hidden.includes(f.descriptor.model),ca_samples:(f.gl?f.gl.selectedAtoms({atom:'CA'}):f.atoms.filter(a=>a.name==='CA')).slice(0,3).map(a=>[a.x,a.y,a.z])}))}}
 root.addEventListener?.('pagehide',persist);
 return {begin,scope,pick,preview,showSet,toggle,clearSet,restyle,compare:ids=>renderSet([...new Set(ids)],session.reference||ids[0]),reference:id=>renderSet(session.members,id),setStyle(value){style=value;restyle()},reset(){fallbackBounds=null;restyle(true)},state,destroy(){++serial;persist();root.removeEventListener?.('pagehide',persist);clearGeometry()}};
}
root.CohortInspection={create};if(typeof module!=='undefined'&&module.exports)module.exports={create};
})(typeof window==='undefined'?globalThis:window);
