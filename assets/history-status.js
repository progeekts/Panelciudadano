/* Corrige la semántica temporal del histórico: el estado más reciente manda. */
(()=>{
const baseRenderHistory=renderHistory;
renderHistory=function(){
 baseRenderHistory();
 if(!D.history.length)return;
 const events=[];
 D.history.forEach(x=>{
  const state=x.estado_historico||'activo';
  const terminalTime=state==='resuelto'?x.resuelto_detectado:state==='retirado'?x.retirado_detectado:'';
  // Si ya existe un evento terminal reciente, no repetimos la misma incidencia como "Nuevo".
  if(!terminalTime&&recent(x.primera_deteccion,48))events.push({kind:'Nuevo',time:x.primera_deteccion,x});
  if(!terminalTime&&x.ultima_modificacion_detectada!==x.primera_deteccion&&recent(x.ultima_modificacion_detectada,48))events.push({kind:'Actualizado',time:x.ultima_modificacion_detectada,x});
  if(state==='resuelto'&&x.resuelto_detectado&&recent(x.resuelto_detectado,72))events.push({kind:'Solucionado',time:x.resuelto_detectado,x});
  if(state==='retirado'&&x.retirado_detectado&&recent(x.retirado_detectado,72))events.push({kind:'Retirado del monitor',time:x.retirado_detectado,x});
 });
 events.sort((a,b)=>parseDate(b.time)-parseDate(a.time));
 $('#recentHistory').innerHTML=events.slice(0,6).map(e=>`<div class="timeline-row"><span class="event ${e.kind==='Solucionado'?'resolved':e.kind==='Nuevo'?'new':e.kind.startsWith('Retirado')?'changed':'changed'}">${esc(e.kind)}</span><div><strong>${esc(e.x.servicio||'Servicio')} · ${esc(e.x.titulo)}</strong><small>${esc(niceDate(e.time))}${e.kind.startsWith('Retirado')&&e.x.motivo_retirada?' · '+esc(e.x.motivo_retirada):''}</small></div></div>`).join('')||'<p class="health-note">Sin cambios relevantes detectados en las últimas 48 horas.</p>';
 $('#historyList').innerHTML=D.history.slice().sort((a,b)=>parseDate(b.primera_deteccion)-parseDate(a.primera_deteccion)).slice(0,50).map(x=>{const state=x.estado_historico||'activo',label=state==='resuelto'?'Solucionado':state==='retirado'?'Retirado del monitor':'Activo',when=state==='resuelto'&&x.resuelto_detectado?' · dejó de detectarse: '+esc(niceDate(x.resuelto_detectado)):state==='retirado'&&x.retirado_detectado?' · retirado: '+esc(niceDate(x.retirado_detectado)):'';return `<div class="history-row"><div><strong>${esc(x.servicio||'Servicio')}</strong><span>${esc(x.titulo)}</span></div><span class="event ${state==='resuelto'?'resolved':state==='retirado'?'changed':'active'}">${label}</span><small>Detectado: ${esc(niceDate(x.primera_deteccion))}${when}</small></div>`}).join('');
 };
 // app.js ya pudo pintar antes de cargar esta extensión; repintamos cuando el histórico esté disponible.
 const retry=()=>{if(D.history.length)renderHistory();else setTimeout(retry,250)};setTimeout(retry,250);
})();
