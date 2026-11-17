(() => {
  const monomers = {'CDK2_DOC1': 'CDK2–DOC1 monomer',
                    'CDK2_DOC1t': 'CDK2–DOC1t monomer',
                    'CDK2_DOC1R': 'CDK2–DOC1R monomer',
                    'CDK2_MONOMER': 'CDK2 monomer'};
  const cohort = range => ['downloads', 'core-downloads'].includes(range) ? 'downloads' : ['combined', 'core-combined'].includes(range) ? 'combined' : range === 'collaborator' ? range :
    ['joint', 'core-joint'].includes(range) ? 'joint' : 'afsample3';
  const single = {CDK2_DOC1R: 'Collaborator AF3 · 3,435 models', CDK2_MONOMER: 'Collaborator AF3 · 284 models'};
  const trimmed = range => ['core-afsample3', 'core-joint', 'core-combined', 'core-downloads'].includes(range);
  const full = range => ['all', 'joint', 'combined', 'collaborator', 'downloads'].includes(range);
  // Keep the complete menu inventory separately from the native select.
  // Hidden <option> elements can still appear in native browser menus.
  let completeOptions = [];
  let optionTarget = '';
  const optionNode = item => Object.assign(new Option(item.text, item.value), {disabled: item.disabled});
  const pairMatrix = [{"id":"afsample3","label":"AFSample3","models":1000,"full":"all","trimmed":"core-afsample3"},{"id":"joint","label":"AIS combined methods","models":5000,"full":"joint","trimmed":"core-joint"},{"id":"collaborator","label":"Legacy collaborator AF3","models":910,"full":"collaborator","trimmed":null},{"id":"combined","label":"AIS + legacy collaborator","models":5910,"full":"combined","trimmed":"core-combined"},{"id":"downloads","label":"Downloaded collaborator AF3","models":14420,"full":"downloads","trimmed":"core-downloads"}];
  function pairAvailability(target) {
    let details = document.getElementById('cohortResidueMatrix');
    if (!details) {
      details = document.createElement('details');details.id = 'cohortResidueMatrix';details.className = 'figure-panel';
      const summary = document.createElement('summary');summary.textContent = 'Model × residue availability · 9 of 10 pairs';details.append(summary);
      const body = document.createElement('div');body.className = 'panel-body';
      const caption = document.createElement('p');caption.textContent = 'Full: CDK2 1–298 + DOC1 1–115 (413 residues). Trimmed: CDK2 1–298 + DOC1 60–115 (354 residues). These are clustering scopes; scores and native coordinate downloads retain the full construct.';body.append(caption);
      const wrap = document.createElement('div');wrap.className = 'table-wrap';
      const table = document.createElement('table');table.setAttribute('aria-label','CDK2–DOC1 model and residue cohort availability');
      const head = document.createElement('thead'),header = document.createElement('tr');
      for (const text of ['Model cohort','Models','Full · 413 residues','Trimmed · 354 residues']) {const th = document.createElement('th');th.scope = 'col';th.textContent = text;header.append(th)}
      head.append(header);table.append(head);const rows = document.createElement('tbody');
      for (const row of pairMatrix) {
        const tr = document.createElement('tr');tr.dataset.cohort = row.id;
        const name = document.createElement('th');name.scope = 'row';name.textContent = row.label;tr.append(name);
        const count = document.createElement('td');count.textContent = row.models.toLocaleString();tr.append(count);
        for (const scope of ['full','trimmed']) {
          const td = document.createElement('td');td.dataset.scope = scope;
          if (row[scope]) {const link = document.createElement('a');link.href = '#CDK2_DOC1?range='+row[scope]+'&view=density';link.textContent = 'Available';td.append(link)}
          else {td.textContent = 'Unavailable — no separate analysis';td.dataset.unavailable = 'true'}
          tr.append(td);
        }
        rows.append(tr);
      }
      table.append(rows);wrap.append(table);body.append(wrap);
      const note = document.createElement('p');note.textContent = 'The 910 legacy collaborator models are included in the trimmed 5,910-model joint fit. That does not provide a separate trimmed 910-model fit. Available pairs can still have unavailable supplements; see the notes in each view.';body.append(note);
      const downloads = document.createElement('p');
      for (const [file,text] of [['CDK2_DOC1/cohort-residue-matrix.csv','Download matrix CSV'],['CDK2_DOC1/cohort-residue-audit.json','Verified view inventory']]) {if(downloads.childNodes.length)downloads.append(' · ');const a=document.createElement('a');a.href=file;a.textContent=text;a.download='';downloads.append(a)}
      body.append(downloads);details.append(body);document.getElementById('coreResultsNote').after(details);
    }
    details.hidden = target !== 'CDK2_DOC1';
  }
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
      const candidates = completeOptions.filter(
        item => cohort(item.value) === select.value && !item.disabled);
      const option = candidates.find(item => trimmed(item.value) === trimmed(range.value))
        || candidates.find(item => full(item.value)) || candidates[0];
      if (!option) return;
      if (optionTarget === 'CDK2_DOC1') range.replaceChildren(...candidates.map(optionNode));
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
    optionTarget = target;
    completeOptions = [...range.options].map(o => ({value:o.value,text:full(o.value)&&target==='CDK2_DOC1'?'Full · A1–298 + B1–115':o.textContent,disabled:o.disabled}));
    const available = new Set(completeOptions.filter(o => !o.disabled).map(o => cohort(o.value)));
    const choices = single[target] ? [['afsample3', single[target]]] :
      [['afsample3', 'AFSample3 · 1,000 models'], ['joint', 'Combined methods · 5,000 models']];
    if (target === 'CDK2_DOC1') choices.push(['collaborator', 'Collaborator AF3 · 910 models'],
      ['combined', 'Existing and collaborator models · 5,910 models'], ['downloads', 'Collaborator AF3 · 14,420 models']);
    select.replaceChildren(...choices.map(([id, text]) => {
      const option = new Option(text + (available.has(id) ? '' : ' — unavailable'), id);
      option.disabled = !available.has(id);
      return option;
    }));
    select.disabled = !!single[target];
    select.value = cohort(currentRange.id);
    label.hidden = !monomer;
    if (target === 'CDK2_DOC1') {
      range.replaceChildren(...completeOptions.filter(o => cohort(o.value) === select.value).map(optionNode));
      range.value = currentRange.id;
    }
    let note = document.getElementById('coreResultsNote');
    if (!note) {
      note = document.createElement('p');
      note.id = 'coreResultsNote';
      note.className = 'hint range-note';
      document.getElementById('residueRangeNote').after(note);
    }
    note.replaceChildren();
    note.hidden = target !== 'CDK2_DOC1' || (!!current.coordinates_private && !current.core_results && currentRange.id !== 'combined');
    if (!note.hidden && current.cohort_note) { note.textContent=current.cohort_note; } else if (!note.hidden && current.core_results) {
      const a = document.createElement('a');
      a.href = current.core_results.comparison;
      a.download = '';
      a.textContent = 'Download full vs. trimmed comparison';
      note.append(current.core_results.summary + ' ' + current.core_results.structures_note + ' ', a);
    } else if (!note.hidden && select.value === 'collaborator') {
      note.textContent = 'Only the full-construct analysis is available for the separate 910-model cohort. A separate trimmed analysis is unavailable; these models are included in the trimmed 5,910-model joint fit.';
    } else if (!note.hidden) {
      note.textContent = 'The trimmed analysis is available under Residues for this cohort.';
    }
    pairAvailability(target);
    if (monomer) queueMicrotask(() => {
      const title = document.getElementById('title');
      if (title?.textContent === target) title.textContent = monomers[target];
    });
  });
})();
