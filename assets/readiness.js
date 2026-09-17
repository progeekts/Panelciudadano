/* Capa de coordinación: seis módulos, una fecha real y una señal estable de preparación. */
(()=>{
const expected=['ayudas','estafas','servicios','alimentacion','salud','meteo'];
const loaded=new Map();
let timer=null,completeSent=false;
function typeOf(h){const n=(h?.name||'').toLowerCase();if(n.includes('ayuda'))return'ayudas';if(n.includes('fraud'))return'estafas';if(n.includes('servicio'))return'servicios';if(n.includes('aliment'))return'alimentacion';if(n.includes('salud'))return'salud';if(n.includes('meteor')||n.includes('aemet'))return'meteo';return''}
function validDate(v){const t=Date.parse(v);return Number.isFinite(t)?t:0}
function reconcile(){const api=window.PanelCiudadano;if(!api)return;const health=api.getHealth?.()||[];health.forEach(h=>{const k=typeOf(h);if(k)loaded.set(k,{status:h.status,review:h.review||''})});const reviews=[...loaded.values()].map(x=>x.review).filter(Boolean).sort((a,b)=>validDate(b)-validDate(a));if(reviews.length){const el=document.getElementById('lastUpdate');if(el)el.textContent=niceDate(reviews[0])}const ready=expected.filter(k=>loaded.has(k));const detail={expected:[...expected],ready,status:Object.fromEntries(loaded),complete:ready.length===expected.length,latestReview:reviews[0]||''};window.PanelReadiness=detail;document.dispatchEvent(new CustomEvent('panel:readiness',{detail}));if(detail.complete&&!completeSent){completeSent=true;document.dispatchEvent(new CustomEvent('panel:ready',{detail}))}}
function schedule(){clearTimeout(timer);timer=setTimeout(reconcile,40)}
document.addEventListener('panel:data-ready',schedule);window.addEventListener('DOMContentLoaded',schedule);setTimeout(schedule,800);
})();