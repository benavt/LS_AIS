from pathlib import Path
import io,sys,tempfile,unittest
import numpy as np
SOURCE=Path(__file__).resolve().parents[1]/'scripts/completion';sys.path.insert(0,str(SOURCE))
from delivery_arrays import privacy_check_npy,privacy_check_npz
from structure_clustering.privacy import privacy_check

class DeliveryArrays(unittest.TestCase):
    def npy(self,value):
        out=io.BytesIO();np.save(out,value,allow_pickle=value.dtype.hasobject);return out.getvalue()
    def test_numeric_byte_pattern_is_validated_as_numeric_data(self):
        # Finite float64 bytes happen to contain a path-like ASCII sequence.
        raw=self.npy(np.frombuffer(b'c:/x\0\0\0\0',dtype='<f8'))
        with self.assertRaises(ValueError):privacy_check(raw,'trace.npy')
        privacy_check_npy(raw,'trace.npy')
    def test_private_strings_remain_blocking(self):
        for value in [np.asarray(['/scratch/person/private']),np.asarray([b'/home/person/private'])]:
            with self.subTest(dtype=str(value.dtype)),self.assertRaises(ValueError):privacy_check_npy(self.npy(value),'names.npy')
    def test_object_and_opaque_arrays_are_rejected(self):
        for value in [np.asarray([{'name':'unsafe'}],dtype=object),np.asarray([b'abcd'],dtype='V4')]:
            with self.subTest(dtype=str(value.dtype)),self.assertRaises(ValueError):privacy_check_npy(self.npy(value),'opaque.npy')
    def test_trailing_and_incomplete_payloads_are_rejected(self):
        raw=self.npy(np.asarray([1.,2.]))
        for bad in [raw+b'/scratch/person/private',raw[:-1]]:
            with self.assertRaises(ValueError):privacy_check_npy(bad,'trace.npy')
    def test_valid_archive_preserves_numeric_and_public_string_members(self):
        out=io.BytesIO();np.savez_compressed(out,trace=np.frombuffer(b'c:/x\0\0\0\0',dtype='<f8'),model_ids=np.asarray(['model-1','model-2']))
        raw=out.getvalue();privacy_check_npz(raw,'chains.npz')
        with np.load(io.BytesIO(raw),allow_pickle=False) as values:self.assertEqual(values['model_ids'].tolist(),['model-1','model-2'])
        with self.assertRaises(ValueError):privacy_check_npz(raw+b'extra','chains.npz')
    def test_archive_private_text_remains_blocking(self):
        out=io.BytesIO();np.savez_compressed(out,model_ids=np.asarray(['/home/person/private']))
        with self.assertRaises(ValueError):privacy_check_npz(out.getvalue(),'private.npz')

if __name__=='__main__':unittest.main()
