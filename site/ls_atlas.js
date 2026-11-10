/* Target-specific links follow the saved target menu; no scientific computation. */
window.addEventListener('atlas:cohort', event => {
  const host = document.getElementById('lsDownloads');
  if (!host) return;
  const links = event.detail.current.native_data_links || {};
  const labels = {methods:'Target methods', scores:'Native scores + ProteinEBM', energies:'All 16 energy levels', sampling:'Saved sampling protocol', diagnostics:'Sampling diagnostics + traces'};
  host.replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    if (!links[key]) continue;
    if (host.childNodes.length) host.append(' · ');
    const link = document.createElement('a');
    link.href = links[key];
    link.textContent = label;
    host.append(link);
  }
});
