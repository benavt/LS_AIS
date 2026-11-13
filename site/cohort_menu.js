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
    const pending = new Option('AFsample2 v1/v2/v3 + AFsample3 + BioEMU2 · 5,000 models — atlas view pending', 'joint');
    pending.disabled = true;
    select.add(saved);
    select.add(pending);
    select.addEventListener('change', () => {
      const range = document.getElementById('residueRange');
      const requested = select.value === 'joint' ? 'joint' : 'all';
      const option = [...(range?.options || [])].find(item => item.value === requested);
      if (!option || option.disabled) return;
      range.value = requested;
      range.dispatchEvent(new Event('change', {bubbles: true}));
    });
    label.append(select);
    anchor.before(label);
    return label;
  }
  window.addEventListener('atlas:cohort', event => {
    const label = menu();
    if (!label) return;
    const target = event.detail.current.target;
    label.hidden = !Object.hasOwn(monomers, target);
    const select = label.querySelector('select');
    const joint = [...select.options].find(option => option.value === 'joint');
    const verifiedRange = [...(document.getElementById('residueRange')?.options || [])]
      .find(option => option.value === 'joint' && !option.disabled);
    joint.disabled = !verifiedRange;
    joint.textContent = verifiedRange
      ? 'AFsample2 v1/v2/v3 + AFsample3 + BioEMU2 · 5,000 models'
      : 'AFsample2 v1/v2/v3 + AFsample3 + BioEMU2 · 5,000 models — atlas view pending';
    select.value = event.detail.current.range_id === 'joint' ? 'joint' : 'afsample3';
    if (!label.hidden) queueMicrotask(() => {
      const title = document.getElementById('title');
      if (title?.textContent === target) title.textContent = monomers[target];
    });
  });
})();
