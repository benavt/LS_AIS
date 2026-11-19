/* Bind shared inspection maps to the unchanged reviewed compact controller. */
(function(root){
'use strict';
const doc=root.document,shared=root.AtlasDistanceMaps,catalog=root.AtlasMapsCatalog;
if(!doc||!shared||!catalog)return;
const explorer=doc.getElementById('atlasCompactExplorer');
if(!explorer)return;
const host=doc.createElement('div');host.id='atlasCohortDistanceMaps';explorer.insertAdjacentElement('afterend',host);
const widget=shared.createWidget({container:host,loader:shared.createLoader(catalog.bindings),ready:root.AtlasUILayout?.ready});
let active=null,destroyed=false,started=false;
const listeners=[];
function clear(note){active=null;widget.clear(note||'Loading the selected saved cohort…');}
function synchronize(){
 if(destroyed||!started)return;
 const state=root.AtlasInspection?.state?.(),id=state?.dataset,bound=doc.documentElement.dataset.cohort;
 if(!id||id!==bound){clear();return;}
 if(active===id)return;
 clear();active=id;
 const context=catalog.datasets[id];
 if(!context){widget.clear('No saved distance maps match this exact active model and residue cohort.');return;}
 if(context.datasetId!==id||(context.presentation_data_sha256||context.cohort_data_sha256)!==state.source_sha256){clear('Saved distance-map context differs from the selected cohort.');return;}
 return widget.setContext(context);
}
function listen(node,event,callback,options){node.addEventListener(event,callback,options);listeners.push(()=>node.removeEventListener(event,callback,options));}
// Capture before the native change handler starts loading. It remains the sole
// owner of dataset selection; this bridge only invalidates stale map content.
for(const id of ['target','cohort','range']){const node=doc.getElementById(id);if(node)listen(node,'change',()=>clear(),true);}
listen(root,'hashchange',()=>{const desired=new root.URLSearchParams(root.location.hash.slice(1)).get('dataset');if(desired&&desired!==active)clear();root.queueMicrotask(synchronize);});
const observer=new root.MutationObserver(synchronize);
observer.observe(doc.documentElement,{attributes:true,attributeFilter:['data-cohort']});
// Native loading replaces selector options before its first await, including
// public selectDataset calls. Observe that signal without wrapping its API.
for(const id of ['target','cohort','range','view']){const node=doc.getElementById(id);if(node)observer.observe(node,{attributes:true,attributeFilter:['disabled'],childList:true,subtree:true});}
const ready=Promise.all([root.AtlasInspection?.ready,root.AtlasUILayout?.ready,widget.ready]).then(async()=>{started=true;await synchronize();return widget.getSnapshot();}).catch(error=>{clear('Saved distance maps are unavailable: '+(error.message||String(error)));return widget.getSnapshot();});
root.AtlasMaps={ready,getState:widget.getState,setState:widget.setState,getView:widget.getView,setView:widget.setView,
 getSnapshot:widget.getSnapshot,resetDisplay:widget.resetDisplay,resetView:widget.resetView,download:widget.download,
 refresh:synchronize,destroy(){destroyed=true;observer.disconnect();for(const off of listeners)off();widget.destroy();host.remove();}};
})(window);
