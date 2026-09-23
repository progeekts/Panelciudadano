(()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const render=()=>{
  const meta=window.PanelCiudadano?.getServiceMeta?.(),root=document.querySelector('#serviceSources');
  if(!meta||!root)return;
  const all=meta.salud_fuentes||[],det=all.filter(x=>x.tipo==='detector'),cov=all.filter(x=>x.tipo==='cobertura');
  const detOk=det.filter(x=>x.estado==='ok').length,covOk=cov.filter(x=>x.estado==='ok').length,issues=cov.filter(x=>x.estado!=='ok');
  const territories=[...new Set(cov.map(x=>x.ambito).filter(Boolean))];
  root.innerHTML=`<div class="coverage-public">
   <div class="coverage-kpis">
    <article><strong>${detOk}/${det.length}</strong><span>detectores de incidencias revisados</span></article>
    <article><strong>${covOk}/${cov.length}</strong><span>fuentes de cobertura accesibles</span></article>
    <article><strong>${territories.length}</strong><span>ámbitos estatales o territoriales comprobados</span></article>
   </div>
   <div class="coverage-explain"><strong>Qué significa</strong><p>Los detectores buscan avisos oficiales de incidencias. Las comprobaciones de cobertura solo verifican que podemos consultar una fuente pública; un fallo de consulta no significa que el servicio público esté caído.</p></div>
   ${issues.length?`<details class="coverage-unavailable"><summary>${issues.length} fuentes no pudieron comprobarse en esta revisión</summary><div>${issues.map(x=>`<span><strong>${esc(x.fuente)}</strong><small>${esc(x.ambito||'España')} · comprobación no disponible</small></span>`).join('')}</div></details>`:'<p class="coverage-all-ok">Todas las fuentes auxiliares respondieron en esta revisión.</p>'}
   <details class="coverage-audit"><summary>Ver detalle de fuentes revisadas</summary><div class="source-table">${all.map(x=>`<div><span><strong>${esc(x.fuente)}</strong><small>${esc(x.ambito||'España')}</small></span><span class="source-kind">${x.tipo==='detector'?'Detector de incidencias':'Cobertura'}</span><span class="health-state ${x.estado==='ok'?'ok':'partial'}"><i></i>${x.estado==='ok'?'Revisada':'No comprobada'}</span></div>`).join('')}</div></details>
  </div>`;
  const summary=root.closest('details')?.querySelector('summary');if(summary)summary.textContent='Ver cobertura y estado de las fuentes';
 };
 document.addEventListener('panel:data-ready',render);if(document.readyState!=='loading')setTimeout(render,0);else document.addEventListener('DOMContentLoaded',()=>setTimeout(render,0));
})();
