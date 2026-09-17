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
  $('#modalContent').innerHTML=`<div class="meta"><span class="pill ${x.type}">${types[x.type]?.name}</span><span class="pill state ${statusClass(x.status)}">${esc(x.status)}</span></div><h2>${esc(x.title)}</h2><p>${esc(x.summary)}</p>${x.detail?`<div class="detail">${esc(x.detail).replace(/\n/g,'<br>')}</div>`:''}<div class="facts"><span><b>Ámbito</b>${esc(x.scope||'No indicado')}</span><span><b>Fecha</b>${esc(x.date||'No indicada')}</span><span><b>Nivel / referencia</b>${esc(x.level||'Fuente oficial')}</span></div><div class="source"><span>Fuente oficial</span><strong>${esc(x.source)}</strong>${x.sourceUrl?`<a href="${esc(x.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(x.sourceLabel||'Abrir fuente oficial ↗')}</a>`:''}</div>`;
  $('#modal').dataset.itemKey=itemKey(x);$('#modal').hidden=false;document.body.classList.add('locked');$('#modal .close').focus();
};
function wire(){document.querySelectorAll('#cards .card').forEach(c=>{const id=c.dataset.id,matches=api.getItems().filter(x=>String(x.id)===String(id));if(matches.length!==1&&!c.dataset.type)return;const type=c.dataset.type||(matches[0]?.type||'');c.dataset.type=type;c.dataset.key=`${type}:${id}`;c.onclick=()=>openCard(type,id);c.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openCard(type,id)}}})}
document.addEventListener('panel:data-ready',()=>requestAnimationFrame(wire));document.addEventListener('panel:ready',()=>requestAnimationFrame(wire));document.addEventListener('click',e=>{if(e.target.closest('[data-filter],[data-stat]'))requestAnimationFrame(()=>requestAnimationFrame(wire))});document.querySelector('#search')?.addEventListener('input',()=>requestAnimationFrame(()=>requestAnimationFrame(wire)));window.addEventListener('DOMContentLoaded',()=>requestAnimationFrame(wire));
})();