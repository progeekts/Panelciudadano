/* Identidad estable de interfaz: tipo:id. Evita colisiones entre radares. */
(()=>{
const api=window.PanelCiudadano;if(!api)return;
const itemKey=x=>x?`${x.type}:${x.id}`:'';
const getItem=(type,id)=>api.getItems().find(x=>String(x.type)===String(type)&&String(x.id)===String(id))||null;
const getByKey=key=>{const p=String(key||'').indexOf(':');return p<0?null:getItem(String(key).slice(0,p),String(key).slice(p+1))};
api.itemKey=itemKey;api.getItem=getItem;api.getItemByKey=getByKey;
const baseOpen=openCard;
openCard=function(type,id){
  if(id===undefined){const matches=api.getItems().filter(x=>String(x.id)===String(type));if(matches.length!==1)return;baseOpen(matches[0].id);return}
  const x=getItem(type,id);if(!x)return;
  lastFocus=document.activeElement;
  const view=window.PanelAllView,h=view?.historyMeta?.(x),shown=view?.displayState?.(x)||x.status;
  const changedText=view?.freshnessText?.(x)||'',changed=!!changedText;
  const sectionName={ayudas:'Datos de la convocatoria',estafas:'Información sobre el fraude',servicios:'Estado de la incidencia',alimentacion:'Información de la alerta alimentaria',salud:'Información del aviso sanitario',meteo:'Información del aviso meteorológico'}[x.type]||'Información del aviso';
  const cleanDetail=String(x.detail||'').trim(),sameDetail=cleanDetail&&cleanDetail.replace(/\\s+/g,' ').trim()===String(x.summary||'').replace(/\\s+/g,' ').trim();
  const detailHtml=cleanDetail&&!sameDetail?`<section class="modal-info"><h3>${esc(sectionName)}</h3><div class="detail"><p>${esc(cleanDetail).replace(/\\n\\n+/g,'</p><p>').replace(/\\n/g,'<br>')}</p></div></section>`:'';
  $('#modalContent').innerHTML=`<div class="meta"><span class="pill ${x.type}">${types[x.type]?.name}</span><span class="pill state ${statusClass(shown)}">${esc(shown)}</span>${changed?`<span class="pill state modal-updated">${esc(changedText)}</span>`:''}</div><h2>${esc(x.title)}</h2><p class="modal-lead">${esc(x.summary)}</p>${detailHtml}<div class="facts"><span><b>Ámbito</b>${esc(x.scope||'No indicado')}</span><span><b>Fecha de publicación / referencia</b>${esc(x.date||'No indicada')}</span><span><b>Nivel / referencia</b>${esc(x.level||'Fuente oficial')}</span>${changed?`<span><b>Último cambio detectado</b>${esc(new Intl.DateTimeFormat('es-ES',{dateStyle:'medium',timeStyle:'short',timeZone:'Europe/Madrid'}).format(new Date(h.ultima_modificacion_detectada)))}</span>`:''}</div><div class="source"><span>Fuente oficial para ampliar o verificar</span><strong>${esc(x.source)}</strong>${x.sourceUrl?`<a href="${esc(x.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(x.sourceLabel||'Abrir fuente oficial ↗')}</a>`:''}</div>`;
  $('#modal').dataset.itemKey=itemKey(x);$('#modal').hidden=false;document.body.classList.add('locked');$('#modal .close').focus();
};
function wire(){document.querySelectorAll('#cards .card').forEach(c=>{const id=c.dataset.id,matches=api.getItems().filter(x=>String(x.id)===String(id));if(matches.length!==1&&!c.dataset.type)return;const type=c.dataset.type||(matches[0]?.type||'');c.dataset.type=type;c.dataset.key=`${type}:${id}`;c.onclick=()=>openCard(type,id);c.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openCard(type,id)}}})}
document.addEventListener('panel:data-ready',()=>requestAnimationFrame(wire));document.addEventListener('panel:ready',()=>requestAnimationFrame(wire));document.addEventListener('click',e=>{if(e.target.closest('[data-filter],[data-stat]'))requestAnimationFrame(()=>requestAnimationFrame(wire))});document.querySelector('#search')?.addEventListener('input',()=>requestAnimationFrame(()=>requestAnimationFrame(wire)));window.addEventListener('DOMContentLoaded',()=>requestAnimationFrame(wire));
})();