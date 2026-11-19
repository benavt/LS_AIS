/* Inspection of saved exact-cohort Cα distance maps. No scientific computation. */
(function(root){
'use strict';
const SCHEMA='atlas-distance-maps-v1',STATE_SCHEMA='atlas-distance-maps-display-v1';
const METRICS=['variance','median'],PALETTES=['Magma','Viridis','Cividis','Inferno'];
const DEFAULTS={schema:STATE_SCHEMA,metric:'variance',scale:'linear',palettes:{variance:'Magma',median:'Viridis'},ranges:{variance:null,median:null}};
const STOPS={
 Magma:['#000004','#1c1044','#4f127b','#812581','#b5367a','#e55063','#fb8761','#fec287','#fcfdbf'],
 Viridis:['#440154','#472d7b','#3b528b','#2c728e','#21918c','#28ae80','#5ec962','#addc30','#fde725'],
 Cividis:['#00224e','#123570','#3b496c','#575d6d','#707173','#8a8678','#a59c74','#c3b369','#e1cc55','#fee838'],
 Inferno:['#000004','#1f0c48','#550f6d','#88226a','#b63655','#e35933','#f98c0a','#f9c932','#fcffa4']
};
const NULL_COLOR='#c7cbd1',HASH=/^[a-f0-9]{64}$/;
function need(ok,note){if(!ok)throw Error(note);}
function clone(v){return JSON.parse(JSON.stringify(v));}
function same(a,b){return JSON.stringify(a)===JSON.stringify(b);}
function finite(v){return typeof v==='number'&&Number.isFinite(v);}
function sha256(bytes){const helper=root.AISExplorerTMStates||(typeof module!=='undefined'&&module.exports?require('./ais_explorer_tm_states.js'):null);need(typeof helper?.sha256==='function','Distance maps require the shared SHA-256 verifier.');return helper.sha256(bytes);}
function validateContext(context){
 need(context&&typeof context.datasetId==='string'&&context.datasetId.length>0&&typeof context.scope_id==='string'&&context.scope_id.length>0&&HASH.test(context.cohort_data_sha256||'')&&Number.isInteger(context.model_count)&&context.model_count>0,'The active distance-map cohort is not verified.');
 need(Array.isArray(context.residue_labels)&&context.residue_labels.length>0&&context.residue_labels.every(v=>typeof v==='string'&&v.length>0)&&new Set(context.residue_labels).size===context.residue_labels.length,'The active distance-map residue order is not verified.');
 for(const key of ['model_order_sha256','sequence_sha256','presentation_data_sha256'])if(context[key]!==undefined)need(HASH.test(context[key]),'Invalid active '+key+'.');
 return context;
}
function validateBinding(binding,context){
 validateContext(context);
 need(binding&&typeof binding.file==='string'&&/^[A-Za-z0-9_][A-Za-z0-9_./-]*\.json$/.test(binding.file)&&!binding.file.split('/').includes('..')&&HASH.test(binding.sha256||''),'Unsafe or unhashed distance-map file.');
 need(binding.scope_id===context.scope_id&&binding.cohort_data_sha256===context.cohort_data_sha256&&binding.model_count===context.model_count&&same(binding.residue_labels,context.residue_labels),'Saved distance maps do not match the exact active model and residue cohort.');
 return binding;
}
function validatePayload(p,binding,context){
 validateBinding(binding,context);
 need(p?.schema===SCHEMA,'Unsupported saved distance-map schema.');
 const c=p.cohort;
 need(c&&c.id===(binding.cohort_id||context.datasetId)&&c.scope_id===context.scope_id&&typeof c.target==='string'&&c.target.length>0&&c.model_count===context.model_count&&c.cohort_data_sha256===context.cohort_data_sha256&&HASH.test(c.model_order_sha256||'')&&HASH.test(c.sequence_sha256||''),'Saved distance-map cohort identity differs.');
 if(context.target!==undefined)need(c.target===context.target,'Saved distance-map target differs.');
 for(const key of ['model_order_sha256','sequence_sha256'])if(context[key]!==undefined)need(c[key]===context[key],'Saved distance-map '+key+' differs.');
 const residues=p.residues,n=context.residue_labels.length;
 need(Array.isArray(residues)&&residues.length===n,'Saved distance-map residue count differs.');
 const identities=new Set();let previousPosition=0;
 for(const [i,r]of residues.entries()){
  need(r&&typeof r.chain==='string'&&r.chain.length>0&&Number.isInteger(r.number)&&typeof r.insertion_code==='string'&&Number.isInteger(r.position)&&r.position>previousPosition&&typeof r.label==='string'&&r.label.length>0&&r.label===context.residue_labels[i]&&!identities.has(JSON.stringify([r.chain,r.number,r.insertion_code])),'Saved distance-map residue identity or order differs.');identities.add(JSON.stringify([r.chain,r.number,r.insertion_code]));previousPosition=r.position;
 }
 need(p.matrices&&Array.isArray(p.matrices.variance),'Saved variance matrix is unavailable.');
 for(const metric of METRICS){
  const m=p.matrices[metric];if(metric==='median'&&m===undefined)continue;
  need(Array.isArray(m)&&m.length===n&&m.every(row=>Array.isArray(row)&&row.length===n),'Saved '+metric+' matrix dimensions differ.');
  let max=0;
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){const v=m[i][j];need(v===null||(finite(v)&&v>=0),'Invalid saved '+metric+' value.');need(v===m[j][i],'Saved '+metric+' matrix is not symmetric.');if(i!==j&&v!==null)max=Math.max(max,v);if(i===j)need(v===0||v===null,'Saved distance-map diagonal differs.');}
  const statistic=p.statistics?.[metric],expected=metric==='variance'?'Å²':'Å';
  need(statistic?.units===expected&&statistic.statistic===(metric==='variance'?'population-variance':'median')&&(metric!=='variance'||statistic.ddof===0),'Saved distance-map statistic or units differ.');
  need(p.display?.[metric]?.palette===DEFAULTS.palettes[metric]&&same(p.display[metric].range,[0,max]),'Saved distance-map full range differs.');
 }
 need(p.display?.scale==='linear'&&p.display.log==='log1p','Saved distance-map scale contract differs.');
 need(p.provenance&&typeof p.provenance==='object'&&!Array.isArray(p.provenance),'Saved distance-map provenance is missing.');
 return p;
}
function bytesOf(value){if(value instanceof Uint8Array)return value;if(value instanceof ArrayBuffer)return new Uint8Array(value);if(typeof value==='string')return new TextEncoder().encode(value);throw Error('The distance-map reader must return saved bytes.');}
function createLoader(bindings={},reader=async(file,_hash,signal)=>{const response=await root.fetch(file,{cache:'no-cache',signal});need(response.ok,'Saved distance maps are unavailable.');return new Uint8Array(await response.arrayBuffer());}){
 const entries=bindings.datasets||bindings;
 return{enabled:!!entries&&Object.keys(entries).length>0,async load(context,{signal}={}){
  try{
   validateContext(context);const binding=entries[context.datasetId];need(binding,'No saved distance maps match this exact active model and residue cohort.');validateBinding(binding,context);
   const raw=bytesOf(await reader(binding.file,binding.sha256,signal));need(!signal?.aborted,'Distance-map request was cancelled.');need(sha256(raw)===binding.sha256,'Saved distance-map file hash differs.');
   const payload=JSON.parse(new TextDecoder().decode(raw));validatePayload(payload,binding,context);return{status:'available',payload,note:'',binding:clone(binding)};
  }catch(error){return{status:'unavailable',payload:null,note:error.message||'Saved distance maps are unavailable.'};}
 }};
}
function displayState(value=DEFAULTS){
 need(value&&typeof value==='object'&&!Array.isArray(value),'Invalid distance-map display state.');
 const state={schema:STATE_SCHEMA,metric:value.metric??DEFAULTS.metric,scale:value.scale??DEFAULTS.scale,palettes:{...DEFAULTS.palettes,...value.palettes},ranges:{...DEFAULTS.ranges,...value.ranges}};
 need((value.schema===undefined||value.schema===STATE_SCHEMA)&&METRICS.includes(state.metric)&&['linear','log'].includes(state.scale),'Invalid distance-map metric or scale.');
 for(const metric of METRICS){need(PALETTES.includes(state.palettes[metric]),'Invalid distance-map palette.');const range=state.ranges[metric];need(range===null||(Array.isArray(range)&&range.length===2&&range.every(v=>finite(v)&&v>=0)&&range[1]>range[0]),'Invalid distance-map range override.');}
 return clone(state);
}
function patchState(previous,patch){return displayState({...previous,...patch,palettes:{...previous.palettes,...patch.palettes},ranges:{...previous.ranges,...patch.ranges}});}
function effectiveRange(payload,state,metric=state.metric){return [...(state.ranges[metric]||payload.display[metric].range)];}
function transform(value,scale){return scale==='log'?Math.log1p(value):value;}
function normalize(value,range,scale='linear'){
 if(value===null)return null;need(finite(value)&&value>=0&&Array.isArray(range)&&range.length===2&&range.every(finite)&&range[0]>=0&&range[1]>=range[0]&&['linear','log'].includes(scale),'Invalid distance-map color value.');
 const lo=transform(range[0],scale),hi=transform(range[1],scale);return hi===lo?0:Math.max(0,Math.min(1,(transform(value,scale)-lo)/(hi-lo)));
}
function color(palette,t){if(t===null)return NULL_COLOR;need(PALETTES.includes(palette)&&finite(t),'Invalid distance-map color.');const stops=STOPS[palette],f=Math.max(0,Math.min(1,t))*(stops.length-1),a=Math.floor(f),b=Math.min(a+1,stops.length-1),mix=f-a;const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));return '#'+rgb(stops[a]).map((v,i)=>Math.round(v+(rgb(stops[b])[i]-v)*mix).toString(16).padStart(2,'0')).join('');}
function colorbarTicks(range,scale='linear',count=5){const lo=transform(range[0],scale),hi=transform(range[1],scale);return Array.from({length:range[0]===range[1]?1:count},(_,i)=>{const fraction=range[0]===range[1]?0:i/(count-1),v=lo+(hi-lo)*fraction;return{fraction,value:i===0?range[0]:i===count-1?range[1]:scale==='log'?Math.expm1(v):v};});}
function separators(residues){const out=[];for(let i=1;i<residues.length;i++){const a=residues[i-1],b=residues[i];if(a.chain!==b.chain)out.push({index:i,kind:'chain'});else if(b.position!==a.position+1)out.push({index:i,kind:'gap'});}return out;}
function fullView(n){return{x:0,y:0,span:n};}
function viewState(value,n){need(value&&finite(value.x)&&finite(value.y)&&finite(value.span)&&value.span>=1&&value.span<=n&&value.x>=0&&value.y>=0&&value.x+value.span<=n+1e-9&&value.y+value.span<=n+1e-9,'Invalid distance-map viewport.');return{x:value.x,y:value.y,span:value.span};}
function boundedView(value,n){const span=Math.max(1,Math.min(n,value.span));return{x:Math.max(0,Math.min(n-span,value.x)),y:Math.max(0,Math.min(n-span,value.y)),span};}
function zoomView(view,factor,at={x:.5,y:.5},n){need(finite(factor)&&factor>0,'Invalid distance-map zoom.');const span=Math.max(1,Math.min(n,view.span*factor));return boundedView({x:view.x+(view.span-span)*at.x,y:view.y+(view.span-span)*at.y,span},n);}
function geometry(width){const left=64,top=14,right=16,bottom=68,size=Math.max(1,width-left-right);return{width,height:top+size+bottom,left,top,size,cell:(n)=>size/n};}
function sparseTicks(n,start=0,span=n,limit=7){const first=Math.max(0,Math.ceil(start-.5)),last=Math.min(n-1,Math.floor(start+span-.5));if(first>last)return[];const count=Math.min(limit,last-first+1);return [...new Set(Array.from({length:count},(_,i)=>count===1?first:Math.round(first+(last-first)*i/(count-1))))];}
function rawHover(payload,metric,row,column){const value=payload.matrices[metric][row][column];return{row,column,x:payload.residues[column].label,y:payload.residues[row].label,value,units:payload.statistics[metric].units};}
function hasOverrides(state){return METRICS.some(m=>state.palettes[m]!==DEFAULTS.palettes[m]||state.ranges[m]!==null);}
function createController({loader,onChange=()=>{}}){
 need(loader&&typeof loader.load==='function','A distance-map loader is required.');
 let state=displayState(),view=null,result={status:'idle',payload:null,note:'Choose an analysis to inspect saved distance maps.'},context=null,generation=0,abort=null,destroyed=false,lastContextKey=null,retainedView=null;
 const snapshot=()=>({state:clone(state),view:view?{...view}:null,context:context?clone(context):null,result});
 const emit=()=>onChange(snapshot());
 const contextKey=value=>value?JSON.stringify(['datasetId','scope_id','cohort_data_sha256','model_count','residue_labels','target','model_order_sha256','sequence_sha256'].map(key=>value[key]??null)):null;
 return{getState:()=>clone(state),getView:()=>view?{...view}:null,getSnapshot:snapshot,
  async setContext(next){
   const key=contextKey(next),changed=lastContextKey!==null&&key!==lastContextKey;
   if(changed){state=displayState();retainedView=null;}
   if(key===lastContextKey&&context&&result.status==='available'){context=clone(next);return snapshot();}
   lastContextKey=key;
   const ticket=++generation;abort?.abort();abort=typeof AbortController==='function'?new AbortController():null;context=next?clone(next):null;view=null;
   result={status:'loading',payload:null,note:'Verifying exact-cohort distance maps…'};emit();
   let loaded;try{loaded=await loader.load(context,{signal:abort?.signal});}catch(error){loaded={status:'unavailable',payload:null,note:error.message};}
   if(destroyed||ticket!==generation)return snapshot();
   result=loaded;if(result.status==='available'&&result.payload){view=retainedView?viewState(retainedView,result.payload.residues.length):fullView(result.payload.residues.length);retainedView={...view};if(!result.payload.matrices[state.metric])state={...state,metric:'variance'};}else result={status:'unavailable',payload:null,note:loaded.note||'Saved distance maps are unavailable for this exact cohort.'};
   emit();return snapshot();
  },
  clear(note='Saved distance maps are unavailable for this exact cohort.'){++generation;abort?.abort();if(view)retainedView={...view};context=null;view=null;result={status:'unavailable',payload:null,note};emit();},
  setState(patch){const next=patchState(state,patch);need(!result.payload||!!result.payload.matrices[next.metric],'The requested saved distance-map metric is unavailable.');state=next;emit();return clone(state);},
  setView(next){need(result.payload,'No saved distance-map viewport is available.');view=viewState(next,result.payload.residues.length);retainedView={...view};emit();return{...view};},
  resetDisplay(){state=displayState();emit();return clone(state);},
  resetView(){if(result.payload){view=fullView(result.payload.residues.length);retainedView={...view};}emit();return view?{...view}:null;},
  destroy(){destroyed=true;++generation;abort?.abort();}
 };
}
function parseRoute(params){try{const value={};if(params.has('map_metric'))value.metric=params.get('map_metric');if(params.has('map_scale'))value.scale=params.get('map_scale');for(const metric of METRICS){if(params.has('map_'+metric+'_palette'))(value.palettes??={})[metric]=params.get('map_'+metric+'_palette');if(params.has('map_'+metric+'_range')){const parts=params.get('map_'+metric+'_range').split(',');need(parts.length===2&&parts.every(v=>v.trim()!==''),'Invalid distance-map range parameter.');(value.ranges??={})[metric]=parts.map(Number);}}return{valid:true,state:displayState(value)};}catch(error){return{valid:false,state:displayState(),note:'Invalid distance-map display parameters: '+error.message};}}
function routeParams(value){const s=displayState(value),p=new URLSearchParams();p.set('map_metric',s.metric);p.set('map_scale',s.scale);for(const metric of METRICS){if(s.palettes[metric]!==DEFAULTS.palettes[metric])p.set('map_'+metric+'_palette',s.palettes[metric]);if(s.ranges[metric])p.set('map_'+metric+'_range',s.ranges[metric].join(','));}return p;}
function updateRoute(hash,value){const split=hash.indexOf('?'),raw=hash.replace(/^#/,''),flat=split<0&&(raw===''||raw.includes('=')||raw.includes('&')),base=flat?'#':split<0?hash:hash.slice(0,split),p=new URLSearchParams(flat?raw:split<0?'':hash.slice(split+1));for(const key of [...p.keys()])if(/^map_(?:metric|scale|(?:variance|median)_(?:palette|range))$/.test(key))p.delete(key);for(const[k,v]of routeParams(value))p.set(k,v);return base+(flat?'':'?')+p.toString();}
function csv(payload,metric='variance'){need(METRICS.includes(metric)&&payload.matrices[metric],'Saved distance-map metric is unavailable.');const q=s=>'"'+String(s).replace(/"/g,'""')+'"';return ['residue,'+payload.residues.map(r=>q(r.label)).join(','),...payload.matrices[metric].map((row,i)=>q(payload.residues[i].label)+','+row.map(v=>v===null?'':String(v)).join(','))].join('\n')+'\n';}
function shortNumber(v){if(v===0)return'0';return Number(v.toPrecision(4)).toString();}
function escapeXML(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));}
function svg(payload,value=DEFAULTS,viewport=null,width=900){
 const state=displayState(value),n=payload.residues.length,view=viewState(viewport||fullView(n),n),g=geometry(width),range=effectiveRange(payload,state),metric=state.metric,palette=state.palettes[metric],unit=payload.statistics[metric].units,height=g.height+105;
 const out=[`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeXML(metric+' Cα distances, '+unit)}"><title>${escapeXML(payload.cohort.id+' · '+metric+' · '+unit+' · '+state.scale)}</title><rect width="100%" height="100%" fill="white"/><defs><clipPath id="map-clip"><rect x="${g.left}" y="${g.top}" width="${g.size}" height="${g.size}"/></clipPath></defs><g clip-path="url(#map-clip)" shape-rendering="crispEdges">`];
 for(let i=Math.floor(view.y);i<Math.min(n,Math.ceil(view.y+view.span));i++)for(let j=Math.floor(view.x);j<Math.min(n,Math.ceil(view.x+view.span));j++){const v=payload.matrices[metric][i][j],size=g.size/view.span;out.push(`<rect x="${g.left+(j-view.x)*size}" y="${g.top+(i-view.y)*size}" width="${size}" height="${size}" fill="${color(palette,normalize(v,range,state.scale))}"/>`);}
 for(const boundary of separators(payload.residues)){const x=g.left+(boundary.index-view.x)*g.size/view.span,y=g.top+(boundary.index-view.y)*g.size/view.span;out.push(`<path d="M${x} ${g.top}v${g.size}M${g.left} ${y}h${g.size}" fill="none" stroke="white" stroke-width="${boundary.kind==='chain'?2:1}"${boundary.kind==='gap'?' stroke-dasharray="3 3"':''}/>`);}
 out.push('</g><g font-family="sans-serif" font-size="12" fill="#334155">');
 for(const index of sparseTicks(n,view.x,view.span)){const x=g.left+(index+.5-view.x)*g.size/view.span;out.push(`<text transform="translate(${x} ${g.top+g.size+13}) rotate(45)" text-anchor="start">${escapeXML(payload.residues[index].label)}</text>`);}
 for(const index of sparseTicks(n,view.y,view.span)){const y=g.top+(index+.5-view.y)*g.size/view.span;out.push(`<text x="${g.left-8}" y="${y+4}" text-anchor="end">${escapeXML(payload.residues[index].label)}</text>`);}
 const barY=g.height+18,barWidth=Math.min(400,g.size);for(let i=0;i<200;i++)out.push(`<rect x="${g.left+i*barWidth/200}" y="${barY}" width="${barWidth/200+1}" height="12" fill="${color(palette,i/199)}"/>`);
 for(const tick of colorbarTicks(range,state.scale))out.push(`<text x="${g.left+tick.fraction*barWidth}" y="${barY+30}" text-anchor="middle">${escapeXML(shortNumber(tick.value))}</text>`);
 out.push(`<text x="${g.left}" y="${barY+56}">${escapeXML((metric==='variance'?'Population variance':'Median distance')+' ('+unit+') · '+state.scale+(hasOverrides(state)?' · display overrides':''))}</text><text x="${g.left}" y="${barY+77}">${escapeXML(payload.cohort.model_count+' models · '+n+' residues · exact saved cohort · gray = missing')}</text></g></svg>`);return out.join('');
}
function createWidget({container,loader,onStateChange=()=>{},ready:fontReady}={}){
 need(container?.ownerDocument,'A distance-map container is required.');const doc=container.ownerDocument,env=doc.defaultView||root;
 const nodes={},listeners=[];let destroyed=false,measurement=null,drawReady=false,hover=null,drag=null;
 function element(tag,cls,text,parent){const el=doc.createElement(tag);if(cls)el.className=cls;if(text!==undefined)el.textContent=text;parent?.append(el);return el;}
 function listen(node,event,fn,options){node.addEventListener(event,fn,options);listeners.push(()=>node.removeEventListener(event,fn,options));}
 const shell=element('section','atlas-distance-maps',undefined,container);shell.setAttribute('aria-label','Saved Cα distance maps');
 const heading=element('div','adm-heading',undefined,shell);element('h3',null,'Cα distance maps',heading);nodes.override=element('span','adm-override','Display overrides',heading);nodes.override.hidden=true;
 nodes.scope=element('p','adm-scope','Exact active model and residue cohort',shell);
 nodes.status=element('p','adm-status','Choose an analysis to inspect saved distance maps.',shell);nodes.status.setAttribute('role','status');
 nodes.body=element('div','adm-body',undefined,shell);nodes.body.hidden=true;
 const toolbar=element('div','adm-toolbar',undefined,nodes.body),tabs=element('div','adm-tabs',undefined,toolbar);tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','Saved distance statistic');
 for(const metric of METRICS){const b=element('button',null,metric==='variance'?'Variance':'Median distance',tabs);b.type='button';b.setAttribute('role','tab');b.setAttribute('aria-selected',String(metric==='variance'));nodes[metric]=b;listen(b,'click',()=>controller.setState({metric}));listen(b,'keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const available=METRICS.filter(m=>!nodes[m].hidden),index=available.indexOf(metric),next=event.key==='Home'?available[0]:event.key==='End'?available[available.length-1]:available[(index+(event.key==='ArrowRight'?1:-1)+available.length)%available.length];controller.setState({metric:next});nodes[next].focus();});}
 const scale=element('div','adm-scale',undefined,toolbar);scale.setAttribute('role','group');scale.setAttribute('aria-label','Color scale');
 for(const mode of ['linear','log']){const b=element('button',null,mode==='linear'?'Linear':'Log',scale);b.type='button';b.title=mode==='log'?'log1p(value / 1 unit); hover and downloads retain raw values':'Linear color scale';b.setAttribute('aria-pressed',String(mode==='linear'));nodes[mode]=b;listen(b,'click',()=>controller.setState({scale:mode}));}
 const chartLine=element('div','adm-chart-line',undefined,nodes.body),figure=element('figure','adm-figure',undefined,chartLine);nodes.chart=element('div','adm-chart',undefined,figure);nodes.chart.tabIndex=0;nodes.chart.setAttribute('role','img');nodes.chart.setAttribute('aria-label','Square Cα matrix. Scroll to zoom, drag to pan, arrow keys inspect cells, Shift and arrow keys pan.');
 nodes.canvas=element('canvas',null,undefined,nodes.chart);nodes.canvas.setAttribute('aria-hidden','true');nodes.axes=doc.createElementNS('http://www.w3.org/2000/svg','svg');nodes.axes.setAttribute('aria-hidden','true');nodes.chart.append(nodes.axes);
 nodes.hover=element('output','adm-hover','Hover over a cell for exact residues and raw value.',figure);nodes.hover.setAttribute('aria-live','polite');
 const side=element('div','adm-inspection',undefined,chartLine);element('h4',null,'Inspect saved values',side);element('p','adm-help','Scroll to zoom · Drag to pan\nArrow keys inspect · Shift + arrows pan',side);
 const viewTools=element('div','adm-view-tools',undefined,side);
 for(const[text,label,action]of [['+','Zoom in',()=>zoom(.7)],['−','Zoom out',()=>zoom(1/.7)],['Reset view','Reset map zoom and pan',()=>controller.resetView()]]){const b=element('button',null,text,viewTools);b.type='button';b.setAttribute('aria-label',label);listen(b,'click',action);}
 nodes.viewNote=element('p','adm-view-note','Full matrix',side);
 nodes.legendTitle=element('p','adm-legend-title',undefined,side);nodes.legend=element('div','adm-colorbar',undefined,side);nodes.legend.setAttribute('role','img');nodes.ticks=element('div','adm-colorbar-ticks',undefined,side);
 const missing=element('p','adm-missing',undefined,side);element('i',null,undefined,missing);missing.append(doc.createTextNode('Missing value'));nodes.scaleNote=element('p','adm-scale-note',undefined,side);
 const downloads=element('div','adm-downloads',undefined,side);element('h4',null,'Download',downloads);
 for(const[text,kind]of [['CSV · raw values','csv'],['JSON · both maps','json'],['SVG · current view','svg']]){const b=element('button',null,text,downloads);b.type='button';listen(b,'click',()=>download(kind));}
 const advanced=element('details','adm-advanced',undefined,nodes.body);element('summary',null,'Display settings',advanced);const fields=element('div','adm-advanced-fields',undefined,advanced);
 const paletteLabel=element('label',null,'Palette',fields);nodes.palette=element('select',null,undefined,paletteLabel);for(const name of PALETTES){const option=element('option',null,name,nodes.palette);option.value=name;}listen(nodes.palette,'change',()=>controller.setState({palettes:{[controller.getState().metric]:nodes.palette.value}}));
 for(const[key,label]of [['min','Minimum'],['max','Maximum']]){const field=element('label',null,label,fields);nodes[key]=element('input',null,undefined,field);nodes[key].type='number';nodes[key].min='0';nodes[key].step='any';}
 const apply=element('button',null,'Apply range',fields);apply.type='button';listen(apply,'click',()=>{try{need(nodes.min.value!==''&&nodes.max.value!=='','Enter both range limits.');controller.setState({ranges:{[controller.getState().metric]:[Number(nodes.min.value),Number(nodes.max.value)]}});nodes.rangeError.textContent='';}catch(error){nodes.rangeError.textContent=error.message;}});
 const reset=element('button',null,'Reset display',fields);reset.type='button';listen(reset,'click',()=>{nodes.rangeError.textContent='';controller.resetDisplay();});nodes.rangeError=element('p','adm-range-error','',advanced);nodes.rangeError.setAttribute('role','alert');
 element('p','adm-contract','Axes use the same ordered residues with uniform square cells. Solid lines separate chains; dashed lines mark sequence gaps. Values and colorbar labels keep their saved units. Display controls preserve the structure selection and camera.',nodes.body);
 const controller=createController({loader,onChange(snapshot){render(snapshot);onStateChange(snapshot.state,snapshot);}});
 function zoom(factor,at){const s=controller.getSnapshot();if(s.result.payload)controller.setView(zoomView(s.view,factor,at,s.result.payload.residues.length));}
 function local(event){if(!measurement)return null;const rect=nodes.chart.getBoundingClientRect(),x=(event.clientX-rect.left)*measurement.width/rect.width,y=(event.clientY-rect.top)*measurement.height/rect.height;return{x:(x-measurement.left)/measurement.size,y:(y-measurement.top)/measurement.size};}
 function showHover(row,column){const s=controller.getSnapshot(),p=s.result.payload;if(!p)return;row=Math.max(0,Math.min(p.residues.length-1,row));column=Math.max(0,Math.min(p.residues.length-1,column));hover={row,column};const h=rawHover(p,s.state.metric,row,column);nodes.hover.textContent=h.x+' × '+h.y+' · '+(h.value===null?'Missing':String(h.value)+' '+h.units)+' · column '+column+', row '+row;}
 listen(nodes.chart,'pointermove',event=>{const at=local(event),s=controller.getSnapshot();if(!at||!s.result.payload)return;if(drag){const dx=(event.clientX-drag.x)/nodes.chart.getBoundingClientRect().width*measurement.width/measurement.size*drag.view.span,dy=(event.clientY-drag.y)/nodes.chart.getBoundingClientRect().height*measurement.height/measurement.size*drag.view.span;controller.setView(boundedView({x:drag.view.x-dx,y:drag.view.y-dy,span:drag.view.span},s.result.payload.residues.length));return;}if(at.x>=0&&at.x<1&&at.y>=0&&at.y<1)showHover(Math.floor(s.view.y+at.y*s.view.span),Math.floor(s.view.x+at.x*s.view.span));});
 listen(nodes.chart,'pointerdown',event=>{const at=local(event),s=controller.getSnapshot();if(!at||!s.result.payload||event.button!==0||at.x<0||at.x>1||at.y<0||at.y>1)return;drag={x:event.clientX,y:event.clientY,view:s.view};nodes.chart.setPointerCapture?.(event.pointerId);nodes.chart.classList.add('is-panning');});
 for(const name of ['pointerup','pointercancel','lostpointercapture'])listen(nodes.chart,name,()=>{drag=null;nodes.chart.classList.remove('is-panning');});
 listen(nodes.chart,'wheel',event=>{const at=local(event);if(!at||at.x<0||at.x>1||at.y<0||at.y>1)return;event.preventDefault();zoom(event.deltaY<0?.8:1.25,at);},{passive:false});
 listen(nodes.chart,'keydown',event=>{const s=controller.getSnapshot(),p=s.result.payload;if(!p)return;const d={ArrowLeft:[0,-1],ArrowRight:[0,1],ArrowUp:[-1,0],ArrowDown:[1,0]}[event.key];if(d){event.preventDefault();if(event.shiftKey)controller.setView(boundedView({...s.view,x:s.view.x+d[1]*s.view.span*.1,y:s.view.y+d[0]*s.view.span*.1},p.residues.length));else showHover((hover?.row??Math.floor(s.view.y+s.view.span/2))+d[0],(hover?.column??Math.floor(s.view.x+s.view.span/2))+d[1]);}else if(['+','=','-','Home'].includes(event.key)){event.preventDefault();if(event.key==='Home')controller.resetView();else zoom(event.key==='-'?1/.7:.7);}});
 function appendSVG(tag,attrs,text){const el=doc.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;nodes.axes.append(el);return el;}
 function draw(snapshot){
  if(!drawReady||destroyed||!snapshot.result.payload||nodes.body.hidden)return;
  const {payload:p}=snapshot.result,{state,view}=snapshot,n=p.residues.length,width=Math.max(240,nodes.chart.getBoundingClientRect().width||600),g=geometry(width),dpr=Math.min(2,env.devicePixelRatio||1);measurement=g;
  nodes.chart.style.aspectRatio=g.width+'/'+g.height;nodes.canvas.width=Math.ceil(g.width*dpr);nodes.canvas.height=Math.ceil(g.height*dpr);const ctx=nodes.canvas.getContext('2d');if(!ctx)return;
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,g.width,g.height);ctx.save();ctx.beginPath();ctx.rect(g.left,g.top,g.size,g.size);ctx.clip();const range=effectiveRange(p,state),cell=g.size/view.span;
  for(let i=Math.floor(view.y);i<Math.min(n,Math.ceil(view.y+view.span));i++)for(let j=Math.floor(view.x);j<Math.min(n,Math.ceil(view.x+view.span));j++){ctx.fillStyle=color(state.palettes[state.metric],normalize(p.matrices[state.metric][i][j],range,state.scale));ctx.fillRect(g.left+(j-view.x)*cell,g.top+(i-view.y)*cell,cell+.3,cell+.3);}ctx.restore();
  nodes.axes.replaceChildren();nodes.axes.setAttribute('viewBox','0 0 '+g.width+' '+g.height);
  appendSVG('rect',{x:g.left,y:g.top,width:g.size,height:g.size,fill:'none',stroke:'currentColor','stroke-opacity':'.2'});
  for(const boundary of separators(p.residues)){const offsetX=(boundary.index-view.x)/view.span,offsetY=(boundary.index-view.y)/view.span,attrs={stroke:'white','stroke-width':boundary.kind==='chain'?2:1,'pointer-events':'none'};if(boundary.kind==='gap')attrs['stroke-dasharray']='3 3';if(offsetX>0&&offsetX<1)appendSVG('line',{...attrs,x1:g.left+offsetX*g.size,x2:g.left+offsetX*g.size,y1:g.top,y2:g.top+g.size});if(offsetY>0&&offsetY<1)appendSVG('line',{...attrs,x1:g.left,x2:g.left+g.size,y1:g.top+offsetY*g.size,y2:g.top+offsetY*g.size});}
  const ticks=Math.max(2,Math.floor(g.size/75));for(const index of sparseTicks(n,view.x,view.span,ticks)){const x=g.left+(index+.5-view.x)*cell;appendSVG('text',{transform:`translate(${x} ${g.top+g.size+13}) rotate(45)`,'text-anchor':'start'},p.residues[index].label);}
  for(const index of sparseTicks(n,view.y,view.span,ticks)){const y=g.top+(index+.5-view.y)*cell;appendSVG('text',{x:g.left-8,y:y+4,'text-anchor':'end'},p.residues[index].label);}
 }
 function render(snapshot){
  const {state,view,result}=snapshot,p=result.payload;nodes.body.hidden=!p;nodes.status.hidden=!!p;nodes.status.textContent=result.note;nodes.override.hidden=!hasOverrides(state);shell.dataset.state=result.status;
  if(!p){nodes.canvas.width=nodes.canvas.height=0;nodes.axes.replaceChildren();nodes.scope.textContent='Exact active model and residue cohort';hover=null;return;}
  nodes.scope.textContent=p.cohort.model_count.toLocaleString()+' models · '+p.residues.length.toLocaleString()+' ordered residues · '+p.cohort.id+' · '+p.cohort.scope_id;
  for(const metric of METRICS){nodes[metric].hidden=!p.matrices[metric];nodes[metric].setAttribute('aria-selected',String(state.metric===metric));nodes[metric].tabIndex=state.metric===metric?0:-1;}
  for(const mode of ['linear','log'])nodes[mode].setAttribute('aria-pressed',String(state.scale===mode));
  const range=effectiveRange(p,state);nodes.palette.value=state.palettes[state.metric];nodes.min.value=String(range[0]);nodes.max.value=String(range[1]);nodes.legendTitle.textContent=(state.metric==='variance'?'Population variance':'Median distance')+' · '+p.statistics[state.metric].units;
  nodes.legend.style.background='linear-gradient(to right,'+STOPS[state.palettes[state.metric]].join(',')+')';nodes.legend.setAttribute('aria-label',nodes.legendTitle.textContent+', '+range[0]+' to '+range[1]+', '+state.scale+' color scale');nodes.ticks.replaceChildren();
  for(const tick of colorbarTicks(range,state.scale,3)){const label=element('span',null,shortNumber(tick.value),nodes.ticks);label.style.left=(tick.fraction*100)+'%';label.title=String(tick.value)+' '+p.statistics[state.metric].units;}
  nodes.scaleNote.textContent=state.scale==='log'?'Log colors use log1p(value / 1 unit). Labels, hover and numeric downloads retain raw units.':'Linear colors · full saved off-diagonal range'+(state.ranges[state.metric]?' overridden.':'.');
  nodes.viewNote.textContent=view.span===p.residues.length?'Full matrix':shortNumber(view.span)+' × '+shortNumber(view.span)+' residue positions';if(hover)showHover(hover.row,hover.column);draw(snapshot);
 }
 function download(kind){const s=controller.getSnapshot(),p=s.result.payload;if(!p)return;const stem=p.cohort.id.replace(/[^A-Za-z0-9_-]/g,'_')+'-'+s.state.metric;const content=kind==='csv'?csv(p,s.state.metric):kind==='json'?JSON.stringify(p,null,2)+'\n':svg(p,s.state,s.view),type=kind==='csv'?'text/csv;charset=utf-8':kind==='json'?'application/json':'image/svg+xml;charset=utf-8',url=env.URL.createObjectURL(new env.Blob([content],{type})),link=element('a');link.href=url;link.download=stem+'.'+kind;link.click();env.setTimeout(()=>env.URL.revokeObjectURL(url),1000);}
 const observer=env.ResizeObserver?new env.ResizeObserver(()=>draw(controller.getSnapshot())):null;observer?.observe(nodes.chart);
 listen(env,'resize',()=>draw(controller.getSnapshot()));
 const ready=Promise.resolve(fontReady||env.AtlasUILayout?.ready||doc.fonts?.ready).catch(()=>{}).then(()=>{drawReady=true;render(controller.getSnapshot());return controller.getSnapshot();});
 return{ready,setContext:context=>{hover=null;return controller.setContext(context);},clear:note=>controller.clear(note),getState:controller.getState,setState:controller.setState,getView:controller.getView,setView:controller.setView,resetDisplay:controller.resetDisplay,resetView:controller.resetView,getSnapshot:controller.getSnapshot,download,destroy(){destroyed=true;controller.destroy();observer?.disconnect();for(const off of listeners)off();shell.remove();}};
}
const api={SCHEMA,STATE_SCHEMA,DEFAULTS:clone(DEFAULTS),METRICS,PALETTES,NULL_COLOR,sha256,validateContext,validateBinding,validatePayload,createLoader,displayState,patchState,normalize,color,colorbarTicks,separators,geometry,sparseTicks,rawHover,effectiveRange,hasOverrides,fullView,viewState,zoomView,createController,parseRoute,routeParams,updateRoute,csv,svg,createWidget};
root.AtlasDistanceMaps=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
