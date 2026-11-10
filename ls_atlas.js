/* Target-specific links follow the saved target menu; no scientific computation. */
window.addEventListener('atlas:cohort', event => {
  // Diagnostic summaries are opt-in, including when inherited from saved exports.
  const current = event.detail.current;
  const requested = new Set(current.requested_optional_plots || []);
  current.heatmaps = (current.heatmaps || []).filter(plot => {
    const match = String(plot.file || '').match(/(?:^|\/)(box_summary_3d|pair_distribution_detail)\.[^/]+$/i);
    return !match || requested.has(match[1].toLowerCase());
  });
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
