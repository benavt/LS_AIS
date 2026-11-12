(() => {
  const monomers = {'CDK2_DOC1': 'CDK2–DOC1 monomer',
                    'CDK2_DOC1t': 'CDK2–DOC1t monomer'};
  function menu() {
    let label = document.getElementById('cohortViewLabel');
    if (label) return label;
    const anchor = document.getElementById('analysisViewLabel');
    if (!anchor) return null;
    label = document.createElement('label');
    label.id = 'cohortViewLabel';
    label.style.gridColumn = '1 / -1';
    label.textContent = 'Model cohort ';
    const select = document.createElement('select');
    select.id = 'cohortView';
    select.style.maxWidth = '480px';
    select.setAttribute('aria-label', 'Model cohort');
    const saved = new Option('AFsample3 · 1,000 models', 'afsample3');
    const pending = new Option('AFsample2 v1/v2/v3 + BioEMU2 · 4,000 models — atlas view pending', 'afsample2-bioemu2');
    pending.disabled = true;
    select.add(saved);
    select.add(pending);
    label.append(select);
    anchor.before(label);
    return label;
  }
  window.addEventListener('atlas:cohort', event => {
    const label = menu();
    if (!label) return;
    const target = event.detail.current.target;
    label.hidden = !Object.hasOwn(monomers, target);
    label.querySelector('select').value = 'afsample3';
    if (!label.hidden) queueMicrotask(() => {
      const title = document.getElementById('title');
      if (title?.textContent === target) title.textContent = monomers[target];
    });
  });
})();
