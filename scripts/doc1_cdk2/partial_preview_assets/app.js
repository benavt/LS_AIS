"use strict";
const TARGETS = ["DOC1Rdimer_CDK2", "DOC1dimer_CDK2"];
const cache = new Map();
let current = TARGETS[0];
const $ = id => document.getElementById(id);
const fmt = n => Number(n).toLocaleString();
function rgb(label) {
  if (label === -1) return "#adb8c5";
  const hue = (Number(label) * 137.508 + 174) % 360;
  return `hsl(${hue},68%,45%)`;
}
function colorFor(key, value, methods) {
  if (key !== "method") return rgb(value);
  const index = methods.indexOf(value);
  return rgb(index);
}
function countsFor(data, key) {
  if (key === "method") return Object.entries(data.method_counts).sort((a,b) => b[1]-a[1]);
  return Object.entries(data.counts[key]).map(([label,n]) => [Number(label),n]).sort((a,b) => b[1]-a[1]);
}
function labelFor(key, value) {
  if (key === "method") return value;
  if (value === -1 || value === "-1") return "Unassigned";
  return `${key === "knn" ? "Group" : "Cluster"} ${value}`;
}
function draw(data) {
  const key = $("color-by").value;
  const methods = Object.keys(data.method_counts);
  const values = data[key];
  const colors = values.map(value => colorFor(key, value, methods));
  const custom = data.model_id.map((id,i) => [id, data.method[i], labelFor(key,values[i]), key === "leaf" ? data.leaf_probability[i] : key === "eom" ? data.eom_probability[i] : "—"]);
  Plotly.react("umap", [{type:"scattergl", mode:"markers", x:data.x, y:data.y,
    customdata:custom, hovertemplate:"<b>%{customdata[0]}</b><br>Method: %{customdata[1]}<br>" + (key === "method" ? "" : "%{customdata[2]}<br>") + "Strength: %{customdata[3]}<extra></extra>",
    marker:{size:4,opacity:.67,color:colors}, showlegend:false}],
    {margin:{l:54,r:15,t:20,b:47},paper_bgcolor:"#fff",plot_bgcolor:"#fff",xaxis:{title:"UMAP 1",zeroline:false,gridcolor:"#e9eef4"},yaxis:{title:"UMAP 2",zeroline:false,gridcolor:"#e9eef4"},hovermode:"closest"},
    {responsive:true,displaylogo:false,modeBarButtonsToRemove:["lasso2d","select2d"]});
  const entries = countsFor(data,key);
  const unassigned = key === "leaf" || key === "eom" ? entries.find(row => row[0] === -1) : null;
  const visible = entries.filter(row => row[0] !== -1).slice(0,15);
  if (unassigned) visible.unshift(unassigned);
  Plotly.react("group-bars", [{type:"bar",orientation:"h",x:visible.map(row=>row[1]).reverse(),y:visible.map(row=>labelFor(key,row[0])).reverse(),marker:{color:visible.map(row=>colorFor(key,row[0],methods)).reverse()}}],
    {margin:{l:120,r:10,t:8,b:40},paper_bgcolor:"#fff",plot_bgcolor:"#fff",xaxis:{title:"Models",gridcolor:"#e9eef4"},yaxis:{automargin:true}},
    {responsive:true,displaylogo:false});
  $("plot-note").textContent = `${fmt(data.models)} accepted models · ${key === "leaf" ? "accepted density view" : key === "eom" ? "diagnostic alternate" : key === "knn" ? "UMAP KNN grouping" : "generation method"} · seed 42`;
  $("group-subtitle").textContent = key === "method" ? "Generation-method counts." : "Largest 15 assigned groups; unassigned shown separately when applicable.";
}
async function setTarget(slug) {
  current = slug;
  for (const button of document.querySelectorAll("[data-target]")) button.classList.toggle("active",button.dataset.target === slug);
  $("status").textContent = "Loading target data…";
  try {
    if (!cache.has(slug)) {
      const response = await fetch(`data/${slug}.json`);
      if (!response.ok) throw new Error(`Data request returned ${response.status}`);
      cache.set(slug, await response.json());
    }
    const data = cache.get(slug);
    if (current !== slug) return;
    $("model-count").textContent = fmt(data.models);
    $("knn-count").textContent = fmt(Object.keys(data.counts.knn).length);
    $("leaf-count").textContent = fmt(Object.keys(data.counts.leaf).filter(x=>x!=="-1").length);
    $("noise-count").textContent = `${fmt(data.counts.leaf[-1] || 0)} (${(100*(data.counts.leaf[-1]||0)/data.models).toFixed(1)}%)`;
    $("csv-link").href = `downloads/${slug}-geometry-memberships.csv`;
    $("pdb-link").href = `data/${slug}-example.pdb`;
    $("structure-note").textContent = `${data.example_model}: first accepted model in the frozen roster; illustrative, not a cluster representative.`;
    draw(data);
    const pdb = await fetch(`data/${slug}-example.pdb`).then(r=>{if(!r.ok)throw new Error("PDB unavailable");return r.text()});
    if (current !== slug) return;
    $("structure").innerHTML = "";
    const viewer = $3Dmol.createViewer("structure",{backgroundColor:"#eef3f7"});
    viewer.addModel(pdb,"pdb");
    viewer.setStyle({chain:"A"},{cartoon:{color:"#008e83"}});
    viewer.setStyle({chain:"B"},{cartoon:{color:"#e3934d"}});
    viewer.setStyle({chain:"C"},{cartoon:{color:"#4871ad"}});
    viewer.zoomTo();viewer.render();
    $("status").textContent = `${data.title} · accepted geometry snapshot · receipt ${data.receipt_sha256.slice(0,12)}…`;
  } catch(error) { $("status").textContent = `Preview could not load: ${error.message}`; }
}
for (const button of document.querySelectorAll("[data-target]")) button.addEventListener("click",()=>setTarget(button.dataset.target));
$("color-by").addEventListener("change",()=>{const data=cache.get(current);if(data)draw(data)});
setTarget(TARGETS[0]);
