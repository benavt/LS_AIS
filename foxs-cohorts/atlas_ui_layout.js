/* Shared presentation geometry. This module never changes scientific selection. */
(function(root){
'use strict';
function geometry(profile,width,expanded=false,margin){
 const p=profile.layout||profile,requested=expanded?p.expandedHeight:p.compactHeight; margin=margin||p.projectionMargin;
 return {narrow:width<p.breakpoint,width:Math.ceil(Math.max(width,p.minDrawingWidth+margin.l+margin.r)),height:Math.ceil(Math.max(requested,p.minDrawingHeight+margin.t+margin.b)),margin:{...margin}};
}
function start(env=root){
 const doc=env.document,profile=env.AtlasUIProfile,explorer=doc?.getElementById('clusterExplorer');
 if(!profile||!explorer)return null;
 const byId=id=>doc.getElementById(id),listeners=[];let expanded=false,fontState='loading',pending=false,destroyed=false,legendExpanded=false,sectionErrors=[];
 const controls=['analysisView','residueRange','projection','color','clusterSelect','family','clusterSubset','selectionMethod','selectionBalance','selectionPressure','selectionReplicate','tmStateSelect','tmStateMethod','modelMode','structureScope','structureColor'];
 function listen(node,name,fn){node?.addEventListener(name,fn);listeners.push(()=>node?.removeEventListener(name,fn));}
 function announce(){if(env.CustomEvent)env.dispatchEvent?.(new env.CustomEvent('atlas:layout-ready',{detail:state()}));}
 function state(){const values={};for(const id of controls){const node=byId(id);if(node)values[id]=node.multiple?[...node.selectedOptions].map(x=>x.value):node.value;}const current=env.AtlasInspection?.current?.(),{coordinate_text,...descriptor}=current||{};return {inspection:env.AtlasInspection?.state?.()||{target:env.AtlasInspection?.target?.()||null,current:current?descriptor:null},controls:values,layout:{expanded,narrow:explorer.dataset.atlasLayout==='narrow',font:fontState,legendExpanded,sectionErrors:[...sectionErrors]}};}
 const slots=['countReview','tmDistribution','medoidTMSection','distanceMaps','decisionsPanel'];
 function sections(){
  const declared=env.AtlasInspection?.presentation?.();sectionErrors=[];
  const valid=declared!==null&&typeof declared==='object'&&!Array.isArray(declared);
  if(declared!==undefined&&!valid)sectionErrors.push('Invalid presentation_sections declaration.');
  if(valid)for(const key of Object.keys(declared))if(!slots.includes(key))sectionErrors.push('Unknown presentation section: '+key);
  for(const id of slots){
   const panel=byId(id);if(!panel)continue;
   let message=panel.querySelector('.atlas-section-message');const status=valid?declared[id]:null;
   delete panel.dataset.atlasSectionState;
   if(!valid||!Object.hasOwn(declared,id)){message?.remove();continue;}
   if(status==='not-applicable'){panel.hidden=true;message?.remove();continue;}
   const invalid=!['available','requested-missing'].includes(status);
   if(status==='available'){message?.remove();continue;}
   panel.hidden=false;panel.dataset.atlasSectionState=invalid?'invalid':'requested-missing';
   if(!message){message=doc.createElement('p');message.className='atlas-section-message';message.setAttribute('role',invalid?'alert':'status');panel.append(message);}
   message.textContent=invalid?'Invalid saved presentation status; section availability cannot be verified.':'Requested section is unavailable in this saved analysis.';
   if(invalid)sectionErrors.push('Invalid presentation status for '+id);
  }
  const intro=byId('supplementary');if(sectionErrors.length||slots.some(id=>byId(id)&&!byId(id).hidden)){if(intro)intro.hidden=false;for(const link of doc.querySelectorAll('.page-index a[href="#supplementary"]'))link.hidden=false;}
  let error=byId('atlasPresentationError');if(sectionErrors.length&&!error&&intro){error=doc.createElement('p');error.id='atlasPresentationError';error.setAttribute('role','alert');intro.append(error);}if(error){error.hidden=!sectionErrors.length;error.textContent=sectionErrors.join(' · ');}
 }
 function advanced(){
  const summary=byId('atlasAdvancedSummary');if(!summary)return;
  // The controller's samplingSummary owns method/count/threshold labels.
  const text=[];for(const id of ['selectionBalance','selectionPressure','selectionReplicate']){const node=byId(id);if(node&&!node.disabled&&!node.closest('[hidden]')){const option=node.selectedOptions?.[0];if(option)text.push(option.textContent);}}
  summary.textContent=text.length?' · '+text.join(' · '):'';
 }
 function order(){
  const scope=byId('residueRangeLabel'),settings=scope?.parentElement;if(scope&&settings?.firstElementChild!==scope)settings.insertBefore(scope,settings.firstElementChild);
  const legend=byId('legendPanel'),host=byId('featuredPlotHost'),overview=byId('plots');
  const destination=host?.querySelector('.is-featured')?host:overview;
  if(legend&&destination?.parentElement&&destination.nextSibling!==legend)destination.parentElement.insertBefore(legend,destination.nextSibling);
 }
 function apply(){
  pending=false;if(destroyed)return;
  const width=explorer.getBoundingClientRect().width;
  explorer.dataset.atlasLayout=width<profile.layout.breakpoint?'narrow':'wide';
  doc.documentElement.dataset.atlasLayout=explorer.dataset.atlasLayout;
  explorer.dataset.atlasMode=expanded?'expanded':'compact';
  const legend=byId('projectionLegend'),toggle=byId('atlasLegendToggle');
  if(legend){legend.classList.toggle('atlas-legend-expanded',legendExpanded);legend.style.setProperty('--atlas-legend-limit',profile.layout.legendMaxHeight+'px');}
  if(toggle){toggle.textContent=legendExpanded?'Show less':'Show all';toggle.setAttribute('aria-expanded',String(legendExpanded));}
  order();advanced();
 }
 function refresh(){if(pending||destroyed)return;pending=true;(env.requestAnimationFrame||((f)=>f()))(apply);}
 function setExpanded(value){
  const requested=Boolean(value);if(requested===expanded)return;
  const button=byId('expandExplorer');
  if(env.AtlasExplorer?.setExpanded)env.AtlasExplorer.setExpanded(requested);
  else button?.click();
  expanded=explorer.classList.contains('is-maximized');refresh();
 }
 function syncExpanded(){expanded=explorer.classList.contains('is-maximized');refresh();}
 doc.documentElement.dataset.atlasProfile=profile.id;
 doc.documentElement.dataset.atlasFont='loading';
 if(profile.branding?.title){const title=doc.querySelector('.brand');if(title)title.textContent=profile.branding.title;doc.title=profile.branding.title;}
 if(profile.branding?.subtitle){const header=doc.querySelector('body>header');if(header){const subtitle=doc.createElement('p');subtitle.id='atlasProjectSubtitle';subtitle.textContent=profile.branding.subtitle;header.append(subtitle);}}
 const legendPanel=byId('legendPanel');
 if(legendPanel&&!byId('atlasLegendToggle')){const button=doc.createElement('button');button.id='atlasLegendToggle';button.type='button';button.textContent='Show all';button.setAttribute('aria-controls','projectionLegend');button.setAttribute('aria-expanded','false');legendPanel.append(button);listen(button,'click',()=>{legendExpanded=!legendExpanded;legendPanel.open=true;apply();env.AtlasResponsive?.schedule?.();});}
 const legend=byId('projectionLegend');if(legend){legend.tabIndex=0;legend.setAttribute('role','region');legend.setAttribute('aria-label','Shared color legend; scroll to inspect every exact label');}
 const sampling=byId('samplingPanel');if(sampling){const summary=sampling.querySelector('summary');if(summary&&!byId('atlasAdvancedSummary')){const span=doc.createElement('span');span.id='atlasAdvancedSummary';span.className='hint';summary.append(span);}}
 listen(doc,'change',refresh);listen(explorer,'toggle',refresh);listen(byId('expandExplorer'),'click',()=>{(env.queueMicrotask||((f)=>Promise.resolve().then(f)))(syncExpanded);});
 listen(env,'atlas:cohort',()=>{apply();env.AtlasResponsive?.schedule?.();});listen(env,'atlas:supplementary',()=>{sections();refresh();});listen(env,'atlas:layout',syncExpanded);listen(env,'resize',refresh);
 const observer=env.ResizeObserver?new env.ResizeObserver(refresh):null;observer?.observe(explorer);
 const ready=(async()=>{
  try{
   if(!doc.fonts?.load||!doc.fonts?.check)throw Error('Font loading API unavailable');
   const family=profile.font.family,math=profile.font.mathFamily;
   const faces=await Promise.all([doc.fonts.load('400 16px "'+family+'"','Atlas α Å'),doc.fonts.load('600 16px "'+family+'"','Atlas α Å'),doc.fonts.load('400 16px "'+math+'"','∑ ≥ ≤')]);
   await doc.fonts.ready;
   const expected=[[family,'400'],[family,'600'],[math,'400']];
   if(faces.some((group,i)=>!group.length||!group.some(face=>face.status==='loaded'&&face.family.replace(/^["']|["']$/g,'')===expected[i][0]&&String(face.weight)===expected[i][1])))throw Error('Pinned font face unavailable');
   if(!doc.fonts.check('400 16px "'+family+'"','Atlas α Å')||!doc.fonts.check('600 16px "'+family+'"','Atlas α Å')||!doc.fonts.check('400 16px "'+math+'"','∑ ≥ ≤'))throw Error('Pinned font unavailable');
   fontState='ready';
  }catch(error){fontState='fallback';}
  doc.documentElement.dataset.atlasFont=fontState;apply();sections();await env.AtlasResponsive?.resizeAll?.();announce();return state();
 })();
 apply();
 return {ready,state,setExpanded,refresh,geometry:(width,isExpanded=expanded,margin)=>geometry(profile,width,isExpanded,margin),destroy(){destroyed=true;observer?.disconnect();for(const off of listeners)off();}};
}
const api={geometry,start};root.AtlasUILayoutSpec=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
if(root.document&&root.AtlasUIProfile){const run=()=>{root.AtlasUILayout=start(root);};if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',run,{once:true});else run();}
})(typeof window==='undefined'?globalThis:window);
