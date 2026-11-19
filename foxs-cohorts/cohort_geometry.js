/* Shared display geometry. Fits never alter the saved coordinate bytes. */
(function(root){'use strict';
const need=(ok,message)=>{if(!ok)throw Error(message)};
function atomKey(atom,asset){
 const native=String(atom.chain||'')+':'+String(atom.resi)+(atom.icode||'').trim();
 if(asset.residue_map)return asset.residue_map[native]||null;
 need(asset.residue_numbering==='canonical','Explicit residue numbering is required');
 const chain=asset.chain_map?.[String(atom.chain||'')];
 return chain===undefined?null:chain+':'+String(atom.resi)+(atom.icode||'').trim();
}
function fitPoints(atoms,asset,mask){
 const byKey=new Map();for(const a of atoms){if((a.name||a.atom)!=='CA')continue;const k=atomKey(a,asset);if(k===null)continue;need(!byKey.has(k),'Ambiguous C-alpha identity '+k);byKey.set(k,a)}
 return mask.map(k=>{const a=byKey.get(k);need(a,'Missing alignment residue '+k);return [a.x,a.y,a.z]});
}
function rigidFit(mobile,reference){
 need(mobile.length===reference.length&&mobile.length>=3&&[...mobile,...reference].every(p=>p.length===3&&p.every(Number.isFinite)),'Alignment coordinates do not match');
 const center=ps=>[0,1,2].map(i=>ps.reduce((s,p)=>s+p[i],0)/ps.length),mc=center(mobile),rc=center(reference);
 const x=mobile.map(p=>p.map((v,i)=>v-mc[i])),y=reference.map(p=>p.map((v,i)=>v-rc[i]));
 for(const ps of [x,y]){const lengths=ps.map(p=>p.reduce((s,v)=>s+v*v,0)),axis=ps[lengths.indexOf(Math.max(...lengths))],scale=Math.max(...lengths),area=Math.max(...ps.map(p=>[axis[1]*p[2]-axis[2]*p[1],axis[2]*p[0]-axis[0]*p[2],axis[0]*p[1]-axis[1]*p[0]].reduce((s,v)=>s+v*v,0)));need(scale>1e-12&&area>1e-12*scale*scale,'Alignment residues do not define a stable orientation')}
 const s=[0,1,2].map(i=>[0,1,2].map(j=>x.reduce((sum,p,k)=>sum+p[i]*y[k][j],0))),[[a,b,c],[d,e,f],[g,h,i]]=s;
 const n=[[a+e+i,f-h,g-c,b-d],[f-h,a-e-i,b+d,c+g],[g-c,b+d,-a+e-i,f+h],[b-d,c+g,f+h,-a-e+i]],v=Array.from({length:4},(_,r)=>Array.from({length:4},(_,c)=>Number(r===c)));
 for(let sweep=0;sweep<64;sweep++){let p=0,q=1;for(let r=0;r<4;r++)for(let c=r+1;c<4;c++)if(Math.abs(n[r][c])>Math.abs(n[p][q])){p=r;q=c}if(Math.abs(n[p][q])<1e-13*Math.max(1,...n.map((row,r)=>Math.abs(row[r]))))break;const angle=.5*Math.atan2(2*n[p][q],n[q][q]-n[p][p]),cs=Math.cos(angle),sn=Math.sin(angle),pp=n[p][p],qq=n[q][q],pq=n[p][q];for(let r=0;r<4;r++)if(r!==p&&r!==q){const rp=n[r][p],rq=n[r][q];n[r][p]=n[p][r]=cs*rp-sn*rq;n[r][q]=n[q][r]=sn*rp+cs*rq}n[p][p]=cs*cs*pp-2*sn*cs*pq+sn*sn*qq;n[q][q]=sn*sn*pp+2*sn*cs*pq+cs*cs*qq;n[p][q]=n[q][p]=0;for(let r=0;r<4;r++){const rp=v[r][p],rq=v[r][q];v[r][p]=cs*rp-sn*rq;v[r][q]=sn*rp+cs*rq}}
 const diag=n.map((row,r)=>row[r]),col=diag.indexOf(Math.max(...diag)),qq=v.map(row=>row[col]),norm=Math.hypot(...qq),[w,qx,qy,qz]=qq.map(x=>x/norm);
 const rotation=[[1-2*(qy*qy+qz*qz),2*(qx*qy-qz*w),2*(qx*qz+qy*w)],[2*(qx*qy+qz*w),1-2*(qx*qx+qz*qz),2*(qy*qz-qx*w)],[2*(qx*qz-qy*w),2*(qy*qz+qx*w),1-2*(qx*qx+qy*qy)]],translation=rc.map((a,r)=>a-rotation[r].reduce((sum,v,c)=>sum+v*mc[c],0));
 need([...rotation.flat(),...translation].every(Number.isFinite),'Nonfinite display alignment');return {rotation,translation};
}
function modelColor(id){let hash=2166136261;for(const c of id){hash^=c.charCodeAt(0);hash=Math.imul(hash,16777619)}const h=(hash>>>0)%360/60,s=.58,l=.44,c=(1-Math.abs(2*l-1))*s,x=c*(1-Math.abs(h%2-1)),m=l-c/2,rgb=h<1?[c,x,0]:h<2?[x,c,0]:h<3?[0,c,x]:h<4?[0,x,c]:h<5?[x,0,c]:[c,0,x];return '#'+rgb.map(v=>Math.round((v+m)*255).toString(16).padStart(2,'0')).join('')}
const api={atomKey,fitPoints,rigidFit,modelColor};root.CohortGeometry=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window==='undefined'?globalThis:window);
