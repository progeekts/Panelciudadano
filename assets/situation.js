/* Pulso ciudadano: síntesis descriptiva de los datos cargados. No sustituye a las fuentes oficiales. */
(function(){
 function apiItems(){try{return window.PanelCiudadano?.getItems?.()||[]}catch(e){return[]}}
 function count(items,type,pred=()=>true){return items.filter(x=>x.type===type&&pred(x)).length}
 function build(){
  const items=apiItems();if(!items.length)return null;
  const red=count(items,'meteo',x=>String(x.level||'').toLowerCase()==='rojo');
  const orange=count(items,'meteo',x=>String(x.level||'').toLowerCase()==='naranja');
  const services=count(items,'servicios');
  const scams=count(items,'estafas',x=>x.sortDate>Date.now()-7*86400000);
  const openAid=count(items,'ayudas',x=>x.status==='Abierta');
  let state='Situación general sin avisos de máxima prioridad';let tone='ok';
  if(red){state='Hay avisos meteorológicos de nivel rojo';tone='high'}
  else if(orange||services){state='Hay avisos que pueden requerir atención';tone='attention'}
  const facts=[];
  if(red)facts.push(`${red} aviso${red===1?'':'s'} meteorológico${red===1?'':'s'} rojo${red===1?'':'s'}`);
  if(orange)facts.push(`${orange} aviso${orange===1?'':'s'} meteorológico${orange===1?'':'s'} naranja${orange===1?'':'s'}`);
  if(services)facts.push(`${services} incidencia${services===1?'':'s'} digital${services===1?'':'es'} confirmada${services===1?'':'s'}`);
  if(scams)facts.push(`${scams} aviso${scams===1?'':'s'} de fraude reciente${scams===1?'':'s'}`);
  if(openAid)facts.push(`${openAid} ayuda${openAid===1?'':'s'} con plazo abierto verificado`);
  if(!facts.length)facts.push('Sin elementos destacados entre los módulos cargados');
  return{state,tone,facts:facts.slice(0,4)}
 }
 function render(){const host=document.querySelector('#citizenPulse');if(!host)return;const s=build();if(!s){host.hidden=true;return}host.hidden=false;host.className='citizen-pulse '+s.tone;host.innerHTML=`<div class="pulse-kicker">PULSO CIUDADANO</div><div class="pulse-main"><div><strong>${s.state}</strong><p>${s.facts.join(' · ')}</p></div><span class="pulse-note">Síntesis de Panel Ciudadano</span></div><small>Se genera a partir de estados y niveles publicados por las fuentes. No sustituye sus avisos oficiales.</small>`}
 document.addEventListener('panel:data-ready',render);window.addEventListener('load',()=>setTimeout(render,1600));
})();
