#!/usr/bin/env python3
"""Radar de incidencias oficiales de servicios públicos relevantes para ciudadanía en España."""
from __future__ import annotations
import html,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
OUT=Path('data/servicios.json');HISTORY=Path('data/historico_servicios.json');UA='PanelCiudadano/2.0 (+GitHub Pages; monitor ciudadano)'
DEPRECATED_DETECTORS={'enaire-sede-mantenimiento':'Retirado del monitor porque la señal disponible no aporta una vigencia temporal suficientemente fiable.'}
# Detectores: fuentes con señal explícita de incidencia/mantenimiento. Cobertura: comprobaciones auxiliares de disponibilidad.
PUBLIC_PAGES=[('pag','Punto de Acceso General','https://sede.administracion.gob.es/','España'),('aeat','Agencia Tributaria (AEAT)','https://sede.agenciatributaria.gob.es/','España'),('seg-social','Seguridad Social','https://sede.seg-social.gob.es/','España'),('dgt','DGT','https://sede.dgt.gob.es/','España'),('transportes','Ministerio de Transportes','https://sede.transportes.gob.es/','España')]
AUTONOMIC_PAGES=[('andalucia','Junta de Andalucía','https://juntadeandalucia.es/servicios/sede.html','Andalucía'),('aragon','Gobierno de Aragón','https://www.aragon.es/tramites','Aragón'),('asturias','Principado de Asturias','https://sede.asturias.es/','Asturias'),('balears','Govern de les Illes Balears','https://www.caib.es/seucaib/','Illes Balears'),('canarias','Gobierno de Canarias','https://sede.gobiernodecanarias.org/sede/','Canarias'),('cantabria','Gobierno de Cantabria','https://sede.cantabria.es/','Cantabria'),('castilla-leon','Junta de Castilla y León','https://www.tramitacastillayleon.jcyl.es/','Castilla y León'),('castilla-mancha','Junta de Castilla-La Mancha','https://www.jccm.es/sede','Castilla-La Mancha'),('gva','Generalitat Valenciana','https://sede.gva.es/','Comunitat Valenciana'),('galicia','Xunta de Galicia','https://sede.xunta.gal/','Galicia'),('madrid','Comunidad de Madrid','https://sede.comunidad.madrid/','Comunidad de Madrid'),('murcia','Región de Murcia','https://sede.carm.es/','Región de Murcia'),('navarra','Gobierno de Navarra','https://www.navarra.es/es/tramites','Navarra'),('euskadi','Gobierno Vasco','https://www.euskadi.eus/sede-electronica/','País Vasco'),('rioja','Gobierno de La Rioja','https://web.larioja.org/sede-electronica','La Rioja'),('ceuta','Ciudad Autónoma de Ceuta','https://sede.ceuta.es/','Ceuta'),('melilla','Ciudad Autónoma de Melilla','https://sede.melilla.es/','Melilla')]
def get(url):
 req=urllib.request.Request(url,headers={'Accept':'text/html,application/xhtml+xml','User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'});return urllib.request.urlopen(req,timeout=12).read().decode('utf-8',errors='replace')
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def health_add(h,k,n,s,d,scope='',kind='cobertura'):h.append({'clave':k,'fuente':n,'estado':s,'detalle':d,'ambito':scope,'tipo':kind,'critica_para_resolucion':kind=='detector'})
def fetch_public(h,key,name,url,scope='España',kind='cobertura'):
 try:t=clean(get(url));health_add(h,key,name,'ok','Fuente oficial accesible',scope,kind);return t
 except Exception as e:health_add(h,key,name,'error',type(e).__name__,scope,kind);return ''
def incident(items,key,service,title,summary,state,impact,scope,source,url,date=''):
 items.append({'id':key,'fuente_clave':key.split('-')[0],'tipo':'servicio','servicio':service,'titulo':title,'resumen':summary,'estado':state,'impacto':impact,'fecha':date,'actualizado':'','ambito':scope,'fuente':source,'url':url,'verificado':True})
def add_age(items,h):
 url='https://sede.administracionespublicas.gob.es/ayuda/';t=fetch_public(h,'age','Administraciones Públicas (AGE)',url,'España','detector');low=t.lower()
 if t and 'actualmente, nuestro sistema de correo electrónico está experimentando incidencias' in low:incident(items,'age-correo-consultas','Administraciones Públicas','Incidencia en el sistema de correo de consultas','La sede oficial comunica problemas en su sistema de correo electrónico de consultas.','Activa','Consultas y comunicaciones','España','Sede de Administraciones Públicas',url)
def add_gencat(items,h):
 url='https://web.gencat.cat/es/seu-electronica/informacio/avisos-i-talls-de-serveis';t=fetch_public(h,'gencat','Generalitat de Catalunya',url,'Cataluña','detector')
 if not t:return
 m=re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*h?).*?(Tramitar en línea).*?(Incidencia en formularios HTML)',t,re.I)
 if m:incident(items,'gencat-formularios-html-'+re.sub(r'\D','',m.group(1)),'Generalitat de Catalunya','Incidencia en la tramitación en línea','La sede electrónica comunica una incidencia en formularios HTML que afecta a la tramitación en línea.','Activa','Tramitación electrónica','Cataluña','Sede electrónica de la Generalitat de Catalunya',url,m.group(1))
def add_sepe(items,h):
 url='https://sede.sepe.gob.es/portalSede';t=fetch_public(h,'sepe','SEPE',url,'España','detector');low=t.lower()
 if t and ('aviso de mantenimiento' in low or 'mantenimiento' in low) and ('se producirá un corte' in low or 'servicio no disponible temporalmente' in low or 'cortes en la disponibilidad' in low):incident(items,'sepe-aviso-mantenimiento','SEPE','Aviso de mantenimiento en la Sede electrónica del SEPE','La portada oficial del SEPE comunica un mantenimiento que puede afectar temporalmente a la tramitación.','Mantenimiento','Tramitación electrónica','España','Sede electrónica del SEPE',url)
def add_melilla(items,h):
 url='https://sede.melilla.es/';t=fetch_public(h,'melilla','Ciudad Autónoma de Melilla',url,'Melilla','detector');low=t.lower();today=datetime.now(timezone.utc).strftime('%d/%m/%Y')
 if t and today in t and ('labores de mantenimiento' in low or 'interrupción' in low) and ('cortes' in low or 'no disponible' in low):incident(items,'melilla-aviso-servicio-'+datetime.now(timezone.utc).strftime('%Y%m%d'),'Ciudad Autónoma de Melilla','Aviso de mantenimiento en la Sede electrónica de Melilla','La sede oficial comunica mantenimiento o cortes vigentes del servicio.','Mantenimiento','Tramitación electrónica','Melilla','Sede electrónica de Melilla',url,today)
def add_coverage(h):
 for k,n,u,s in PUBLIC_PAGES:fetch_public(h,k,n,u,s,'cobertura')
 for k,n,u,s in AUTONOMIC_PAGES:
  if k!='melilla':fetch_public(h,k,n,u,s,'cobertura')
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return d
def fingerprint(x):return '|'.join(str(x.get(k,'')).strip() for k in ('titulo','resumen','estado','impacto','actualizado'))
def infer_source_key(x):
 if x.get('fuente_clave'):return x['fuente_clave']
 iid=str(x.get('id') or '')
 for prefix,key in [('age-','age'),('gencat-','gencat'),('sepe-','sepe'),('melilla-','melilla')]:
  if iid.startswith(prefix):return key
 return ''
def update_history(items,healthy,now):
 old=load(HISTORY,{'items':[]});records={x.get('id'):x for x in old.get('items',[]) if x.get('id')};current={x['id']:x for x in items};resolved=retired=0
 records={iid:r for iid,r in records.items() if not str(iid).startswith(('github-','cloudflare-','atlassian-','digitalocean-'))}
 for iid,x in current.items():
  if iid not in records:records[iid]={**x,'primera_deteccion':now,'ultima_deteccion':now,'ultima_modificacion_detectada':now,'resuelto_detectado':'','estado_historico':'activo','fingerprint':fingerprint(x)}
  else:
   r=records[iid];fp=fingerprint(x)
   if r.get('fingerprint')!=fp:r['ultima_modificacion_detectada']=now
   r.update(x);r.update({'ultima_deteccion':now,'resuelto_detectado':'','estado_historico':'activo','fingerprint':fp})
 for iid,r in records.items():
  if iid in current or r.get('estado_historico')!='activo':continue
  if iid in DEPRECATED_DETECTORS:r['estado_historico']='retirado';r['retirado_detectado']=now;r['motivo_retirada']=DEPRECATED_DETECTORS[iid];r['resuelto_detectado']='';retired+=1;continue
  key=infer_source_key(r)
  if key and key in healthy:r['estado_historico']='resuelto';r['resuelto_detectado']=now;resolved+=1
 history={'ultima_revision':now,'nota':'Resuelto solo se registra cuando el detector oficial correspondiente respondió correctamente y dejó de publicar la incidencia. Un error técnico de consulta nunca se presenta como caída del servicio.','total':len(records),'items':sorted(records.values(),key=lambda x:x.get('primera_deteccion',''),reverse=True)[:500]};HISTORY.parent.mkdir(parents=True,exist_ok=True);tmp=HISTORY.with_suffix('.tmp');tmp.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(HISTORY);return resolved,retired
def main():
 now=datetime.now(timezone.utc).isoformat();items=[];health=[];add_age(items,health);add_gencat(items,health);add_sepe(items,health);add_melilla(items,health);add_coverage(health);items=list({x['id']:x for x in items}.values())
 detectors=[x for x in health if x['tipo']=='detector'];coverage=[x for x in health if x['tipo']=='cobertura'];det_ok=[x for x in detectors if x['estado']=='ok'];cov_ok=[x for x in coverage if x['estado']=='ok'];healthy={x['clave'] for x in det_ok}
 if not healthy:print('REVISIÓN INCOMPLETA: ningún detector de incidencias respondió; se conservan los datos anteriores.');return
 previous=load(OUT,{});previous_ids={x.get('id') for x in previous.get('items',[]) if str(x.get('ambito') or '')!='Global'};current_ids={x['id'] for x in items};territorial={}
 for x in health:
  scope=x.get('ambito') or 'Sin ámbito';territorial.setdefault(scope,{'configuradas':0,'respondieron':0});territorial[scope]['configuradas']+=1;territorial[scope]['respondieron']+=x['estado']=='ok'
 resolved,retired=update_history(items,healthy,now);errors=[{'servicio':x['fuente'],'error':x['detalle'],'tipo':x['tipo'],'ambito':x['ambito']} for x in health if x['estado']=='error']
 result={'ultima_revision':now,'revision':'completa' if len(det_ok)==len(detectors) else 'parcial','revision_fuentes_incidentes':'completa' if len(det_ok)==len(detectors) else 'parcial','salud_auxiliar':'completa' if len(cov_ok)==len(coverage) else 'parcial','cobertura':{'detectores_configurados':len(detectors),'detectores_respondieron':len(det_ok),'comprobaciones_cobertura':len(coverage),'comprobaciones_respondieron':len(cov_ok),'fuentes_configuradas':len(health),'fuentes_respondieron':len(det_ok)+len(cov_ok),'fuentes_incidentes':len(detectors),'fuentes_incidentes_ok':len(det_ok),'territorial':territorial},'salud_fuentes':health,'fuentes_error':errors,'cambios':{'nuevas':len(current_ids-previous_ids),'resueltas_detectadas':resolved,'retiradas_monitor':retired},'total':len(items),'items':items};OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);print(f'Servicios: {len(items)} activas; detectores {len(det_ok)}/{len(detectors)}; cobertura {len(cov_ok)}/{len(coverage)}; resueltas {resolved}')
if __name__=='__main__':main()
