/* Target-specific links follow the saved target menu; no scientific computation. */
window.addEventListener('atlas:cohort', event => {
  const menu = document.getElementById('targets');
  for (const [slug, label] of [
    ['DOC1Rdimer_CDK2', 'DOC1R dimer–CDK2'],
    ['DOC1dimer_CDK2', 'DOC1 dimer–CDK2'],
  ]) {
    if (menu && !menu.querySelector(`[data-linked-target="${slug}"]`)) {
      const link = document.createElement('a');
      link.href = `doc1-cdk2/#${slug}`;
      link.textContent = label;
      link.dataset.linkedTarget = slug;
      menu.append(link);
    }
  }
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
  const labels = {methods:'Target methods', scores:'Native scores + ProteinEBM', energies:'All 16 energy levels', sampling:'Saved sampling protocol', diagnostics:'Sampling diagnostics + traces', dockq:'DockQ vs 0865 · all 5,000 target models'};
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
