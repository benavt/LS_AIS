"""Inspect NumPy headers and text fields; validate numeric payloads as arrays."""
import io,json,math,zipfile
from pathlib import PurePosixPath
from execution_utils import require

def privacy_check_npy(raw,name):
    import numpy as np
    from structure_clustering.privacy import privacy_check
    require(len(raw)<=64*2**20,'NumPy member exceeds inspection limit')
    stream=io.BytesIO(raw);version=np.lib.format.read_magic(stream)
    require(version in [(1,0),(2,0)],'Unsupported NumPy format')
    shape,fortran,dtype=(np.lib.format.read_array_header_1_0(stream) if version==(1,0) else np.lib.format.read_array_header_2_0(stream))
    offset=stream.tell()
    require(not dtype.hasobject and dtype.fields is None and dtype.subdtype is None and dtype.kind in 'biufUS','Opaque/object NumPy payload is not permitted')
    require(len(shape)<=32 and all(type(n) is int and n>=0 for n in shape),'Invalid NumPy shape')
    require(len(raw)==offset+math.prod(shape)*dtype.itemsize,'Incomplete or trailing NumPy payload')
    privacy_check(raw[:offset],name+'.header.txt')
    values=np.frombuffer(raw,dtype=dtype,offset=offset)
    if dtype.kind in 'US':
        for value in values.tolist():
            text=value.decode('utf-8',errors='strict') if isinstance(value,bytes) else value
            privacy_check(json.dumps(text,ensure_ascii=False).encode(),name+'.json')
    else:require(np.isfinite(values).all(),'Nonfinite public numeric trace')

def privacy_check_npz(raw,name):
    from structure_clustering.privacy import privacy_check
    require(len(raw)<=256*2**20 and raw.startswith(b'PK\x03\x04') and raw[-22:-18]==b'PK\x05\x06','Unsupported/trailing NumPy archive bytes')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows=archive.infolist();names=[r.filename for r in rows]
        require(rows and len(names)==len(set(names)) and not archive.comment,'Ambiguous NumPy archive metadata')
        require(rows[0].header_offset==0 and sum(r.file_size for r in rows)<=256*2**20,'NumPy archive exceeds inspection scope')
        for row in rows:
            path=PurePosixPath(row.filename)
            require(path.name==row.filename and path.suffix=='.npy' and not row.comment and not row.extra and not row.flag_bits&1,'Unsupported NumPy member metadata')
            require(row.file_size<=64*2**20,'NumPy member exceeds inspection limit')
            privacy_check(json.dumps(row.filename).encode(),name+'.member.json')
            privacy_check_npy(archive.read(row),name+'/'+row.filename)
