#!/usr/bin/env python3
"""Monitor de incidencias oficiales de servicios digitales relevantes para ciudadanía en España."""
from __future__ import annotations
import html,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
OUT=Path('data/servicios.json');HISTORY=Path('data/historico_servicios.json');UA='PanelCiudadano/1.5 (+GitHub Pages; monitor de estado)'
STATUS_SOURCES=[('GitHub','https://www.githubstatus.com/api/v2/incidents/unresolved.json','https://www.githubstatus.com/','Global'),('Cloudflare','https://www.cloudflarestatus.com/api/v2/incidents/unresolved.json','https://www.cloudflarestatus.com/','Global'),('Atlassian','https://status.atlassian.com/api/v2/incidents/unresolved.json','https://status.atlassian.com/','Global'),('DigitalOcean','https://status.digitalocean.com/api/v2/incidents/unresolved.json','https://status.digitalocean.com/','Global')]
PUBLIC_PAGES=[('Punto de Acceso General','https://sede.administracion.gob.es/','España'),('Agencia Tributaria (AEAT)','https://sede.agenciatributaria.gob.es/','España'),('Seguridad Social','https://sede.seg-social.gob.es/','España'),('DGT','https://sede.dgt.gob.es/','España'),('Ministerio de Transportes','https://sede.transportes.gob.es/','España')]
# Primer anillo territorial. Se monitoriza accesibilidad de la sede; un fallo del robot NO se publica como caída ciudadana.
AUTONOMIC_PAGES=[('Junta de Andalucía','https://juntadeandalucia.es/servicios/sede.html','Andalucía'),('Gobierno de Aragón','https://www.aragon.es/tramites','Aragón'),('Principado de Asturias','https://sede.asturias.es/','Asturias'),('Govern de les Illes Balears','https://www.caib.es/seucaib/','Illes Balears'),('Gobierno de Canarias','https://sede.gobiernodecanarias.org/sede/','Canarias'),('Gobierno de Cantabria','https://sede.cantabria.es/','Cantabria'),('Junta de Castilla y León','https://www.tramitacastillayleon.jcyl.es/','Castilla y León'),('Junta de Castilla-La Mancha','https://www.jccm.es/sede','Castilla-La Mancha'),('Generalitat Valenciana','https://sede.gva.es/','Comunitat Valenciana'),('Xunta de Galicia','https://sede.xunta.gal/','Galicia'),('Comunidad de Madrid','https://sede.comunidad.madrid/','Comunidad de Madrid'),('Región de Murcia','https://sede.carm.es/','Región de Murcia'),('Gobierno de Navarra','https://www.navarra.es/es/tramites','Navarra'),('Gobierno Vasco','https://www.euskadi.eus/sede-electronica/','País Vasco'),('Gobierno de La Rioja','https://www.larioja.org/oficina-electronica/es','La Rioja')]
STATUS_ES={'investigating':'Investigando','identified':'Identificada','monitoring':'Monitorizando'};IMPACT_ES={'none':'Sin impacto indicado','minor':'Menor','major':'Importante','critical':'Crítica'}
def get(url,accept='text/html'):
 req=urllib.request.Request(url,headers={'Accept':accept,'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'})
 with urllib.request.urlopen(req,timeout=10) as r:return r.read().decode('utf-8',errors='replace')
def get_json(url):return json.loads(get(url,'application/json'))
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def latest_update(i):
 u=i.get('incident_updates') or [];return str(u[0].get('body') or '').strip() if u else ''
def health_add(health,name,state,detail,scope=''):
 health.append({'fuente':name,'estado':state,'detalle':detail,'ambito':scope})
def add_status_api(items,health,service,api,status_page,scope):
 try:p=get_json(api);health_add(health,service,'ok','API oficial de estado respondió',scope)
 except Exception as e:health_add(health,service,'error',type(e).__name__,scope);return
 for inc in p.get('incidents',[]):
  status=str(inc.get('status') or '').lower()
  if status not in STATUS_ES:continue
  iid=str(inc.get('id') or '');items.append({'id':f'{service.lower()}-{iid}','tipo':'servicio','servicio':service,'titulo':str(inc.get('name') or f'Incidencia en {service}'),'resumen':latest_update(inc),'estado':STATUS_ES[status],'impacto':IMPACT_ES.get(str(inc.get('impact') or '').lower(),'No indicado'),'fecha':str(inc.get('created_at') or ''),'actualizado':str(inc.get('updated_at') or ''),'ambito':scope,'fuente':f'{service} Status','url':str(inc.get('shortlink') or status_page),'verificado':True})
def fetch_public(health,name,url,scope='España'):
 try:text=clean(get(url));health_add(health,name,'ok','Sede oficial accesible',scope);return text
 except Exception as e:health_add(health,name,'error',type(e).__name__,scope);return ''
def add_age_mail(items,health):
 name='Administraciones Públicas (AGE)';url='https://sede.administracionespublicas.gob.es/ayuda/';text=fetch_public(health,name,url)
 if text and 'actualmente, nuestro sistema de correo electrónico está experimentando incidencias' in text.lower():items.append({'id':'age-correo-consultas','tipo':'servicio','servicio':'Administraciones Públicas','titulo':'Incidencia en el sistema de correo de consultas de Administraciones Públicas','resumen':'La sede oficial avisa de problemas que pueden afectar a la recepción y envío de comunicaciones relacionadas con consultas.','estado':'Activa','impacto':'No indicado','fecha':'','actualizado':'','ambito':'España','fuente':'Sede de Administraciones Públicas','url':url,'verificado':True})
def add_gencat(items,health):
 name='Generalitat de Catalunya';url='https://web.gencat.cat/es/seu-electronica/informacio/avisos-i-talls-de-serveis';text=fetch_public(health,name,url,'Cataluña')
 if not text:return
 m=re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*h?)\s+(?:Desconocido|Desconegut)\s+.*?(Tramitar en línea).*?(Incidencia en formularios HTML)',text,re.I)
 if m:items.append({'id':'gencat-formularios-html-'+re.sub(r'\D','',m.group(1)),'tipo':'servicio','servicio':'Generalitat de Catalunya','titulo':'Incidencia en la tramitación en línea de la Generalitat','resumen':'La Sede electrónica informa de una incidencia en formularios HTML que afecta a la tramitación en línea.','estado':'Activa','impacto':'Tramitación electrónica','fecha':m.group(1),'actualizado':'','ambito':'Cataluña','fuente':'Sede electrónica de la Generalitat de Catalunya','url':url,'verificado':True})
def add_enaire(items,health):
 name='ENAIRE Sede electrónica';url='https://servicios-enaire.sede.gob.es/';text=fetch_public(health,name,url);low=text.lower()
 if text and 'sede electrónica en mantenimiento' in low and 'labores de mantenimiento' in low:items.append({'id':'enaire-sede-mantenimiento','tipo':'servicio','servicio':'ENAIRE','titulo':'Sede electrónica de ENAIRE en mantenimiento','resumen':'La propia sede electrónica informa de labores de mantenimiento y de indisponibilidad temporal.','estado':'Mantenimiento','impacto':'Tramitación electrónica','fecha':'','actualizado':'','ambito':'España','fuente':'Sede electrónica de ENAIRE','url':url,'verificado':True})
def add_sepe(items,health):
 name='SEPE';url='https://sede.sepe.gob.es/';text=fetch_public(health,name,url);low=text.lower()
 if text and 'aviso de mantenimiento' in low and ('se producirá un corte' in low or 'servicio no disponible temporalmente' in low):items.append({'id':'sepe-aviso-mantenimiento','tipo':'servicio','servicio':'SEPE','titulo':'Aviso de mantenimiento en la Sede electrónica del SEPE','resumen':'La portada oficial de la Sede del SEPE muestra un aviso de mantenimiento que puede afectar temporalmente a sus servicios.','estado':'Mantenimiento','impacto':'Tramitación electrónica','fecha':'','actualizado':'','ambito':'España','fuente':'Sede electrónica del SEPE','url':url,'verificado':True})
def add_public_health(health):
 for name,url,scope in PUBLIC_PAGES:fetch_public(health,name,url,scope)
def add_autonomic_health(health):
 for name,url,scope in AUTONOMIC_PAGES:fetch_public(health,name,url,scope)
def load(path,default):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except Exception:return default
def fingerprint(x):return '|'.join(str(x.get(k,'')).strip() for k in ('titulo','resumen','estado','impacto','actualizado'))
def update_history(items,complete,now):
 old=load(HISTORY,{'items':[]});records={x.get('id'):x for x in old.get('items',[]) if x.get('id')};current={x['id']:x for x in items}
 for iid,x in current.items():
  if iid not in records:records[iid]={**x,'primera_deteccion':now,'ultima_deteccion':now,'ultima_modificacion_detectada':now,'resuelto_detectado':'','estado_historico':'activo','fingerprint':fingerprint(x)}
  else:
   r=records[iid];fp=fingerprint(x)
   if r.get('fingerprint')!=fp:r['ultima_modificacion_detectada']=now
   r.update(x);r.update({'ultima_deteccion':now,'resuelto_detectado':'','estado_historico':'activo','fingerprint':fp})
 if complete:
  for iid,r in records.items():
   if iid not in current and r.get('estado_historico')=='activo':r['estado_historico']='resuelto';r['resuelto_detectado']=now
 history={'ultima_revision':now,'nota':'resuelto_detectado indica cuándo Panel Ciudadano dejó de detectar la incidencia; no necesariamente la hora exacta de resolución.','total':len(records),'items':sorted(records.values(),key=lambda x:x.get('primera_deteccion',''),reverse=True)[:500]};HISTORY.parent.mkdir(parents=True,exist_ok=True);tmp=HISTORY.with_suffix('.tmp');tmp.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(HISTORY)
def main():
 now=datetime.now(timezone.utc).isoformat();items=[];health=[]
 for row in STATUS_SOURCES:add_status_api(items,health,*row)
 add_age_mail(items,health);add_gencat(items,health);add_enaire(items,health);add_sepe(items,health);add_public_health(health);add_autonomic_health(health)
 items=list({x['id']:x for x in items}.values());ok=[x['fuente'] for x in health if x['estado']=='ok'];errors=[{'servicio':x['fuente'],'error':x['detalle']} for x in health if x['estado']=='error'];complete=not errors
 if not ok:print('REVISIÓN INCOMPLETA: ninguna fuente oficial respondió; se conservan los datos anteriores.');return
 previous=load(OUT,{});previous_ids={x.get('id') for x in previous.get('items',[])};current_ids={x['id'] for x in items}
 territorial={};
 for h in health:
  scope=h.get('ambito') or 'Sin ámbito';territorial.setdefault(scope,{'configuradas':0,'respondieron':0});territorial[scope]['configuradas']+=1;territorial[scope]['respondieron']+=h['estado']=='ok'
 result={'ultima_revision':now,'revision':'completa' if complete else 'parcial','cobertura':{'fuentes_configuradas':len(health),'fuentes_respondieron':len(ok),'territorial':territorial},'salud_fuentes':health,'fuentes_ok':ok,'fuentes_error':errors,'cambios':{'nuevas':len(current_ids-previous_ids),'desaparecidas_detectadas':len(previous_ids-current_ids) if complete else 0},'total':len(items),'items':items};OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);update_history(items,complete,now);print(f"Servicios: {len(items)} activas; fuentes {len(ok)}/{len(health)}; errores {len(errors)}")
if __name__=='__main__':main()
