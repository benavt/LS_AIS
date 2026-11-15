(() => {
  const monomers = {'CDK2_DOC1': 'CDK2–DOC1 monomer',
                    'CDK2_DOC1t': 'CDK2–DOC1t monomer',
                    'CDK2_DOC1R': 'CDK2–DOC1R monomer',
                    'CDK2_MONOMER': 'CDK2 monomer'};
  const cohort = range => ['collaborator', 'combined'].includes(range) ? range :
    ['joint', 'core-joint'].includes(range) ? 'joint' : 'afsample3';
  const single = {CDK2_DOC1R: 'Collaborator AF3 · 3,435 models', CDK2_MONOMER: 'Collaborator AF3 · 284 models'};
  const trimmed = range => ['core-afsample3', 'core-joint'].includes(range);
  const full = range => ['all', 'joint'].includes(range);
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
    select.style.maxWidth = '100%';
    select.setAttribute('aria-label', 'Model cohort');
    select.addEventListener('change', () => {
      const range = document.getElementById('residueRange');
      const candidates = [...(range?.options || [])].filter(
        item => cohort(item.value) === select.value && !item.disabled);
      const option = candidates.find(item => trimmed(item.value) === trimmed(range.value))
        || candidates.find(item => full(item.value)) || candidates[0];
      if (!option) return;
      range.value = option.value;
      range.dispatchEvent(new Event('change', {bubbles: true}));
    });
    label.append(select);
    anchor.before(label);
    return label;
  }

  window.addEventListener('atlas:cohort', event => {
    const label = menu();
    if (!label) return;
    const {current, range: currentRange} = event.detail;
    const target = current.target;
    const monomer = Object.hasOwn(monomers, target);
    const range = document.getElementById('residueRange');
    const select = label.querySelector('select');
    const available = new Set([...range.options].filter(o => !o.disabled).map(o => cohort(o.value)));
    const choices = single[target] ? [['afsample3', single[target]]] :
      [['afsample3', 'AFSample3 · 1,000 models'], ['joint', 'Combined methods · 5,000 models']];
    if (target === 'CDK2_DOC1') choices.push(['collaborator', 'Collaborator AF3 · 910 models'],
      ['combined', 'Existing and collaborator models · 5,910 models']);
    select.replaceChildren(...choices.map(([id, text]) => {
      const option = new Option(text + (available.has(id) ? '' : ' — unavailable'), id);
      option.disabled = !available.has(id);
      return option;
    }));
    select.disabled = !!single[target];
    select.value = cohort(currentRange.id);
    label.hidden = !monomer;
    if (target === 'CDK2_DOC1') {
      for (const option of range.options) {
        option.hidden = cohort(option.value) !== select.value;
        if (full(option.value)) option.textContent = 'Full · A1–298 + B1–115';
      }
    }
    let note = document.getElementById('coreResultsNote');
    if (!note) {
      note = document.createElement('p');
      note.id = 'coreResultsNote';
      note.className = 'hint range-note';
      document.getElementById('residueRangeNote').after(note);
    }
    note.replaceChildren();
    note.hidden = target !== 'CDK2_DOC1' || !!current.coordinates_private;
    if (!note.hidden && current.core_results) {
      const a = document.createElement('a');
      a.href = current.core_results.comparison;
      a.download = '';
      a.textContent = 'Download full vs. trimmed comparison';
      note.append(current.core_results.summary + ' ' + current.core_results.structures_note + ' ', a);
    } else if (!note.hidden) {
      note.textContent = 'The trimmed analysis is available under Residues for this cohort.';
    }
    if (monomer) queueMicrotask(() => {
      const title = document.getElementById('title');
      if (title?.textContent === target) title.textContent = monomers[target];
    });
  });
})();
