/* Saved native Bonsai layouts; colors come from the active projection scheme. */
(function (root) {
  'use strict';
  const ns = 'http://www.w3.org/2000/svg', gray = '#808080';
  function element(tag, attrs = {}, text) {
    const e = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) e.setAttribute(key, value);
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function rgb(color) {
    if (/^#[0-9a-f]{6}$/i.test(color)) return [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16));
    if (/^#[0-9a-f]{3}$/i.test(color)) return [...color.slice(1)].map(c => parseInt(c + c, 16));
    const match = /^rgba?\(\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)(?:\s*[,/]\s*[\d.]+)?\s*\)$/i.exec(color);
    if (!match) throw Error('Unsupported resolved projection color: ' + color);
    return match.slice(1, 4).map(Number);
  }
  function colorResolver(scheme, projection) {
    if (scheme.type !== 'continuous') return value => scheme.colors[String(value ?? 'Unspecified')] || gray;
    // Plotly resolves named palettes and automatic bounds on the population.
    // Do not renormalize on the much smaller Bonsai selection.
    const marker = projection?._fullData?.find(t => Array.isArray(t.marker?.colorscale) && Array.isArray(t.marker?.color))?.marker;
    if (!marker) {
      if (scheme.values.every(v => !Number.isFinite(v))) return () => gray;
      throw Error('The numeric projection palette must resolve before drawing Bonsai.');
    }
    const lo = marker.cmin, hi = marker.cmax, scale = marker.colorscale;
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi < lo || scale.length < 2) throw Error('Invalid projection color bounds.');
    return value => {
      if (!Number.isFinite(value)) return gray;
      const t = hi === lo ? .5 : Math.max(0, Math.min(1, (value - lo) / (hi - lo)));
      let upper = 1;
      while (upper < scale.length - 1 && t > scale[upper][0]) upper++;
      const [a, ca] = scale[upper - 1], [b, cb] = scale[upper], fraction = b === a ? 0 : (t - a) / (b - a);
      const left = rgb(ca), right = rgb(cb);
      return 'rgb(' + left.map((v, i) => Math.round(v + fraction * (right[i] - v))).join(', ') + ')';
    };
  }
  function validate(payload, models) {
    const names = new Set(models), selected = new Set();
    if (payload.schema_version !== 1 || payload.layouts.length !== 3) throw Error('Invalid saved Bonsai payload.');
    for (const row of payload.models) {
      if (!names.has(row.model) || selected.has(row.model) || !Number.isInteger(row.vertex) || row.vertex < 0) throw Error('Bonsai selection does not match the current analysis.');
      selected.add(row.model);
    }
    for (const layout of payload.layouts) {
      if (!layout.nodes.length || !layout.nodes.every(p => p.length === 2 && p.every(Number.isFinite)) || !layout.edges.every(s => s.length >= 2 && s.every(p => p.length === 2 && p.every(Number.isFinite))) || payload.models.some(r => r.vertex >= layout.nodes.length)) throw Error('Invalid native Bonsai geometry.');
    }
  }
  function create(container, {onChoose = () => {}, detailsHref = null} = {}) {
    container.replaceChildren(); container.style.position = 'relative';
    const toolbar = document.createElement('div'); toolbar.className = 'bonsai-toolbar'; toolbar.style.cssText = 'display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:12px 0';
    const label = document.createElement('label'); label.append('Layout ');
    const select = document.createElement('select'); select.setAttribute('aria-label', 'Bonsai tree layout'); label.append(select);
    const reset = document.createElement('button'); reset.textContent = 'Reset tree view';
    const download = document.createElement('button'); download.textContent = 'Download colored SVG';
    toolbar.append(label, reset, download);
    const legend = document.createElement('div'); legend.className = 'bonsai-legend'; legend.style.cssText = 'display:flex;align-items:center;gap:8px 18px;flex-wrap:wrap;font-size:12px;margin:12px 0';
    const svg = element('svg', {viewBox: '0 0 1000 620', role: 'img', 'aria-label': 'Interactive Bonsai tree of selected ensemble models', tabindex: 0});
    svg.style.cssText = 'display:block;width:100%;background:white;touch-action:none;border:1px solid #dce5e8;border-radius:6px';
    const info = document.createElement('p'); info.className = 'hint bonsai-model-info'; info.hidden = true; info.setAttribute('aria-live', 'polite');
    // Keep point details out of the flex layout: showing them must not resize
    // the SVG and cause its ResizeObserver to replace the focused marker.
    info.style.cssText = 'position:absolute;z-index:2;left:8px;right:8px;margin:0;padding:6px 8px;background:rgba(255,255,255,.96);border:1px solid #ddd;border-radius:2px;pointer-events:none;overflow-wrap:anywhere';
    const note = document.createElement('p'); note.className = 'hint bonsai-caption';
    container.append(toolbar, legend, svg, info, note);
    let data, payload, scheme, projection, active = null, pan = [0, 0], zoom = 1, world, drag, lastWidth = 0, hiddenCategories = new Set(), resolvedColor = null, lastHeight = 0, highlightedModels = null;
    function transform() { if (world) world.setAttribute('transform', `translate(${pan}) scale(${zoom})`); }
    function point(e) {
      const matrix = svg.getScreenCTM();
      return new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix.inverse());
    }
    function describe(row, index) {
      const value = scheme.values[index];
      return `${row.model} · ${data.clusters[index]} · ${data.methods[index]} · ${row.bonsai_group} · ${scheme.name}: ${Number.isFinite(value) ? value.toFixed(4) : value ?? 'unavailable'}`;
    }
    function draw() {
      if (!payload) return;
      const panel=container.closest('.cluster-view'),featured=!panel||panel.classList.contains('is-featured');
      const width=Math.max(1,Math.round(svg.getBoundingClientRect().width||container.getBoundingClientRect().width||320));
      const height=panel?.closest('.explorer-screen')?Math.max(30,Math.round(svg.getBoundingClientRect().height)):featured?Math.round(Math.max(180,Math.min(width*.7,(window.visualViewport?.height||window.innerHeight||800)*.6))):Math.round(Math.max(45,width*.62));
      lastWidth = width; lastHeight=height; svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.style.height = height + 'px';
      info.style.top = Math.max(0, svg.getBoundingClientRect().top - container.getBoundingClientRect().top + 6) + 'px';
      const layout = payload.layouts.find(x => x.key === select.value) || payload.layouts[0];
      const color = resolvedColor || colorResolver(scheme, projection), byName = new Map(data.models.map((n, i) => [n, i]));
      svg.replaceChildren(element('title', {}, `${data.target}: ${layout.title} Bonsai; color by ${scheme.name}`));
      world = element('g'); svg.append(world);
      const all = [...layout.nodes, ...layout.edges.flat()], xs = all.map(p => p[0]), ys = all.map(p => p[1]);
      const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
      const spanX = xmax - xmin || 1, spanY = ymax - ymin || 1, scale = Math.min((width - 80) / spanX, (height - 80) / spanY);
      const xy = p => [width / 2 + (p[0] - (xmin + xmax) / 2) * scale, height / 2 - (p[1] - (ymin + ymax) / 2) * scale];
      for (const segment of layout.edges) world.append(element('polyline', {points: segment.map(xy).map(p => p.join(',')).join(' '), fill: 'none', stroke: '#a0a0a0', 'stroke-width': 1.2, 'vector-effect': 'non-scaling-stroke'}));
      const vertices = new Map();let visibleHighlighted=0;
      for (const row of payload.models) { const i=byName.get(row.model),value=scheme.values[i],key=scheme.type==='continuous'?(Number.isFinite(value)?'valid':'Not calculable'):String(value??'Unspecified');if(hiddenCategories.has(key))continue; if (!vertices.has(row.vertex)) vertices.set(row.vertex, []); vertices.get(row.vertex).push(row); }
      for (const [vertex, rows] of vertices) {
        const [x, y] = xy(layout.nodes[vertex]), radius = 5 * Math.sqrt(rows.length);
        rows.forEach((row, sector) => {
          const i = byName.get(row.model), title = describe(row, i), attributes = {fill: color(scheme.values[i]), stroke: 'white', 'stroke-width': .8, 'data-model': row.model, 'data-cluster': data.clusters[i], tabindex: 0, role: 'button', 'aria-label': title, opacity: highlightedModels?(highlightedModels.has(row.model)?1:.16):1, 'data-sampling-highlight': String(!!highlightedModels?.has(row.model))};
          let marker;
          if (rows.length === 1) marker = element('circle', {...attributes, cx: x, cy: y, r: radius});
          else {
            const a = 2 * Math.PI * sector / rows.length, b = 2 * Math.PI * (sector + 1) / rows.length;
            marker = element('path', {...attributes, d: `M${x},${y} L${x + radius * Math.cos(a)},${y + radius * Math.sin(a)} A${radius},${radius} 0 ${b - a > Math.PI ? 1 : 0} 1 ${x + radius * Math.cos(b)},${y + radius * Math.sin(b)} Z`});
          }
          marker.style.cursor = 'pointer'; marker.append(element('title', {}, title));
          marker.addEventListener('mouseenter', () => { info.textContent = title; info.hidden = false; });
          marker.addEventListener('focus', () => { info.textContent = title; info.hidden = false; });
          marker.addEventListener('click', e => { if (!drag?.moved) onChoose(data.clusters[i], row.model, e); });
          marker.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onChoose(data.clusters[i], row.model, e); } });
          world.append(marker);
          if(highlightedModels?.has(row.model)){
            ++visibleHighlighted;
            const ring={fill:'none',stroke:'#151515','stroke-width':1.8,'vector-effect':'non-scaling-stroke','pointer-events':'none','aria-hidden':'true','data-sampling-ring':'true','data-sampling-model':row.model,'data-model-index':i};
            world.append(rows.length===1?element('circle',{...ring,cx:x,cy:y,r:radius+2}):element('path',{...ring,d:marker.getAttribute('d')}));
          }
        });
        if (rows.some(r => data.clusters[byName.get(r.model)] === active)) world.append(element('circle', {cx: x, cy: y, r: radius + 3, fill: 'none', stroke: '#153f4d', 'stroke-width': 2, 'pointer-events': 'none', 'data-selection-ring': 'true'}));
      }
      legend.replaceChildren();
      const heading = document.createElement('strong'); heading.textContent = scheme.name; legend.append(heading);
      if (scheme.type === 'continuous') {
        const resolved = projection?._fullData?.find(t => Array.isArray(t.marker?.colorscale) && Array.isArray(t.marker?.color))?.marker;
        if (resolved) {
          const bar = document.createElement('span'); bar.className = 'bonsai-colorbar'; bar.style.cssText = 'display:inline-block;width:160px;height:12px;border:1px solid #aaa';
          bar.style.background = 'linear-gradient(to right,' + resolved.colorscale.map(([v, c]) => `${c} ${100 * v}%`).join(',') + ')';
          const bounds = document.createElement('span'); bounds.textContent = `${resolved.cmin.toPrecision(4)} – ${resolved.cmax.toPrecision(4)}`;
          legend.append(bar, bounds);
        }
        const missing = document.createElement('span'); missing.textContent = '● Unavailable'; missing.style.color = gray; legend.append(missing);
      } else {
        for (const value of new Set(scheme.values)) {
          const entry = document.createElement('span'); const dot = document.createElement('span'); dot.textContent = '● '; dot.style.color = color(value);
          entry.append(dot, String(value ?? 'Unspecified')); legend.append(entry);
        }
      }
      note.textContent = `${payload.models.length} models · ${data.representatives.length} clusters. `+(data.model_files?'Select a point to view that exact model.':'Select a point to view its cluster.')+(highlightedModels?` ${visibleHighlighted} of ${highlightedModels.size} highlights.`:'');
      if (detailsHref) {
        const link = document.createElement('a'); link.href = detailsHref; link.className = 'bonsai-details-link'; link.textContent = 'Methods'; link.setAttribute('aria-label', 'Bonsai plot details and controls');
        note.append(' ', link);
      }
      info.textContent = ''; info.hidden = true;
      transform();
    }
    select.onchange = () => { pan = [0, 0]; zoom = 1; draw(); };
    reset.onclick = () => { pan = [0, 0]; zoom = 1; transform(); };
    svg.addEventListener('wheel', e => {
      e.preventDefault(); const p = point(e), next = Math.max(.5, Math.min(12, zoom * Math.exp(-e.deltaY * .001)));
      pan = [p.x - (p.x - pan[0]) * next / zoom, p.y - (p.y - pan[1]) * next / zoom]; zoom = next; transform();
    }, {passive: false});
    svg.addEventListener('pointerdown', e => { if (e.button !== 0) return; const p = point(e); drag = {x: p.x, y: p.y, pan: [...pan], moved: false}; });
    svg.addEventListener('pointermove', e => { if (!drag || !e.buttons) return; const p = point(e); if (Math.hypot(p.x - drag.x, p.y - drag.y) > 3) { drag.moved = true; svg.setPointerCapture(e.pointerId); pan = [drag.pan[0] + p.x - drag.x, drag.pan[1] + p.y - drag.y]; transform(); } });
    svg.addEventListener('pointerup', () => { setTimeout(() => { drag = null; }, 0); });
    svg.addEventListener('pointercancel', () => { drag = null; });
    download.onclick = () => {
      const color = resolvedColor || colorResolver(scheme, projection), entries = [...new Set(scheme.values)], footer = scheme.type === 'continuous' ? 165 : 110 + 25 * Math.ceil(entries.length / 5);
      const drawing = svg.cloneNode(true); drawing.removeAttribute('style'); drawing.setAttribute('width', 1000); drawing.setAttribute('height', 620);
      const copy = element('svg', {xmlns: ns, width: 1000, height: 620 + footer, viewBox: `0 0 1000 ${620 + footer}`}); copy.append(drawing);
      copy.append(element('rect', {x: 0, y: 620, width: 1000, height: footer, fill: 'white'}));
      copy.append(element('text', {x: 25, y: 650, 'font-size': 15, 'font-family': 'Arial', fill: '#172b35'}, `${data.target} · ${data.view_id || 'whole'} · ${select.selectedOptions[0].textContent} · ${scheme.name}`));
      copy.append(element('text', {x: 25, y: 675, 'font-size': 12, 'font-family': 'Arial', fill: '#49616c'}, `${payload.models.length} selected models; paths encode distance. Shared projection color scale; unavailable values gray.`));
      if (scheme.type === 'continuous') {
        const marker = projection?._fullData?.find(t => Array.isArray(t.marker?.colorscale) && Array.isArray(t.marker?.color))?.marker;
        if (marker) {
          const defs = element('defs'), gradient = element('linearGradient', {id: 'bonsai-export-palette'});
          for (const [value, stop] of marker.colorscale) gradient.append(element('stop', {offset: value, 'stop-color': stop}));
          defs.append(gradient); copy.append(defs, element('rect', {x: 25, y: 700, width: 300, height: 15, fill: 'url(#bonsai-export-palette)'}));
          copy.append(element('text', {x: 25, y: 738, 'font-size': 12, 'font-family': 'Arial'}, marker.cmin.toPrecision(4)), element('text', {x: 325, y: 738, 'text-anchor': 'end', 'font-size': 12, 'font-family': 'Arial'}, marker.cmax.toPrecision(4)));
        }
        copy.append(element('circle', {cx: 370, cy: 708, r: 5, fill: gray}), element('text', {x: 383, y: 712, 'font-size': 12, 'font-family': 'Arial'}, 'Unavailable'));
      } else entries.forEach((value, i) => {
        const x = 25 + i % 5 * 190, y = 707 + Math.floor(i / 5) * 25;
        copy.append(element('circle', {cx: x, cy: y - 4, r: 5, fill: color(value)}), element('text', {x: x + 12, y, 'font-size': 12, 'font-family': 'Arial'}, String(value ?? 'Unspecified')));
      });
      const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)], {type: 'image/svg+xml'}));
      const link = document.createElement('a'); link.href = url; link.download = `${data.target}_${data.view_id || 'whole'}_bonsai_${scheme.key}.svg`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    const resize = new ResizeObserver(() => {const box=svg.getBoundingClientRect();if(payload&&box.width>0&&(Math.abs(box.width-lastWidth)>1||Math.abs(box.height-lastHeight)>1))draw()});
    resize.observe(svg);
    return {
      update(currentData, currentPayload, currentScheme, currentProjection, hidden = [], highlighted = null) {
        validate(currentPayload, currentData.models);
        highlightedModels=highlighted===null?null:new Set(highlighted);
        if(highlightedModels&&[...highlightedModels].some(model=>!currentData.models.includes(model)))throw Error('Saved selection contains a model outside this cohort.');
        if (payload !== currentPayload) { pan = [0, 0]; zoom = 1; active = null; select.replaceChildren(...currentPayload.layouts.map(x => Object.assign(document.createElement('option'), {value: x.key, textContent: x.title}))); }
        data = currentData; payload = currentPayload; scheme = currentScheme; projection = currentProjection; hiddenCategories = new Set(hidden); resolvedColor=colorResolver(scheme,projection); draw();
      },
      resetView() { reset.onclick(); },
      async savePNG() {
        const copy=svg.cloneNode(true),box=svg.viewBox.baseVal,width=1200,height=Math.round(width*box.height/box.width);
        copy.setAttribute('xmlns',ns);copy.setAttribute('width',width);copy.setAttribute('height',height);copy.removeAttribute('style');
        const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml'}));
        try {
          const image=new Image();image.src=url;await image.decode();
          const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
          const context=canvas.getContext('2d');context.fillStyle='#fff';context.fillRect(0,0,width,height);context.drawImage(image,0,0,width,height);
          const link=document.createElement('a');link.href=canvas.toDataURL('image/png');link.download=data.target+'_bonsai.png';link.click();
        } finally { URL.revokeObjectURL(url); }
      },
      select(cluster) { active = cluster; draw(); },
      clear() { resize.disconnect(); container.replaceChildren(); },
    };
  }
  root.BonsaiEnsemble = {create, colorResolver, validate};
})(typeof window === 'undefined' ? globalThis : window);

window.CDK2SavedScopeBindings={"CDK2_MONOMER_collaborator284_full":{"id":"CDK2_MONOMER_collaborator284_full","kind":"full","maps":{"median":{"png":"CDK2_MONOMER/all/figures/median-ca-distances.png"},"variance":{"png":"CDK2_MONOMER/all/figures/variance-ca-distances.png"}},"pca_variance":[0.869494616985321,0.026870856061577797],"residue_label":"full CDK2 1–298"},"CDK2_MONOMER_collaborator284_roi33":{"id":"CDK2_MONOMER_collaborator284_roi33","kind":"roi","maps":{"median":{"csv":"roi/median-ca-distances.csv","png":"roi/median-ca-distances.png"},"variance":{"csv":"roi/variance-ca-distances.csv","png":"roi/variance-ca-distances.png"}},"pca_variance":[0.9349951148033142,0.03088279813528061],"residue_label":"CDK2 B45–56 ∪ B146–166 (33 residues; 57–145 excluded)"}};
/* Task-owned saved-data presentation. No scientific fitting or model selection. */
(function(root){
'use strict';
const doc=root.document,bindings=root.CDK2SavedScopeBindings;
if(new URLSearchParams(root.location.search).get('render')==='cpu'&&root.$3Dmol){
 const facade=Object.create(root.$3Dmol);
 Object.defineProperty(facade,'createViewer',{value:()=>{throw Error('Explicit CPU C-alpha fallback requested');}});
 root.$3Dmol=facade;
}
doc.addEventListener('DOMContentLoaded',()=>{
 Promise.all([root.AtlasInspection?.ready,root.AtlasUILayout?.ready,root.AtlasMaps?.ready]).then(()=>{
  const tree=doc.getElementById('bonsai'),preferences=new Map(),plot=doc.getElementById('plot');
  const route=new URLSearchParams(root.location.hash.slice(1));let token=null,mapScope=null,axisBusy=false;
  const policy=doc.getElementById('point-inspection-policy'),fullPolicy=policy.innerHTML;
  function axisTitles(){
   const state=root.AtlasInspection.state(),scope=bindings[state.dataset];
   if(axisBusy||state.projection!=='pca'||!scope?.pca_variance||!plot._fullLayout)return;
   const titles=scope.pca_variance.slice(0,2).map((v,i)=>'PC'+(i+1)+' ('+(v*100).toFixed(2)+'% variance explained)');
   if(plot._fullLayout.xaxis.title.text===titles[0]&&plot._fullLayout.yaxis.title.text===titles[1])return;
   axisBusy=true;Promise.resolve(root.Plotly.relayout(plot,{'xaxis.title.text':titles[0],'yaxis.title.text':titles[1]})).finally(()=>{axisBusy=false;axisTitles();});
  }
  function bindAxis(){if(typeof plot.on!=='function')return;plot.removeListener?.('plotly_afterplot',axisTitles);plot.on('plotly_afterplot',axisTitles);}
  bindAxis();
  function nativeTree(){
   const select=tree?.querySelector('select[aria-label="Bonsai tree layout"]');if(!select)return;
   const state=root.AtlasInspection.state(),key=state.dataset+'|'+state.view+'|'+doc.getElementById('tree').value;
   if(key===token)return;
   const requested=preferences.get(key)||route.get('native_layout')||'ly_dendrogram_ladderized';
   if(![...select.options].some(x=>x.value===requested))return;
   token=key;select.value=requested;select.dispatchEvent(new Event('change',{bubbles:true}));
  }
  tree.addEventListener('change',event=>{if(event.target.matches('select[aria-label="Bonsai tree layout"]')&&token)preferences.set(token,event.target.value);});
  new MutationObserver(nativeTree).observe(tree,{childList:true,subtree:true});
  function maps(scope){
   const host=doc.getElementById('atlasCohortDistanceMaps');if(!host)return;
   if(mapScope===scope.id&&host.querySelector('#accepted-map-select'))return;
   mapScope=scope.id;
   const section=doc.createElement('section'),heading=doc.createElement('h2'),note=doc.createElement('p');
   heading.textContent='Cα distance maps';note.textContent='Accepted maps · 284 models · '+scope.residue_label+'. Images preserve the exact scope.'+(scope.kind==='roi'?' Numeric tables are downloadable.':'');
   const label=doc.createElement('label'),select=doc.createElement('select');label.textContent='Map ';select.id='accepted-map-select';select.setAttribute('aria-label','Accepted distance map for active residue cohort');
   for(const [id,text]of [['variance','Population variance ·Å²'],['median','Median distance ·Å']])select.add(new Option(text,id));label.append(select);
   const image=doc.createElement('img');image.style.cssText='display:block;max-width:100%;height:auto;';
   const download=doc.createElement('a'),numeric=doc.createElement('a');download.download='';download.textContent='Download accepted map image';numeric.download='';numeric.textContent='Numeric CSV';
   function choose(){const entry=scope.maps[select.value];image.src=entry.png;image.alt=select.selectedOptions[0].textContent+' ·'+scope.residue_label;download.href=entry.png;numeric.hidden=!entry.csv;if(entry.csv)numeric.href=entry.csv;}
   select.addEventListener('change',choose);choose();section.append(heading,note,label,image,download,' · ',numeric);host.replaceChildren(section);
  }
  function status(){
   const state=root.AtlasInspection.state(),scope=bindings[state.dataset];if(!scope)return;
   const isROI=scope.kind==='roi';
   for(const heading of ['tm-heading','tree-heading']){const node=doc.getElementById(heading)?.closest('section');if(node)node.hidden=isROI;}
   doc.getElementById('roi-supplements-gap').hidden=!isROI;
   doc.getElementById('viewer').hidden=false;
   doc.getElementById('cluster').disabled=isROI;
   policy.textContent='Click a point to inspect that exact native model. Ctrl/Command-click toggles comparison membership. ROI representative/TM/Bonsai availability is separate.';
   bindAxis();maps(scope);nativeTree();axisTitles();
  }
  new MutationObserver(status).observe(doc.documentElement,{attributes:true,attributeFilter:['data-cohort']});
  new MutationObserver(()=>{if(bindings[root.AtlasInspection.state().dataset]?.kind==='roi')status();}).observe(doc.getElementById('structure-status'),{childList:true,subtree:true});
  status();
 }).catch(error=>{const node=doc.getElementById('error');node.hidden=false;node.textContent='Saved presentation derivative failed: '+error.message;});
});
})(window);
