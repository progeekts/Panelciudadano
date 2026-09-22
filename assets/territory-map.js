/* Mapa provincial interactivo de España. Sin lista separada: cada territorio es el control. */
(()=> {
const rows=[
[['A Coruña',0],['Lugo',1],['Asturias',2],['Cantabria',3],['Bizkaia',4],['Gipuzkoa',5],['Navarra',6],['Huesca',7],['Lleida',8],['Girona',9]],
[['Pontevedra',0],['Ourense',1],['León',2],['Palencia',3],['Burgos',4],['La Rioja',5],['Zaragoza',6],['Tarragona',8],['Barcelona',9]],
[['Zamora',2],['Valladolid',3],['Soria',4],['Segovia',3.6],['Guadalajara',4.8],['Teruel',6],['Castellón',7]],
[['Salamanca',2],['Ávila',3],['Madrid',4],['Cuenca',5],['Valencia',6.5]],
[['Cáceres',1.6],['Toledo',3.3],['Ciudad Real',4],['Albacete',5.2],['Alicante',6.4]],
[['Badajoz',1.4],['Córdoba',3],['Jaén',4],['Murcia',5.5]],
[['Huelva',1.5],['Sevilla',2.5],['Málaga',3.5],['Granada',4.5],['Almería',5.5],['Cádiz',2.7]]
];
const aliases={'Bizkaia':'Vizcaya','Gipuzkoa':'Guipúzcoa','A Coruña':'Coruña','Castellón':'Castello','Valencia':'València','Alicante':'Alacant'};
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
let selected='';
function national(s){s=norm(s);return !s||/espana|nacional|estatal|global|todo el territorio/.test(s)}
function polygon(cx,cy,w=55,h=46){return [[cx-w/2,cy-h/2],[cx+w*.28,cy-h/2-5],[cx+w/2,cy-h*.08],[cx+w*.38,cy+h/2],[cx-w*.3,cy+h/2+4],[cx-w/2,cy+h*.08]].map(p=>p.join(',')).join(' ')}
function paint(){
 const svg=document.getElementById('provinceMap'); if(!svg)return;
 let out='<g class="map-mainland">';
 rows.forEach((row,ri)=>row.forEach(([name,col])=>{const x=72+col*51,y=66+ri*48;out+=`<g class="province-region" data-province="${name}" tabindex="0" role="button" aria-label="Filtrar por ${name}"><polygon points="${polygon(x,y)}"/><title>${name}</title></g>`}));
 out+='</g><g class="islands"><g class="province-region island" data-province="Illes Balears" tabindex="0" role="button"><ellipse cx="565" cy="250" rx="24" ry="13"/><title>Illes Balears</title></g><g class="province-region island" data-province="Las Palmas" tabindex="0" role="button"><ellipse cx="112" cy="425" rx="28" ry="13"/><title>Las Palmas</title></g><g class="province-region island" data-province="Santa Cruz de Tenerife" tabindex="0" role="button"><ellipse cx="48" cy="410" rx="28" ry="13"/><title>Santa Cruz de Tenerife</title></g></g>';
 svg.innerHTML=out;
 svg.querySelectorAll('[data-province]').forEach(el=>{el.onclick=()=>set(el.dataset.province);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();set(el.dataset.province)}}});
}
function set(name){selected=selected===name?'':name;localStorage.setItem('panel-territory',selected);ui();filter()}
function ui(){const l=document.getElementById('territoryLabel'),a=document.getElementById('territoryActive'),c=document.getElementById('clearTerritory');if(l)l.textContent=selected||'Toda España';if(a)a.textContent=selected?`Provincia: ${selected}`:'Cobertura nacional';if(c)c.hidden=!selected;document.querySelectorAll('[data-province]').forEach(el=>el.classList.toggle('active',el.dataset.province===selected))}
function match(scope){if(!selected)return true;if(national(scope))return true;const s=norm(scope), names=[selected,aliases[selected]].filter(Boolean).map(norm);return names.some(n=>s.includes(n))}
function filter(){const api=window.PanelCiudadano;if(!api)return;const items=api.getItems?.()||[];document.querySelectorAll('.card').forEach(card=>{const item=items.find(x=>String(x.id)===String(card.dataset.id));card.hidden=!match(item?.scope||'')});const n=[...document.querySelectorAll('.card')].filter(c=>!c.hidden).length,count=document.getElementById('resultCount');if(count&&selected)count.textContent=`${n} visibles para ${selected}, incluidos avisos nacionales`}
document.addEventListener('panel:data-ready',()=>setTimeout(filter,0));
window.addEventListener('DOMContentLoaded',()=>{selected=localStorage.getItem('panel-territory')||'';paint();ui();document.getElementById('clearTerritory')?.addEventListener('click',()=>set(selected));document.getElementById('territoryButton')?.addEventListener('click',()=>document.getElementById('spainFilter')?.scrollIntoView({behavior:'smooth',block:'center'}))});
})();