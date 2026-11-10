from pathlib import Path
import importlib.util,json,sys,tempfile,unittest
source=Path(__file__).resolve().parents[1]/'scripts/completion/execution_utils.py'
spec=importlib.util.spec_from_file_location('execution_utils_test',source)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ProducerReceipts(unittest.TestCase):
    def test_final_receipt_wins_over_initial_intent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);attempt=root/'attempt';attempt.mkdir();(attempt/'resources').mkdir()
            (attempt/'workload.sh').write_text('frozen')
            (attempt/'submission.json').write_text(json.dumps({'status':'attempt_recorded'}))
            (attempt/'submission-result.json').write_text(json.dumps({'status':'accepted','job_id':'123','scheduler_script_verified':True,'workload_sha256':m.sha(attempt/'workload.sh')}))
            start={'event':'start','job':'456','array_task':'4','device':'cpu'}
            (attempt/'resources/resource-123_4-456-restart0.log').write_text('[resource] '+json.dumps(start)+'\n')
            service=root/'receipts/E0-user-service-4';service.mkdir(parents=True)
            (service/'worker-result.json').write_text(json.dumps({'return_code':0,'service_limits_verified':True,'stop_reason':None}))
            (service/'launcher-result.json').write_text(json.dumps({'return_code':0}))
            (service/'native-resource.log').write_text('log')
            old=m.log_check;m.log_check=lambda path,monitor,gpu=False:{'job_id':'456'}
            try:
                r=m.finished({'run_root':str(root),'attempts':{'E0':str(attempt)},'monitor':{}},'E0',4)
                self.assertEqual(r['outer']['job_id'],'456')
                (service/'worker-result.json').write_text(json.dumps({'return_code':1,'service_limits_verified':True,'stop_reason':None}))
                with self.assertRaises(ValueError):m.finished({'run_root':str(root),'attempts':{'E0':str(attempt)},'monitor':{}},'E0',4)
            finally:m.log_check=old
if __name__=='__main__':unittest.main()
