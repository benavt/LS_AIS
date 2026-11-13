"""Presentation-only checks for the joint monomer atlas adapter."""

import importlib.util
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'joint_preview', ROOT / 'scripts/cdk2_doc1_monomer/build_joint_preview.py')
joint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(joint)


class JointPreviewTests(unittest.TestCase):
    def test_tm_grid_is_bound_to_accepted_representatives_and_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            supplement = root / 'supplement'
            supplement.mkdir()
            groups = [dict(cluster=i, size=5, representative=dict(
                model_id=f'm{i}', native_sha256=f'{i:064x}',
                native_physicality_status='passed', energy_t010=float(i)))
                for i in range(2)]
            selection = dict(clusters=groups)
            source = supplement / 'representatives-knn.json'
            source.write_text(json.dumps(selection))
            grid = dict(target='CDK2_DOC1', view='knn', models_fit=5000,
                        method='fixed-chain whole-complex bidirectional average-length USalign TM',
                        representatives_source_sha256=joint.digest(source),
                        groups=groups, unassigned_count=0,
                        matrix=[[1.0, 0.75], [0.75, 1.0]])
            (root / 'tm-grid-knn.json').write_text(json.dumps(grid))
            (root / 'tm-grid-knn.csv').write_text('cluster_a,cluster_b\n0,1\n')
            files = {name: joint.digest(root / name) for name in
                     ('tm-grid-knn.json', 'tm-grid-knn.csv')}
            receipt = dict(status='validated', target='CDK2_DOC1', models=5000,
                           plan_sha256=joint.TM_PLAN_SHA,
                           protocol='USalign -mol prot -ter 1 -TMscore 2 -a T; fixed CDK2 A/DOC1 B; no chain swapping',
                           view_counts={'knn': dict(clusters=2, unordered_pairs=1)},
                           physicality_rejected_representatives={'knn': 0},
                           files=files)
            (root / 'acceptance.json').write_text(json.dumps(receipt))
            receipt_sha = joint.digest(root / 'acceptance.json')
            result = joint.accepted_tm(root, receipt_sha, 'CDK2_DOC1', 'knn',
                                       supplement, {i: group for i, group in enumerate(groups)},
                                       np.array([0, 1]))
            self.assertEqual(result[0]['matrix'][0][1], 0.75)
            grid['groups'][1]['representative']['model_id'] = 'wrong'
            (root / 'tm-grid-knn.json').write_text(json.dumps(grid))
            receipt['files']['tm-grid-knn.json'] = joint.digest(root / 'tm-grid-knn.json')
            (root / 'acceptance.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'correspondence'):
                joint.accepted_tm(root, joint.digest(root / 'acceptance.json'),
                                  'CDK2_DOC1', 'knn', supplement,
                                  {i: group for i, group in enumerate(groups)},
                                  np.array([0, 1]))

    def test_optional_plots_are_removed_from_stage_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            stage = root / 'stage'
            (source / 'target/figures').mkdir(parents=True)
            (stage / 'target/figures').mkdir(parents=True)
            original = dict(heatmaps=[
                dict(name='Cα variance', file='target/figures/variance.png'),
                dict(name='3-D box', file='target/figures/box_summary_3d.png'),
                dict(name='Pair detail', file='target/figures/pair_distribution_detail.png')],
                provenance=dict(optional_plots_excluded_from_view=[
                    'box_summary_3d.png', 'pair_distribution_detail.png']))
            saved = source / 'target/primary.json'
            saved.write_text(json.dumps(original))
            os.link(saved, stage / 'target/primary.json')
            for name in ('box_summary_3d.png', 'pair_distribution_detail.png'):
                original_image = source / 'target/figures' / name
                original_image.write_bytes(b'plot')
                os.link(original_image, stage / 'target/figures' / name)
            joint.omit_optional_plots(stage)
            cleaned = json.loads((stage / 'target/primary.json').read_text())
            self.assertEqual(cleaned['heatmaps'], original['heatmaps'][:1])
            self.assertNotIn('optional_plots_excluded_from_view', cleaned['provenance'])
            self.assertEqual(json.loads(saved.read_text()), original)
            for name in ('box_summary_3d.png', 'pair_distribution_detail.png'):
                self.assertFalse((stage / 'target/figures' / name).exists())
                self.assertTrue((source / 'target/figures' / name).exists())

    def test_bonsai_acceptance_links_receipt_models_and_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = 'CDK2_DOC1-joint-leaf'
            (root / name).mkdir()
            supplement = root / 'supplement'
            supplement.mkdir()
            (supplement / 'representatives-leaf.json').write_text('{}')
            selection_sha = joint.digest(supplement / 'representatives-leaf.json')
            rows = [dict(model_id=f'm{i}', native_sha256=f'{i:064x}',
                         method='afsample3', weights_version='',
                         native_physicality_status='not_assessed', energy_t010=float(i))
                    for i in range(2)]
            selected = [dict(**{key: row[key] for key in
                                ('native_sha256', 'method', 'weights_version',
                                 'native_physicality_status', 'energy_t010')},
                             model_id=row['model_id'], cluster_label=label,
                             role=role)
                        for row, label, role in zip(rows, [0, -1],
                            ['energy_selected_representative', 'unassigned_example'])]
            fit = dict(status='validated', target='CDK2_DOC1', view='leaf',
                       plan_sha256=joint.BONSAI_PLAN_SHA,
                       joint_receipt_sha256='a' * 64,
                       selection_sha256=selection_sha, sketch_sha256='b' * 64,
                       model_index_sha256='c' * 64, residue_scope='A1-298+B1-115',
                       selected_representatives=1, selected_models=selected,
                       tree_sha256='d' * 64, hdf_sha256='e' * 64)
            receipt = root / name / 'acceptance.json'
            receipt.write_text(json.dumps(fit))
            receipt_sha = joint.digest(receipt)
            provenance = dict(acceptance_sha256=receipt_sha,
                              plan_sha256=joint.BONSAI_PLAN_SHA,
                              selection_sha256=selection_sha, sketch_sha256='b' * 64,
                              model_index_sha256='c' * 64, tree_sha256='d' * 64,
                              hdf_sha256='e' * 64, selected_models=2)
            models = [dict(model=row['model_id'], vertex=i,
                           original_cluster_label=selected[i]['cluster_label'],
                           selection_role=selected[i]['role'],
                           **{key: row[key] for key in
                              ('method', 'weights_version', 'native_physicality_status',
                               'energy_t010')}) for i, row in enumerate(rows)]
            viewer = dict(schema_version=1, models=models, provenance=provenance,
                          layouts=[dict(key=key, nodes=[[0, 0], [1, 1]], edges=[])
                                   for key in ('ly_eq_angle', 'ly_eq_daylight',
                                               'ly_dendrogram_ladderized')])
            layout = root / name / 'bonsai.json'
            layout.write_text(json.dumps(viewer))
            receipt_map = {'leaf': receipt_sha}
            export_map = {'leaf': joint.digest(layout)}
            with patch.dict(joint.BONSAI_RECEIPTS['CDK2_DOC1'], receipt_map), \
                 patch.dict(joint.BONSAI_EXPORTS['CDK2_DOC1'], export_map):
                result = joint.accepted_bonsai(root, root, 'CDK2_DOC1', 'leaf',
                    root, dict(joint_sketch_sha256='b' * 64,
                               model_index_sha256='c' * 64,
                               residue_scope='A1-298+B1-115'), 'a' * 64,
                    supplement, np.array([0, -1]), rows,
                    {0: dict(representative=rows[0])})
                self.assertEqual(result[2], ['m0', 'm1'])
                viewer['models'][1]['original_cluster_label'] = 0
                layout.write_text(json.dumps(viewer))
                with patch.dict(joint.BONSAI_EXPORTS['CDK2_DOC1'],
                                {'leaf': joint.digest(layout)}):
                    with self.assertRaisesRegex(ValueError, 'cluster label'):
                        joint.accepted_bonsai(root, root, 'CDK2_DOC1', 'leaf', root,
                            dict(joint_sketch_sha256='b' * 64,
                                 model_index_sha256='c' * 64,
                                 residue_scope='A1-298+B1-115'), 'a' * 64,
                            supplement, np.array([0, -1]), rows,
                            {0: dict(representative=rows[0])})

    def test_energy_representative_is_verified_and_physicality_is_visible(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            rows = [dict(model_id=f'm{i}', native_sha256=f'{i:064x}',
                         native_path=f'/scratch/private/m{i}.pdb',
                         native_physicality_status=('rejected' if i == 0 else 'passed'),
                         method='bioemu2', weights_version='', energy_t010=100.0 + i)
                    for i in range(5000)]
            rows[0]['energy_t010'] = -3.0
            labels = np.zeros(5000, dtype=np.int32)
            selection = dict(status='validated', target='CDK2_DOC1', view='leaf',
                             models=5000, plan_sha256=joint.SUPPLEMENT_PLAN_SHA,
                             representative_kind='energy-selected, not structural medoid',
                             clusters=[dict(cluster=0, size=5000,
                                            representative={key: rows[0][key] for key in
                                                ('model_id', 'native_sha256', 'method',
                                                 'weights_version', 'native_physicality_status',
                                                 'energy_t010')})],
                             unassigned_count=0)
            (folder / 'representatives-leaf.json').write_text(json.dumps(selection))
            groups = joint.verified_representatives(folder, 'CDK2_DOC1', 'leaf', labels, rows)
            projections = {name: {'xy': [[0, 0]] * 5000} for name in
                           ('pca', 'umap', 'tsne')}
            payload = joint.view_payload('CDK2_DOC1', 'leaf', rows,
                ['BioEMU2'] * 5000, labels, {'leaf': np.ones(5000)}, projections,
                {'chain_lengths': [298, 115]}, groups,
                {'m0': dict(file='CDK2_DOC1/joint-models/m0.pdb.gz', format='pdb')},
                'CDK2_DOC1/joint-memberships-and-scores.csv.gz', 'a' * 64,
                'b' * 64, {'rejected': 1},
                {'file': 'CDK2_DOC1/joint-density-bonsai.json',
                 'sha256': 'c' * 64, 'fit_receipt_sha256': 'd' * 64}, {})
            self.assertIn('flagged native physicality failure',
                          payload['representatives'][0]['method'])
            self.assertIn('not a structural medoid', payload['representative_kind'])
            self.assertEqual(payload['schemes'][2]['values'][0], -3.0)
            serialized = json.dumps(payload)
            self.assertNotIn('/scratch/', serialized)
            self.assertNotIn('native_path', serialized)
            selection['clusters'][0]['representative']['model_id'] = 'm1'
            (folder / 'representatives-leaf.json').write_text(json.dumps(selection))
            with self.assertRaisesRegex(ValueError, 'energy selection'):
                joint.verified_representatives(folder, 'CDK2_DOC1', 'leaf', labels, rows)

    def test_curated_eom_patch_does_not_modify_hard_linked_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.js'
            body = "\n".join([
                "const views=range.views.filter(view=>['primary','density'].includes(view.id));",
                "current.representatives=raw.representatives.map(row=>{const out={...row};for(const key of ['file','ensemble_file','ensemble_pse']){} });",
                "const response=await fetch(descriptor.file,{cache:'no-cache',signal:AbortSignal.timeout(15000)});",
                "if(descriptor.file.endsWith('.pdb.gz')||descriptor.file.endsWith('.cif.gz')){}",
                "if(digest!==descriptor.sha256)throw Error('Original coordinate hash does not match the selected model.');",
                "const current=data,exact=modelIndex!==null,cluster=exact?pointModelDescriptor(current,modelIndex):current.representatives.find(x=>x.cluster===label);",
                "onChoose:(cluster,model)=>choose(cluster,data.model_files?data.models.indexOf(model):null).catch(fail)",
                "function pointModelDescriptor(current,index){",
                "if(Array.isArray(raw.model_files))current.model_files=raw.model_files.map(path=>rangeAssetPath(path,range));",
                "if(!text){const r=await fetch(c.file,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Medoid file unavailable');text=await r.text();c.coordinate_text=text}",
                "const note=` · medoids of the displayed ensembles`",
                "const nativeDownload=cluster.file;",
            ])
            source.write_text(body)
            stage = root / 'stage'
            stage.mkdir()
            os.link(source, stage / 'app.js')
            joint.patch_curated_eom(stage)
            self.assertEqual(source.read_text(), body)
            patched = (stage / 'app.js').read_text()
            self.assertIn("['primary','density','eom']", patched)
            self.assertIn("descriptor.display_file||descriptor.file", patched)
            self.assertIn("'display_file'", patched)
            self.assertIn("descriptor.display_sha256||descriptor.sha256", patched)
            self.assertIn('bonsaiModelDescriptor(current,modelIndex)', patched)
            self.assertIn('current.bonsai_models=Object.fromEntries', patched)
            self.assertIn('text=await savedCoordinate(c)', patched)
            self.assertIn('energy-selected cluster representatives', patched)
            self.assertIn("const nativeDownload=cluster.file", patched)

    def test_representative_labels_preserve_hard_linked_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.html'
            body = ('<th>Medoid method</th>'
                    '<summary><span>Selected medoid pair</span></summary>'
                    '>Download medoid TM matrix CSV</a>'
                    '>Medoid TM similarity</span>')
            source.write_text(body)
            stage = root / 'stage'
            stage.mkdir()
            os.link(source, stage / 'index.html')
            joint.patch_representative_labels(stage)
            self.assertEqual(source.read_text(), body)
            shown = (stage / 'index.html').read_text()
            self.assertIn('Representative method', shown)
            self.assertIn('Selected representative pair', shown)
            self.assertIn('Download representative TM matrix CSV', shown)

    def test_afsample2_display_copy_preserves_native_download_and_atom_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native = root / 'coordinates'
            native.mkdir()
            raw_lines = [b'REMARK Original native B/C chain labels\n']
            index = 0
            for chain, count in [('B', 298), ('C', 115)]:
                for residue in range(1, count + 1):
                    index += 1
                    line = (f'ATOM  {index:5d}  CA  ALA {chain}{residue:4d}    '
                            '  0.000   0.000   0.000  1.00 90.00           C\n').encode()
                    self.assertEqual(line[21:22], chain.encode())
                    raw_lines.append(line)
            raw = b''.join(raw_lines)
            source = native / 'm0.pdb'
            source.write_bytes(raw)
            row = dict(model_id='m0', native_sha256=hashlib.sha256(raw).hexdigest(),
                       native_path='/private/remote/m0.pdb', method='afsample2')
            stage = root / 'stage'
            stage.mkdir()
            groups = {'leaf': {0: {'representative': row}}}
            files = joint.copy_representatives(stage, 'CDK2_DOC1', groups, [row], native)
            descriptor = files['m0']
            original = gzip.decompress((stage / descriptor['file']).read_bytes())
            display = gzip.decompress((stage / descriptor['display_file']).read_bytes())
            self.assertEqual(original, raw)
            self.assertEqual(descriptor['display_sha256'], hashlib.sha256(display).hexdigest())
            for old, shown in zip(original.splitlines(), display.splitlines()):
                if old.startswith(b'ATOM  '):
                    self.assertEqual(old[:21] + old[22:], shown[:21] + shown[22:])
                    self.assertEqual(shown[21:22], b'A' if old[21:22] == b'B' else b'B')
                else:
                    self.assertEqual(old, shown)
            self.assertNotIn('/private/', json.dumps(descriptor))
            with self.assertRaisesRegex(ValueError, 'Cα chain counts'):
                joint.canonical_afsample2_pdb(raw_lines[0] + b''.join(raw_lines[2:]),
                                               'CDK2_DOC1')

    def test_joint_catalog_keeps_old_afsample3_and_adds_three_views(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            target = 'CDK2_DOC1t'
            (stage / target).mkdir()
            for name in ('primary', 'density', 'eom'):
                (stage / target / f'joint-{name}.json').write_text('{}')
            (stage / 'residue-ranges.json').write_text(json.dumps({'schema_version': 1,
                'targets': {}}))
            old_scope = dict(chain='A,B', chains=[dict(chain='A', expected_ca_count=298),
                                                dict(chain='B', expected_ca_count=55)],
                             expected_ca_count=353, sequence_sha256='a' * 64,
                             canonical_positions=list(range(1, 354)))
            (stage / 'clustering-residues.json').write_text(json.dumps({
                'schema_version': 1, 'targets': {target: {'views': {'whole': old_scope}}}}))
            joint.add_range_catalogs(stage, target, joint.VIEWS, {'chain_lengths': [298, 55]})
            catalog = json.loads((stage / 'residue-ranges.json').read_text())
            ranges = catalog['targets'][target]['residue_ranges']
            self.assertEqual([entry['id'] for entry in ranges], ['all', 'joint'])
            self.assertEqual(ranges[0]['data'], f'{target}/primary.json')
            self.assertEqual({entry['id'] for entry in ranges[1]['views']},
                             {'primary', 'density', 'eom'})
            scope = json.loads((stage / 'clustering-residues.json').read_text())
            self.assertEqual(set(scope['targets'][target]['ranges']['joint']['views']),
                             {'primary', 'density', 'eom'})

    def test_cohort_menu_enables_only_a_verified_joint_range(self):
        source = (ROOT / 'site/cohort_menu.js').read_text()
        self.assertIn("option.value === 'joint' && !option.disabled", source)
        self.assertIn("joint.disabled = !verifiedRange", source)
        self.assertIn("range.dispatchEvent(new Event('change'", source)


if __name__ == '__main__':
    unittest.main()
