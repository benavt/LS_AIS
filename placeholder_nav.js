(() => {
  const links = [{"id": "CDK2_DOC1", "label": "CDK2–DOC1 monomer", "href": "targets/cdk2-doc1-monomer/"}, {"id": "CDK2_DOC1t", "label": "CDK2–DOC1t monomer", "href": "targets/cdk2-doc1t-monomer/"}];
  function sync() {
    const menu = document.getElementById('targets');
    if (!menu) return;
    for (const item of links) {
      let anchor = [...menu.querySelectorAll('a[data-linked-target]')].find(a => a.dataset.linkedTarget === item.id);
      if (!anchor) { anchor = document.createElement('a'); anchor.dataset.linkedTarget = item.id; }
      anchor.href = item.href; anchor.textContent = item.label; menu.append(anchor);
    }
  }
  window.addEventListener('atlas:cohort', sync);
  document.addEventListener('DOMContentLoaded', sync);
})();
