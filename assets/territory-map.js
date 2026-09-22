/* Filtro territorial visual por provincia. Mantiene visibles avisos nacionales. */
(()=> {
  const provinces=[
    ['A Coruña',105,82],['Lugo',143,76],['Asturias',176,66],['Cantabria',211,69],['Bizkaia',248,68],['Gipuzkoa',276,72],['Navarra',300,90],['Huesca',336,102],['Girona',403,106],
    ['Pontevedra',94,111],['Ourense',130,116],['León',178,103],['Palencia',205,113],['Burgos',238,111],['La Rioja',270,112],['Zaragoza',319,129],['Lleida',370,126],['Barcelona',405,137],
    ['Zamora',174,139],['Valladolid',209,142],['Soria',261,139],['Tarragona',374,158],['Salamanca',177,170],['Ávila',213,174],['Segovia',235,160],['Madrid',246,188],['Guadalajara',277,175],['Teruel',319,174],['Castellón',344,194],
    ['Cáceres',174,207],['Toledo',229,213],['Cuenca',278,209],['Valencia',333,222],['Badajoz',169,242],['Ciudad Real',236,244],['Albacete',280,248],['Alicante',317,267],
    ['Huelva',183,281],['Sevilla',213,278],['Córdoba',243,269],['Jaén',273,278],['Murcia',302,291],['Cádiz',215,309],['Málaga',252,306],['Granada',281,301],['Almería',318,307]
  ];
  const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  let selected='';
  function isNational(scope){const s=normalize(scope);return !s||/espana|nacional|estatal|global|todo el territorio/.test(s)}
  function paint(){
    const list=document.getElementById('provinceList'), dots=document.getElementById('provinceDots');
    if(!list||!dots)return;
    list.innerHTML=provinces.map(([n])=>`<button type="button" data-province="${n}">${n}</button>`).join('');
    dots.innerHTML=provinces.map(([n,x,y])=>`<circle class="province-dot" data-province="${n}" cx="${x}" cy="${y}" r="7"><title>${n}</title></circle>`).join('');
    [...document.querySelectorAll('[data-province]')].forEach(el=>el.addEventListener('click',()=>setProvince(el.dataset.province)));
  }
  function setProvince(name){
    selected=selected===name?'':name;
    localStorage.setItem('panel-territory',selected);
    updateUI();
    filterCards();
  }
  function updateUI(){
    const label=document.getElementById('territoryLabel'), active=document.getElementById('territoryActive'), clear=document.getElementById('clearTerritory');
    if(label)label.textContent=selected||'Toda España';
    if(active)active.textContent=selected?`Filtrando por ${selected}`:'Cobertura nacional';
    if(clear)clear.hidden=!selected;
    document.querySelectorAll('[data-province]').forEach(el=>el.classList.toggle('active',el.dataset.province===selected));
  }
  function filterCards(){
    const api=window.PanelCiudadano;
    if(!api)return;
    const cards=[...document.querySelectorAll('.card')];
    cards.forEach(card=>{
      if(!selected){card.hidden=false;return}
      const id=card.dataset.id;
      const item=(api.getItems?.()||[]).find(x=>String(x.id)===String(id));
      const scope=item?.scope||'';
      card.hidden=!(isNational(scope)||normalize(scope).includes(normalize(selected)));
    });
    const visible=cards.filter(c=>!c.hidden).length;
    const count=document.getElementById('resultCount');
    if(count&&selected)count.textContent=`${visible} visibles para ${selected} (más avisos nacionales)`;
  }
  document.addEventListener('panel:data-ready',()=>setTimeout(filterCards,0));
  window.addEventListener('DOMContentLoaded',()=>{
    selected=localStorage.getItem('panel-territory')||'';
    paint();updateUI();
    document.getElementById('clearTerritory')?.addEventListener('click',()=>setProvince(selected));
    document.getElementById('territoryButton')?.addEventListener('click',()=>document.getElementById('spainFilter')?.scrollIntoView({behavior:'smooth',block:'center'}));
  });
})();