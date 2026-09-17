/* Capa de relevancia: ordena el escaparate sin alterar los datos oficiales. */
(()=>{
const n=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function ageHours(x){const t=Number(x.sortDate||0);return t?Math.max(0,(Date.now()-t)/36e5):9999}
function score(x){let s=(x.priority||0)*20;const age=ageHours(x),txt=n([x.status,x.level,x.title,x.summary].join(' '));
 if(x.type==='meteo'){if(/rojo/.test(txt))s+=90;else if(/naranja/.test(txt))s+=65;else if(/amarillo/.test(txt))s+=30;if(age<12)s+=18;else if(age<36)s+=9}
 if(x.type==='servicios'){s+=55;if(/major|critical|critico|grave|caida|interrupcion/.test(txt))s+=20;if(age<12)s+=16}
 if(x.type==='estafas'){s+=38;if(age<24*7)s+=18;else if(age<24*30)s+=8}
 if(x.type==='alimentacion'){s+=34;if(/alerg|intoler/.test(txt))s+=9;if(age<24*14)s+=14}
 if(x.type==='salud'){s+=35;if(age<24*14)s+=14}
 if(x.type==='ayudas'){if(/abierta/.test(txt))s+=28;if(/proxima/.test(txt))s+=18;if(age<24*14)s+=7}
 return s}
function diverse(a){const sorted=[...a].sort((x,y)=>score(y)-score(x)||(y.sortDate||0)-(x.sortDate||0)),out=[],used=new Map();for(const x of sorted){const c=used.get(x.type)||0;if(c<2){out.push(x);used.set(x.type,c+1)}}for(const x of sorted)if(!out.includes(x))out.push(x);return out}
ranked=function(a){return diverse(a)};
function reason(x){const txt=n([x.status,x.level,x.title,x.summary].join(' ')),age=ageHours(x);if(x.type==='meteo'&&/rojo/.test(txt))return'Aviso meteorológico rojo';if(x.type==='meteo'&&/naranja/.test(txt))return'Aviso meteorológico naranja';if(x.type==='servicios')return'Incidencia confirmada';if(x.type==='estafas'&&age<24*30)return'Alerta de fraude reciente';if(x.type==='alimentacion'&&age<24*14)return'Alerta alimentaria reciente';if(x.type==='salud'&&age<24*14)return'Aviso sanitario reciente';if(x.type==='ayudas'&&/abierta/.test(txt))return'Plazo de solicitud abierto';return'Relevancia y actualidad'}
const oldRender=render;
render=function(){oldRender();const q=$('#search').value.trim();if(active!=='todos'||q)return;const cards=[...document.querySelectorAll('#cards .card')];cards.slice(0,4).forEach((c,i)=>{c.classList.add('top-relevance');const item=D.items.find(x=>String(x.id)===String(c.dataset.id));if(item)c.insertAdjacentHTML('afterbegin',`<span class="relevance-mark" title="Criterio de Panel Ciudadano; no es una calificación de la fuente oficial">${i===0?'Prioridad informativa · ':''}${reason(item)}</span>`)})};
window.PanelRelevance={score,reason};
})();