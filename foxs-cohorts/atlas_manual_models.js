/* Exact-model manual collections. Original coordinate bytes are never mutated. */
(function(root){'use strict';
const LIMITS=Object.freeze({models:50,atoms:250000,sourceBytes:64*1024*1024}),VERSION=1;
const need=(ok,message)=>{if(!ok)throw Error(message)},missing=v=>v===undefined||v==='.'||v==='?';
const number=(v,name)=>{need(!missing(v)&&String(v).trim()!==''&&Number.isFinite(Number(v)),'Invalid '+name);return Number(v)};
const identityFit=()=>({rotation:[[1,0,0],[0,1,0],[0,0,1]],translation:[0,0,0]});
function point(p,fit){return fit.rotation.map((row,i)=>row.reduce((n,v,j)=>n+v*p[j],fit.translation[i]))}
function descriptor(d){
 need(d&&typeof d.model==='string'&&d.model.length>0&&d.model.length<=512&&!/[\x00-\x1f\x7f]/.test(d.model),'Invalid model identity');
 need(typeof d.sha256==='string'&&/^[a-f0-9]{64}$/.test(d.sha256),'An exact coordinate hash is required');
 need(typeof d.file==='string'&&d.file.length<=2048&&!d.file.startsWith('/')&&!/[\\:?#]/.test(d.file)&&!d.file.split('/').some(x=>!x||x==='.'||x==='..'),'Unsafe coordinate path');
 const decoded=decodeURIComponent(d.file);need(!decoded.startsWith('/')&&!/[\\:?#]/.test(decoded)&&!decoded.split('/').some(x=>x==='.'||x==='..'),'Unsafe encoded coordinate path');
 const format=d.file.replace(/\.gz$/i,'').split('.').pop().toLowerCase();need(['pdb','cif','mmcif'].includes(format),'Unsupported coordinate format');
 need(!d.representation||d.representation==='full_atom','Only full saved structures can enter the collection; this view provides a display derivative');
 return {model:d.model,sha256:d.sha256,file:d.file,format:format==='mmcif'?'cif':format,method:String(d.method||''),representation:'full_atom'};
}
const key=d=>d.model+'\n'+d.sha256;
// Includes a synchronous fallback for private HTTP previews without WebCrypto.
function sha256(input){
 const bytes=input instanceof Uint8Array?input:new Uint8Array(input),K=[1116352408,1899447441,3049323471,3921009573,961987163,1508970993,2453635748,2870763221,3624381080,310598401,607225278,1426881987,1925078388,2162078206,2614888103,3248222580,3835390401,4022224774,264347078,604807628,770255983,1249150122,1555081692,1996064986,2554220882,2821834349,2952996808,3210313671,3336571891,3584528711,113926993,338241895,666307205,773529912,1294757372,1396182291,1695183700,1986661051,2177026350,2456956037,2730485921,2820302411,3259730800,3345764771,3516065817,3600352804,4094571909,275423344,430227734,506948616,659060556,883997877,958139571,1322822218,1537002063,1747873779,1955562222,2024104815,2227730452,2361852424,2428436474,2756734187,3204031479,3329325298];
 const padded=new Uint8Array(Math.ceil((bytes.length+9)/64)*64);padded.set(bytes);padded[bytes.length]=128;const dv=new DataView(padded.buffer);dv.setUint32(padded.length-8,Math.floor(bytes.length/536870912));dv.setUint32(padded.length-4,(bytes.length*8)>>>0);
 const h=[1779033703,3144134277,1013904242,2773480762,1359893119,2600822924,528734635,1541459225],w=new Uint32Array(64),rr=(v,n)=>(v>>>n)|(v<<(32-n));
 for(let o=0;o<padded.length;o+=64){for(let j=0;j<16;j++)w[j]=dv.getUint32(o+4*j);for(let j=16;j<64;j++){const a=w[j-15],b=w[j-2];w[j]=(w[j-16]+(rr(a,7)^rr(a,18)^(a>>>3))+w[j-7]+(rr(b,17)^rr(b,19)^(b>>>10)))>>>0}let[a,b,c,d,e,f,g,z]=h;for(let j=0;j<64;j++){const t1=(z+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+K[j]+w[j])>>>0,t2=((rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c)))>>>0;z=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0}for(const[j,v]of[a,b,c,d,e,f,g,z].entries())h[j]=(h[j]+v)>>>0}
 return h.map(v=>v.toString(16).padStart(8,'0')).join('');
}
async function readCoordinate(d,fetcher=root.fetch){
 d=descriptor(d);const response=await fetcher(d.file,{cache:'no-cache',signal:AbortSignal.timeout(30000)});need(response.ok,'Coordinate unavailable (HTTP '+response.status+')');
 const length=Number(response.headers?.get?.('Content-Length'));need(!length||length<=LIMITS.sourceBytes,'Coordinate file exceeds the read limit');
 let bytes;
 if(response.body?.getReader){const reader=response.body.getReader(),chunks=[];let count=0;try{while(true){const {done,value}=await reader.read();if(done)break;count+=value.length;need(count<=LIMITS.sourceBytes,'Coordinate file exceeds the read limit');chunks.push(value)}}catch(e){await reader.cancel();throw e}bytes=new Uint8Array(count);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}}
 else{bytes=new Uint8Array(await response.arrayBuffer());need(bytes.length<=LIMITS.sourceBytes,'Coordinate file exceeds the read limit')}
 if(/\.gz$/i.test(d.file)&&bytes[0]===31&&bytes[1]===139){need(typeof DecompressionStream!=='undefined','This browser cannot decompress coordinates');const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')),reader=stream.getReader(),chunks=[];let size=0;try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;need(size<=LIMITS.sourceBytes,'Inflated coordinate file exceeds the read limit');chunks.push(value)}}catch(e){await reader.cancel();throw e}bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length}}
 need(sha256(bytes)===d.sha256,'Original coordinate hash does not match '+d.model);
 return new TextDecoder('utf-8',{fatal:true}).decode(bytes);
}
function tokens(text){
 const out=[];let i=0;
 while(i<text.length){if(/\s/.test(text[i])){i++;continue}if(text[i]==='#'){while(i<text.length&&text[i]!=='\n')i++;continue}const start=i;let value,quoted=false;
  if(text[i]===';'&&(i===0||text[i-1]==='\n')){quoted=true;const end=text.indexOf('\n;',i+1);need(end>=0,'Unclosed CIF text field');value=text.slice(i+1,end);i=end+2}
  else if(text[i]==="'"||text[i]==='"'){quoted=true;const q=text[i++],begin=i;while(i<text.length&&!(text[i]===q&&(i+1===text.length||/\s/.test(text[i+1]))))i++;need(i<text.length,'Unclosed CIF quote');value=text.slice(begin,i++)}
  else{while(i<text.length&&!/\s/.test(text[i]))i++;value=text.slice(start,i)}
  out.push({value,start,end:i,quoted});
 }
 return out;
}
const control=t=>t&&!t.quoted&&(/^(?:data_|save_)/i.test(t.value)||/^(?:loop_|stop_|global_)$/i.test(t.value)||t.value.startsWith('_'));
function parseCIF(text){
 const ts=tokens(text),loops=[];let blocks=0;
 for(let i=0;i<ts.length;){const t=ts[i];if(!t.quoted&&/^data_/i.test(t.value)){blocks++;i++;continue}if(t.value!=='loop_'||t.quoted){i++;continue}
  const tags=[];i++;while(i<ts.length&&!ts[i].quoted&&ts[i].value.startsWith('_'))tags.push(ts[i++].value);need(tags.length,'CIF loop has no tags');const rows=[];
  while(i<ts.length&&!control(ts[i])){need(i+tags.length<=ts.length,'Incomplete CIF loop row');const row=ts.slice(i,i+tags.length);need(!row.some(control),'Incomplete CIF loop row');rows.push(row);i+=tags.length}
  loops.push({tags,rows});
 }
 need(blocks===1,'An exact model file must contain one CIF data block');
 const atomLoops=loops.filter(l=>l.tags.some(t=>t.toLowerCase().startsWith('_atom_site.')));need(atomLoops.length===1,'One atom_site loop is required');const loop=atomLoops[0],cols=Object.fromEntries(loop.tags.map((s,i)=>[s.toLowerCase().slice(11),i]));
 const get=(row,...names)=>{for(const n of names)if(cols[n]!==undefined&&!missing(row[cols[n]].value))return row[cols[n]].value;return undefined};
 for(const n of ['cartn_x','cartn_y','cartn_z'])need(cols[n]!==undefined,'CIF lacks '+n);
 const atoms=loop.rows.map(row=>({record:get(row,'group_pdb')||'ATOM',serial:get(row,'id'),name:get(row,'auth_atom_id','label_atom_id'),alt:get(row,'label_alt_id','pdbx_pdb_alt_id')||'',resn:get(row,'auth_comp_id','label_comp_id'),chain:get(row,'auth_asym_id','label_asym_id')||'',resi:get(row,'auth_seq_id','label_seq_id'),icode:get(row,'pdbx_pdb_ins_code')||'',x:number(get(row,'cartn_x'),'x coordinate'),y:number(get(row,'cartn_y'),'y coordinate'),z:number(get(row,'cartn_z'),'z coordinate'),occupancy:missing(get(row,'occupancy'))?null:number(get(row,'occupancy'),'occupancy'),b:missing(get(row,'b_iso_or_equiv'))?null:number(get(row,'b_iso_or_equiv'),'B factor'),element:get(row,'type_symbol')||'',charge:get(row,'pdbx_formal_charge')||'',frame:get(row,'pdbx_pdb_model_num')||'1',row}));
 need(new Set(atoms.map(a=>a.frame)).size===1,'Select an exact single-frame coordinate file');need(atoms.length&&atoms.length<=LIMITS.atoms,'Coordinate atom count exceeds the collection limit');
 const chemistry=loops.some(l=>l.rows.length&&l.tags.some(t=>/^_(?:struct_conn|atom_site_anisotrop)\./i.test(t)));
 return {format:'cif',text,atoms,loop,loops,cols,chemistry};
}
function parsePDB(text){
 const lines=text.replace(/\r\n/g,'\n').split('\n'),atoms=[];let frames=0,chemistry=false,inside=false,ended=false,outside=false;
 for(const [lineIndex,line]of lines.entries()){
  const record=line.slice(0,6).trim();if(record==='MODEL'){need(!inside&&!outside&&!ended,'Mixed or repeated PDB model frames');frames++;inside=true}if(record==='ENDMDL'){need(inside,'Unmatched ENDMDL');inside=false;ended=true}if(record==='END')ended=true;if(['ANISOU','SIGUIJ','CONECT','LINK','SSBOND'].includes(record))chemistry=true;
  if(!['ATOM','HETATM'].includes(record))continue;need(!ended,'Atom records occur after the model ended');if(!inside)outside=true;need(line.length>=54,'Truncated PDB atom record');
  atoms.push({record,serial:line.slice(6,11).trim(),name:line.slice(12,16).trim(),alt:line.slice(16,17).trim(),resn:line.slice(17,20).trim(),chain:line.slice(21,22).trim(),resi:line.slice(22,26).trim(),icode:line.slice(26,27).trim(),x:number(line.slice(30,38),'x coordinate'),y:number(line.slice(38,46),'y coordinate'),z:number(line.slice(46,54),'z coordinate'),occupancy:line.slice(54,60).trim()?number(line.slice(54,60),'occupancy'):null,b:line.slice(60,66).trim()?number(line.slice(60,66),'B factor'):null,element:line.slice(76,78).trim(),charge:line.slice(78,80).trim(),lineIndex});
 }
 need(frames<=1&&!inside,'Select an exact, complete single-frame coordinate file');need(atoms.length&&atoms.length<=LIMITS.atoms,'Coordinate atom count exceeds the collection limit');return {format:'pdb',text,lines,atoms,chemistry};
}
function parse(text,format){return format==='pdb'?parsePDB(text):parseCIF(text)}
function validateLimits(frames){need(frames.length<=LIMITS.models,'Selection limit: 50 models');const atoms=frames.reduce((n,f)=>n+f.parsed.atoms.length,0);need(atoms<=LIMITS.atoms,'Selection limit: 250,000 full-structure atoms');need(new Set(frames.map(f=>key(f.descriptor))).size===frames.length,'Duplicate selected model');return atoms}
function field(value,width,label,align='right'){value=String(value??'');need(!/[\n\r]/.test(value)&&value.length<=width,'PDB cannot preserve '+label);return align==='right'?value.padStart(width):value.padEnd(width)}
function fixed(value,width,precision,label){need(Number.isFinite(value),'Nonfinite '+label);return field(value.toFixed(precision),width,label)}
function pdbAtom(a,fit){
 need(['ATOM','HETATM'].includes(a.record),'Unsupported PDB atom kind');need(/^\d+$/.test(a.serial||'')&&Number(a.serial)>0&&Number(a.serial)<=99999,'PDB atom serial cannot be preserved');
 need(/^-?\d+$/.test(a.resi||'')&&Number(a.resi)>=-999&&Number(a.resi)<=9999,'PDB residue number cannot be preserved');
 need(a.occupancy!==null&&a.b!==null,'PDB would invent missing occupancy or B-factor observations');
 const xyz=point([a.x,a.y,a.z],fit),name=String(a.name||'');need(name&&name.length<=4,'PDB atom name cannot be preserved');let charge=a.charge;
 if(charge&&/^-?\d+$/.test(charge)){const n=Number(charge);need(Math.abs(n)<=9,'PDB charge cannot be preserved');charge=n?Math.abs(n)+(n<0?'-':'+'):''}
 const atomName=name.length<4&&a.element.length===1&&!/^\d/.test(name)?(' '+name).padEnd(4):name.padEnd(4);
 return field(a.record,6,'atom kind','left')+field(a.serial,5,'serial')+' '+atomName+field(a.alt,1,'alternate location','left')+field(a.resn,3,'residue name')+' '+field(a.chain,1,'chain','left')+field(a.resi,4,'residue number')+field(a.icode,1,'insertion code','left')+'   '+xyz.map((v,i)=>fixed(v,8,3,'xyz'[i]+' coordinate')).join('')+fixed(a.occupancy,6,2,'occupancy')+fixed(a.b,6,2,'B factor')+'          '+field(a.element,2,'element')+field(charge,2,'charge');
}
function pdbBody(parsed,fit){
 need(!parsed.chemistry,'PDB export cannot safely merge connectivity or anisotropic records; use the lossless mmCIF collection');
 need(parsed.atoms.length<=99999,'PDB atom count cannot be represented');const ids=new Set();for(const a of parsed.atoms){need(!ids.has(a.serial),'PDB atom IDs are not unique');ids.add(a.serial)}
 if(parsed.format==='pdb'){
  return []; // Native atom fields are retained by transformedPDBLines after validation.
 }
 return parsed.atoms.map(a=>pdbAtom(a,fit));
}
function transformedPDBLines(parsed,fit){
 // Validate representability even when preserving native record spelling.
 for(const a of parsed.atoms)pdbAtom(a,fit);
 const byLine=new Map(parsed.atoms.map(a=>[a.lineIndex,a]));return parsed.lines.flatMap((line,i)=>{const a=byLine.get(i);if(a){const xyz=point([a.x,a.y,a.z],fit);return [line.slice(0,30)+xyz.map(v=>fixed(v,8,3,'coordinate')).join('')+line.slice(54)]}return line.slice(0,6).trim()==='TER'?[line]:[]});
}
function cifValue(v){v=String(v);if(v==='.'||v==='?')return v;if(v&&!/\s|['"#]/.test(v)&&!/^_|^(?:data_|loop_|stop_|save_|global_)/i.test(v))return v;if(!v.includes("'")&&!v.includes('\n'))return "'"+v+"'";if(!v.includes('"')&&!v.includes('\n'))return '"'+v+'"';need(!/^;/m.test(v),'CIF text contains a semicolon delimiter');return '\n;'+v+'\n;\n'}
function transformedCIF(parsed,fit,index){
 // All non-coordinate source tokens, including chemistry, are retained per data block.
 need(!parsed.loops.some(l=>l.tags.some(t=>t.toLowerCase().startsWith('_atom_site_anisotrop.'))),'Anisotropic tensors require a tensor-aware export; original coordinates remain available');
 const edits=[];for(const a of parsed.atoms){const xyz=point([a.x,a.y,a.z],fit);['cartn_x','cartn_y','cartn_z'].forEach((c,i)=>edits.push({...a.row[parsed.cols[c]],replacement:xyz[i].toFixed(6)}))}
 const first=tokens(parsed.text).find(t=>!t.quoted&&/^data_/i.test(t.value));edits.push({...first,replacement:'data_selection_'+index});let text=parsed.text;for(const e of edits.sort((a,b)=>b.start-a.start))text=text.slice(0,e.start)+e.replacement+text.slice(e.end);return text;
}
function pdbToCIF(parsed,fit,index){
 need(!parsed.lines.some(l=>/^(?:ANISOU|SIGUIJ)/.test(l)),'Anisotropic tensors require a tensor-aware export; original coordinates remain available');
 const tags=['group_PDB','id','type_symbol','label_atom_id','label_alt_id','label_comp_id','label_asym_id','label_entity_id','label_seq_id','pdbx_PDB_ins_code','Cartn_x','Cartn_y','Cartn_z','occupancy','B_iso_or_equiv','pdbx_formal_charge','auth_seq_id','auth_comp_id','auth_asym_id','auth_atom_id','pdbx_PDB_model_num'];
 return 'data_selection_'+index+'\n#\nloop_\n'+tags.map(t=>'_atom_site.'+t).join('\n')+'\n'+parsed.atoms.map(a=>{const xyz=point([a.x,a.y,a.z],fit);return[a.record,a.serial,a.element||'?',a.name,a.alt||'.',a.resn,a.chain||'_blank','.','.',a.icode||'?',...xyz.map(v=>v.toFixed(6)),a.occupancy??'?',a.b??'?',a.charge?.replace(/^(\d)([+-])$/,(_,n,sign)=>sign==='-'?'-'+n:n)||'?',a.resi,a.resn,a.chain,a.name,1].map(cifValue).join(' ')}).join('\n')+'\n#\n_atlas_original_pdb.coordinate_frame original\n_atlas_original_pdb.text\n;'+parsed.text+'\n;\n';
}
function exportCollection(frames,context){
 need(frames.length,'Select at least one model');const atoms=validateLimits(frames);let reason=null,pdb=[];
 try{for(const [i,f]of frames.entries()){need(f.fit,'A selection alignment is missing');const lines=pdbBody(f.parsed,f.fit);pdb.push('MODEL     '+field(i+1,4,'model number'),...JSON.stringify(f.descriptor.model).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0')).match(/.{1,60}/g).map(part=>'REMARK 950 SOURCE '+part),...(f.parsed.format==='pdb'?transformedPDBLines(f.parsed,f.fit):lines),'ENDMDL')}pdb.push('END')}
 catch(error){reason=error.message}
 let format='pdb',text=pdb.join('\n')+'\n',layout='MODEL/ENDMDL';
 if(reason){format='cif';layout='one complete data block per selected model';text=frames.map((f,i)=>f.parsed.format==='cif'?transformedCIF(f.parsed,f.fit,i+1):pdbToCIF(f.parsed,f.fit,i+1)).join('\n')}
 const provenance={schema_version:VERSION,kind:'manual_structure_selection',created_at:new Date().toISOString(),...context,coordinate_scope:'full_saved_structure',alignment:'proper rigid C-alpha fit; no scaling or pruning',format,layout,coordinate_precision_A:format==='pdb'?.001:.000001,pdb_fallback_reason:reason,model_count:frames.length,atom_count:atoms,models:frames.map((f,i)=>({model_number:i+1,...f.descriptor,atom_count:f.parsed.atoms.length,display_chain_map:f.chainMap||null,transform:f.fit})),export_sha256:sha256(new TextEncoder().encode(text))};
 return {format,text,provenance};
}
class Collections{
 constructor(storage,scope=''){this.storage=storage;this.buckets=new Map();this.namespace='atlas.manual-models.v1:'+(scope?scope+':':'')}
 get(target){if(!this.buckets.has(target)){let state={members:[],overlay:false};try{const raw=JSON.parse(this.storage?.getItem(this.namespace+target)||'null');if(raw?.version===VERSION&&raw.members?.length<=LIMITS.models){const members=raw.members.map(descriptor);need(new Set(members.map(key)).size===members.length,'Duplicate stored member');state={members,overlay:!!raw.overlay}}}catch{}this.buckets.set(target,state)}return this.buckets.get(target)}
 save(target,members,overlay){need(members.length<=LIMITS.models,'Selection limit: 50 models');const state={members:members.map(descriptor),overlay:!!overlay};need(new Set(state.members.map(key)).size===state.members.length,'Duplicate member');this.buckets.set(target,state);try{this.storage?.setItem(this.namespace+target,JSON.stringify({version:VERSION,...state}))}catch{}return state}
 clear(target){return this.save(target,[],false)}
}
const api={VERSION,LIMITS,descriptor,key,sha256,readCoordinate,parse,tokens,point,identityFit,validateLimits,pdbAtom,exportCollection,Collections};
if(typeof module==='object'&&module.exports)module.exports=api;root.AISManualModels=api;
})(typeof window==='undefined'?globalThis:window);
