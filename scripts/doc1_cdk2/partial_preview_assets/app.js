"use strict";
const TARGETS = ["DOC1Rdimer_CDK2", "DOC1dimer_CDK2"];
const cache = new Map();
const $ = id => document.getElementById(id);
const fmt = value => Number(value).toLocaleString();
const svgMode = new URLSearchParams(location.search).get("renderer") === "svg";
const publicBundle = document.documentElement.dataset.publicBundle === "true";
let current = TARGETS[0], data = null, selected = null, projection = "umap", viewer = null, spinning = false;

async function readTargetJSON(path) {
  const name = publicBundle ? `${path}.gz` : path;
  const response = await fetch(name);
  if (!response.ok) throw Error(`${name} returned ${response.status}`);
  if (!publicBundle) return response.json();
  const raw = await response.arrayBuffer(), bytes = new Uint8Array(raw);
  // Static hosts may transmit .gz as-is or apply Content-Encoding on the wire.
  if (bytes[0] !== 0x1f || bytes[1] !== 0x8b) return JSON.parse(new TextDecoder().decode(bytes));
  if (!('DecompressionStream' in window)) throw Error("This browser cannot unpack the saved atlas data");
  const stream = new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}

function groupName(view, label) {
  if (Number(label) === -1) return "Unassigned";
  return `${view === "knn" ? "Group" : "Cluster"} ${label}`;
}
function groupColor(label) {
  if (Number(label) === -1) return "#adb3bb";
  return `hsl(${(Number(label) * 137.508 + 174) % 360},67%,43%)`;
}
function energyColor(value) {
  const [low,,high] = data.energy.limits;
  const fraction = Math.max(0, Math.min(1, (value - low) / (high - low || 1)));
  return `hsl(${Math.round(225 - 220 * fraction)},70%,43%)`;
}
function colors(view, mode, indexes) {
  const labels = data[view], methods = Object.keys(data.method_counts);
  return indexes.map(i => {
    if (selected !== null && Number(labels[i]) !== selected) return "#d6d9da";
    if (mode === "energy" && data.energy) return energyColor(data.energy.values[i]);
    if (mode === "method") return groupColor(methods.indexOf(data.method[i]));
    if (mode === "strength" && view !== "knn") {
      if (labels[i] === -1) return "#adb3bb";
      const p = data[`${view}_probability`][i];
      return `hsl(205,75%,${Math.round(86 - p * 51)}%)`;
    }
    return groupColor(labels[i]);
  });
}
function updateLegend(view, mode) {
  const element = $("projectionLegend");
  element.replaceChildren();
  const items = [];
  if (selected !== null) items.push([mode === "energy" ? "#d6d9da" : groupColor(selected),
                                    mode === "energy" ? "Other groups dimmed" : `${groupName(view, selected)} highlighted`]);
  if (mode === "energy" && data.energy) {
    items.push([energyColor(data.energy.limits[0]), `Lower score ${data.energy.limits[0].toFixed(2)}`],
               [energyColor(data.energy.limits[2]), `Higher score ${data.energy.limits[2].toFixed(2)} · learned units`]);
  }
  else if (mode === "method") items.push(["#317f7b", `${Object.keys(data.method_counts).length} generation methods`]);
  else if (mode === "strength") items.push(["#2869a2", "Darker = stronger membership"], ["#adb3bb", "Unassigned"]);
  else items.push(["#317f7b", `${Object.keys(data.counts[view]).filter(x => x !== "-1").length} saved ${view === "knn" ? "groups" : "clusters"}`]);
  if (view !== "knn" && mode !== "strength" && mode !== "energy") items.push(["#adb3bb", "Unassigned"]);
  for (const [color, label] of items) {
    const span = document.createElement("span"), swatch = document.createElement("i");
    swatch.className = "swatch"; swatch.style.background = color;
    span.append(swatch, document.createTextNode(label)); element.append(span);
  }
}
function updateSelection(view) {
  const counts = data.counts[view];
  $("selectionSummary").textContent = selected === null
    ? "Select a projection point or cluster row to inspect a saved group. The structure shown is an independent example model."
    : `${groupName(view, selected)} · ${fmt(counts[selected] || 0)} models (${(100*(counts[selected] || 0)/data.models).toFixed(1)}%). The example structure is not a representative of this selection.`;
  for (const row of $("clusterRows").querySelectorAll("tr[data-cluster]")) row.classList.toggle("selected", Number(row.dataset.cluster) === selected);
}
function drawTable(view) {
  const body = $("clusterRows"); body.replaceChildren();
  const rows = Object.entries(data.counts[view]).map(([label, count]) => [Number(label), Number(count)]).sort((a,b) => b[1] - a[1]);
  const fragment = document.createDocumentFragment();
  for (const [label, count] of rows) {
    const row = document.createElement("tr"); row.dataset.cluster = label; row.tabIndex = 0;
    const name = document.createElement("td"), dot = document.createElement("span"); dot.className = "dot"; dot.style.background = groupColor(label);
    name.append(dot, document.createTextNode(groupName(view,label)));
    for (const value of [name, fmt(count), `${(100*count/data.models).toFixed(2)}%`, "Pending"]) {
      if (value instanceof Element) row.append(value);
      else { const td = document.createElement("td"); td.textContent = value; row.append(td); }
    }
    row.addEventListener("click", () => chooseCluster(label));
    row.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); chooseCluster(label); }});
    fragment.append(row);
  }
  body.append(fragment); updateSelection(view);
}
function drawBars(view) {
  const rows = Object.entries(data.counts[view]).map(([label,n]) => [Number(label),Number(n)]).sort((a,b) => b[1]-a[1]);
  const unassigned = rows.find(row => row[0] === -1);
  const shown = rows.filter(row => row[0] !== -1).slice(0,15);
  if (unassigned) shown.unshift(unassigned);
  Plotly.react("groupBars", [{type:"bar",orientation:"h",x:shown.map(row=>row[1]).reverse(),y:shown.map(row=>groupName(view,row[0])).reverse(),marker:{color:shown.map(row=>groupColor(row[0])).reverse()}}],
    {margin:{l:110,r:12,t:12,b:40},paper_bgcolor:"#fff",plot_bgcolor:"#fff",xaxis:{title:"Models",gridcolor:"#e8e8e2"},yaxis:{automargin:true}},
    {responsive:true,displaylogo:false});
}
function drawEnergy(view) {
  if (!data.energy) return;
  const values = data.energy.values, low = data.energy.minimum, high = data.energy.maximum;
  const bins = 60, width = (high - low) / bins || 1;
  const all = Array(bins).fill(0), highlighted = Array(bins).fill(0);
  for (let i = 0; i < values.length; i++) {
    const bin = Math.max(0, Math.min(bins - 1, Math.floor((values[i] - low) / width)));
    all[bin]++;
    if (selected !== null && Number(data[view][i]) === selected) highlighted[bin]++;
  }
  const x = all.map((_, i) => low + (i + .5) * width);
  const traces = [{type:"bar",x,y:all,name:"All accepted models",marker:{color:"#88ada9"}}];
  if (selected !== null) traces.push({type:"bar",x,y:highlighted,name:groupName(view,selected),marker:{color:"#ae3348"}});
  Plotly.react("energyHistogram",traces,
    {barmode:"overlay",margin:{l:55,r:12,t:8,b:55},paper_bgcolor:"#fff",plot_bgcolor:"#fff",
     xaxis:{title:"ProteinEBM full-complex energy · t = 0.10 (learned units)",gridcolor:"#e8e8e2"},
     yaxis:{title:"Models",gridcolor:"#e8e8e2"},legend:{orientation:"h"}},
    {responsive:true,displaylogo:false});
  $("energySummary").textContent = `${fmt(values.length)} of ${fmt(data.models)} models scored · median ${data.energy.limits[1].toFixed(3)} learned units · range ${low.toFixed(3)} to ${high.toFixed(3)}${selected === null ? "" : ` · highlighted ${fmt(data.counts[view][selected] || 0)} models`}.`;
}
function draw() {
  if (!data) return;
  const view = $("analysisView").value, mode = $("color").value;
  const coordinates = projection === "umap" ? {x:data.x,y:data.y} : data[projection];
  if (!coordinates) return;
  const title = projection === "tsne" ? "t-SNE" : projection.toUpperCase();
  $("projectionTitle").textContent = title;
  for (const button of document.querySelectorAll("[data-projection]")) button.setAttribute("aria-selected",String(button.dataset.projection === projection));
  const step = svgMode ? Math.ceil(data.models / 5000) : 1;
  const indexes = Array.from({length:Math.ceil(data.models / step)}, (_,j) => j*step).filter(i => i < data.models);
  const labels = data[view];
  const custom = indexes.map(i => [i,data.model_id[i],data.method[i],groupName(view,labels[i]),view === "knn" ? "—" : data[`${view}_probability`][i],data.energy ? data.energy.values[i].toFixed(3) : "—"]);
  const plot = $("umap");
  plot.setAttribute("aria-label",`${title} projection of ${fmt(data.models)} accepted models`);
  Plotly.react(plot,[{type:svgMode?"scatter":"scattergl",mode:"markers",x:indexes.map(i=>coordinates.x[i]),y:indexes.map(i=>coordinates.y[i]),customdata:custom,
    hovertemplate:`<b>%{customdata[1]}</b><br>Method: %{customdata[2]}<br>%{customdata[3]}<br>Strength: %{customdata[4]}${data.energy ? "<br>Full-complex ProteinEBM t=0.10: %{customdata[5]}" : ""}<extra></extra>`,
    marker:{size:svgMode?4:4,opacity:.68,color:colors(view,mode,indexes)},showlegend:false}],
    {margin:{l:52,r:12,t:15,b:45},paper_bgcolor:"#fff",plot_bgcolor:"#fff",xaxis:{title:`${title} 1`,zeroline:false,gridcolor:"#e8e8e2"},yaxis:{title:`${title} 2`,zeroline:false,gridcolor:"#e8e8e2"},hovermode:"closest"},
    {responsive:true,displaylogo:false,modeBarButtonsToRemove:["lasso2d","select2d"]});
  if (!plot.dataset.clickBound) {
    plot.on("plotly_click", event => {const index=event.points[0].customdata[0];chooseCluster(Number(data[$("analysisView").value][index]));});
    plot.dataset.clickBound = "true";
  }
  $("plotNote").textContent = svgMode
    ? `${fmt(indexes.length)} evenly spaced display points in CPU/SVG mode; all ${fmt(data.models)} models are in the download. ${title} fit uses ${data.range_label}.`
    : `${fmt(data.models)} accepted models plotted · ${data.range_label} · saved seed-42 ${title}${projection === "pca" ? ` · explained variance ${(100*data.pca.explained_variance_ratio[0]).toFixed(1)}%, ${(100*data.pca.explained_variance_ratio[1]).toFixed(1)}%` : ""}`;
  const count = Object.keys(data.counts[view]).filter(x=>x!=="-1").length;
  const noise = Number(data.counts[view][-1] || 0);
  $("explorerNote").textContent = `${fmt(data.models)} accepted models · fit residues ${data.range_label} · ${fmt(count)} ${view === "knn" ? "groups" : "clusters"}${view === "knn" ? "" : ` · ${fmt(noise)} unassigned (${(100*noise/data.models).toFixed(1)}%)`}${view === "eom" ? " · diagnostic alternate" : ""}.`;
  updateLegend(view,mode); updateSelection(view); drawEnergy(view);
}
function chooseCluster(label) {
  selected = Number(label); draw(); updateSelection($("analysisView").value);
}
function fillMethods() {
  const table = document.createElement("table"), head = document.createElement("thead"), hr = document.createElement("tr");
  for (const title of ["Generation method","Accepted models"]) {const th=document.createElement("th");th.textContent=title;hr.append(th);} head.append(hr);table.append(head);
  const body = document.createElement("tbody");
  for (const [method,count] of Object.entries(data.method_counts).sort((a,b)=>b[1]-a[1])) {
    const row=document.createElement("tr");for(const value of [method,fmt(count)]){const td=document.createElement("td");td.textContent=value;row.append(td);}body.append(row);
  }
  table.append(body);$("methodCounts").replaceChildren(table);
}
async function showStructure(slug) {
  const response = await fetch(`data/${slug}-example.pdb`);
  if (!response.ok) throw Error(`Example structure returned ${response.status}`);
  const pdb = await response.text();if (current !== slug) return;
  if (viewer && spinning) {viewer.spin(false);spinning=false;$("spin").setAttribute("aria-pressed","false");}
  $("molecule").replaceChildren();
  viewer = AtlasStructureRenderer.createViewer($("molecule"),{backgroundColor:"#f7f7f4"});
  viewer.addModel(pdb,"pdb");
  viewer.setStyle({chain:"A"},{cartoon:{color:"#008e83"}});
  viewer.setStyle({chain:"B"},{cartoon:{color:"#e3934d"}});
  viewer.setStyle({chain:"C"},{cartoon:{color:"#4871ad"}});
  viewer.zoomTo();viewer.render();
  $("modelTitle").textContent = `${data.example_model} · first accepted model, not a cluster representative`;
  $("modelInfo").textContent = `Native full-construct A/B/C coordinates from the accepted roster. Example identity: ${data.example_model}.`;
  $("pdbLink").href = `data/${slug}-example.pdb`;
}
async function setRange(slug, range) {
  if (!cache.has(slug)) throw Error("Target data is not loaded");
  if (range === "core" && !cache.has(`${slug}-core`)) {
    cache.set(`${slug}-core`, await readTargetJSON(`data/${slug}-core.json`));
  }
  if (current !== slug) return;
  const full = cache.get(slug);
  const core = range === "core" ? cache.get(`${slug}-core`) : null;
  data = core ? {...full, ...core, pca:null, tsne:null, maps:null, supplemental_receipt_sha256:null} : full;
  selected = null;
  $("residueRange").value = range;
  $("residueRange").options[0].textContent = `Full · ${full.range_label}`;
  if (core) $("residueRange").options[1].textContent = `Core · ${core.range_label}`;
  else if (cache.has(`${slug}-core`)) $("residueRange").options[1].textContent = `Core · ${cache.get(`${slug}-core`).range_label}`;
  if (!data[projection] && projection !== "umap") projection = "umap";
  for (const button of document.querySelectorAll("[data-projection]")) button.disabled = button.dataset.projection !== "umap" && !data[button.dataset.projection];
  $("summary").textContent = `${fmt(data.models)} accepted models · ${data.range_label} fit · ${data.energy ? "geometry + full-complex ProteinEBM" : "geometry-only"} ${publicBundle ? "preliminary public atlas" : "private preview"}`;
  $("members").href = `downloads/${slug}${range === "core" ? "-core" : ""}-geometry-memberships.csv${publicBundle ? ".gz" : ""}`;
  $("provenance").textContent = `Accepted ${range === "core" ? "A/B-core" : "full-construct"} clustering receipt SHA-256: ${data.receipt_sha256}. Saved UMAP, labels, and model order were verified against native hashes.`;
  $("fitMethods").textContent = range === "core"
    ? `Core fit retains ${data.range_label}, with ${fmt(data.pair_count)} Cα pair features per model in the validated 4,096-dimensional sketch. Saved seed-42 UMAP KNN and HDBSCAN leaf/EOM partitions are exploratory geometry groups, not validated biological states. PCA, t-SNE, and distance maps have only been calculated for the full construct. ProteinEBM scores are full-complex overlays, not fit features.`
    : "Full fit retains all A/B/C residues in the validated 4,096-dimensional all-pair sketch. UMAP and clustering views are saved seed-42 results. HDBSCAN EOM is a diagnostic alternate; unassigned models remain unassigned. ProteinEBM scores are separate from geometry and confidence.";
  $("energyPanel").hidden = !data.energy;
  $("color").querySelector('[value="energy"]').disabled = !data.energy;
  if (data.energy) {
    $("energyScope").textContent = `Energy scoring scope: full A/B/C complex for every accepted model. Active geometry fit: ${data.range_label}.`;
    $("energyDownload").href = data.energy.download + (publicBundle ? ".gz" : "");
    $("provenance").textContent += ` Accepted ProteinEBM receipt SHA-256: ${data.energy.receipt_sha256}; full 16-level CSV SHA-256: ${data.energy.csv_sha256}.`;
  } else {
    $("energyDownload").removeAttribute("href");
    if ($("color").value === "energy") $("color").value = "cluster";
  }
  $("distanceMaps").hidden = !data.maps;
  $("supplementalMethods").hidden = !data.maps;
  if (data.maps) {
    $("medianMap").src = data.maps.median; $("varianceMap").src = data.maps.variance;
    $("medianDownload").href = data.maps.median; $("varianceDownload").href = data.maps.variance;
    $("mapCaption").textContent = `Full-construct map: all ${data.maps.chain_lengths.reduce((a,b)=>a+b,0)} Cα positions in chains A/B/C; dashed lines mark chain boundaries.`;
    $("medianCaption").textContent = `Median Cα distance (Å), frozen uniform sample of ${fmt(data.maps.median_models)} accepted models.`;
    $("varianceCaption").textContent = `Cα distance variance (Å²), all ${fmt(data.maps.variance_models)} accepted models.`;
    $("pendingText").textContent = "Bonsai, representative medoids, TM comparisons, aligned ensembles, and MCMC/DISCO panels do not yet have accepted outputs for these two targets. No values or structures are inferred to fill those views.";
    $("provenance").textContent += ` Accepted full-construct PCA/t-SNE/map receipt SHA-256: ${data.supplemental_receipt_sha256}.`;
  } else {
    $("medianMap").removeAttribute("src"); $("varianceMap").removeAttribute("src");
    $("medianDownload").removeAttribute("href"); $("varianceDownload").removeAttribute("href");
    $("pendingText").textContent = "The A/B-core fit has no saved PCA, t-SNE, or Cα distance maps. Switch to Full for those full-construct figures. Bonsai, representative medoids, TM comparisons, aligned ensembles, and MCMC/DISCO panels remain pending.";
  }
  $("color").querySelector('[value="strength"]').disabled = $("analysisView").value === "knn";
  if ($("color").value === "strength" && $("analysisView").value === "knn") $("color").value = "cluster";
  fillMethods(); drawTable($("analysisView").value); drawBars($("analysisView").value); draw();
}
async function setTarget(slug) {
  if (!TARGETS.includes(slug)) return;
  current=slug;selected=null;$("error").hidden=true;
  for(const link of document.querySelectorAll("[data-target]")) link.setAttribute("aria-current",link.dataset.target === slug ? "page":"false");
  $("summary").textContent="Loading saved target data…";
  try {
    if (!cache.has(slug)) cache.set(slug,await readTargetJSON(`data/${slug}.json`));
    if (current !== slug) return;
    $("title").textContent=cache.get(slug).title;
    await setRange(slug, rangeFromHash());
    await showStructure(slug);
  } catch(error) {$("error").hidden=false;$("error").textContent=`Atlas could not load: ${error.message}`;}
}
function targetFromHash() {const slug=location.hash.slice(1).split("?")[0];return TARGETS.includes(slug)?slug:null;}
function rangeFromHash() {return new URLSearchParams(location.hash.split("?")[1] || "").get("range") === "core" ? "core" : "full";}
window.addEventListener("hashchange",()=>{const slug=targetFromHash();if(slug)setTarget(slug);});
$("residueRange").addEventListener("change",async()=>{
  const range=$("residueRange").value;
  history.replaceState(null,"",`#${current}?range=${range}`);
  try { await setRange(current,range); }
  catch(error) {$("error").hidden=false;$("error").textContent=`Atlas could not load: ${error.message}`;}
});
$("analysisView").addEventListener("change",()=>{selected=null;const view=$("analysisView").value;$("color").querySelector('[value="strength"]').disabled=view==="knn";if(view==="knn"&&$("color").value==="strength")$("color").value="cluster";drawTable(view);drawBars(view);draw();});
$("color").addEventListener("change",draw);
for (const button of document.querySelectorAll("[data-projection]")) button.addEventListener("click",()=>{if(button.disabled)return;projection=button.dataset.projection;draw();});
$("clear").addEventListener("click",()=>{selected=null;draw();});
$("resetPlot").addEventListener("click",()=>Plotly.relayout("umap",{"xaxis.autorange":true,"yaxis.autorange":true}));
$("savePlot").addEventListener("click",()=>Plotly.downloadImage($("umap"),{format:"png",filename:`${current}-${data.range}-${$("analysisView").value}-${projection}`}));
$("resetStructure").addEventListener("click",()=>{if(viewer)viewer.zoomTo().render();});
$("spin").addEventListener("click",()=>{if(!viewer)return;spinning=!spinning;viewer.spin(spinning);$("spin").setAttribute("aria-pressed",String(spinning));});
setTarget(targetFromHash() || TARGETS[0]);
