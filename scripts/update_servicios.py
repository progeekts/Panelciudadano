#!/usr/bin/env python3
"""Monitor de incidencias oficiales de servicios digitales relevantes para ciudadanía en España."""
from __future__ import annotations
import html,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
OUT=Path('data/servicios.json');HISTORY=Path('data/historico_servicios.json');UA='PanelCiudadano/1.3 (+GitHub Pages; monitor de estado)'
STATUS_SOURCES=[
 ('GitHub','https://www.githubstatus.com/api/v2/incidents/unresolved.json','https://www.githubstatus.com/','Global'),
 ('Cloudflare','https://www.cloudflarestatus.com/api/v2/incidents/unresolved.json','https://www.cloudflarestatus.com/','Global'),
 ('Atlassian','https://status.atlassian.com/api/v2/incidents/unresolved.json','https://status.atlassian.com/','Global'),
 ('DigitalOcean','https://status.digitalocean.com/api/v2/incidents/unresolved.json','https://status.digitalocean.com/','Global'),
 ('Fastly','https://www.fastlystatus.com/api/v2/incidents/unresolved.json','https://www.fastlystatus.com/','Global'),
 ('GitLab','https://status.gitlab.com/api/v2/incidents/unresolved.json','https://status.gitlab.com/','Global'),
]
STATUS_ES={'investigating':'Investigando','identified':'Identificada','monitoring':'Monitorizando'};IMPACT_ES={'none':'Sin impacto indicado','minor':'Menor','major':'Importante','critical':'Crítica'}
def get(url,accept='text/html'):
 req=urllib.request.Request(url,headers={'Accept':accept,'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'})
 with urllib.request.urlopen(req,timeout=10) as r:return r.read().decode('utf-8',errors='replace')
def get_json(url):return json.loads(get(url,'application/json'))
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def latest_update(i):
 u=i.get('incident_updates') or [];return str(u[0].get('body') or '').strip() if u else ''
def add_status_api(items,ok,errors,service,api,status_page,scope):
 try:p=get_json(api);ok.append(service)
 except Exception as e:errors.append({'servicio':service,'error':type(e).__name__});return
 for inc in p.get('incidents',[]):
  status=str(inc.get('status') or '').lower()
  if status not in STATUS_ES:continue
  iid=str(inc.get('id') or '')
  items.append({'id':f'{service.lower()}-{iid}','tipo':'servicio','servicio':service,'titulo':str(inc.get('name') or f'Incidencia en {service}'),'resumen':latest_update(inc),'estado':STATUS_ES[status],'impacto':IMPACT_ES.get(str(inc.get('impact') or '').lower(),'No indicado'),'fecha':str(inc.get('created_at') or ''),'actualizado':str(inc.get('updated_at') or ''),'ambito':scope,'fuente':f'{service} Status','url':str(inc.get('shortlink') or status_page),'verificado':True})
def add_age_mail(items,ok,errors):
 name='Administraciones Públicas (AGE)';url='https://sede.administracionespublicas.gob.es/ayuda/'
 try:text=clean(get(url));ok.append(name)
 except Exception as e:errors.append({'servicio':name,'error':type(e).__name__});return
 if 'actualmente, nuestro sistema de correo electrónico está experimentando incidencias' in text.lower():items.append({'id':'age-correo-consultas','tipo':'servicio','servicio':'Administraciones Públicas','titulo':'Incidencia en el sistema de correo de consultas de Administraciones Públicas','resumen':'La sede oficial avisa de problemas que pueden afectar a la recepción y envío de comunicaciones relacionadas con consultas.','estado':'Activa','impacto':'No indicado','fecha':'','actualizado':'','ambito':'España','fuente':'Sede de Administraciones Públicas','url':url,'verificado':True})
def add_gencat(items,ok,errors):
 name='Generalitat de Catalunya';url='https://web.gencat.cat/es/seu-electronica/informacio/avisos-i-talls-de-serveis'
 try:text=clean(get(url));ok.append(name)
 except Exception as e:errors.append({'servicio':name,'error':type(e).__name__});return
 m=re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*h?)\s+(?:Desconocido|Desconegut)\s+.*?(Tramitar en línea).*?(Incidencia en formularios HTML)',text,re.I)
 if m:items.append({'id':'gencat-formularios-html-'+re.sub(r'\D','',m.group(1)),'tipo':'servicio','servicio':'Generalitat de Catalunya','titulo':'Incidencia en la tramitación en línea de la Generalitat','resumen':'La Sede electrónica informa de una incidencia en formularios HTML que afecta a la tramitación en línea.','estado':'Activa','impacto':'Tramitación electrónica','fecha':m.group(1),'actualizado':'','ambito':'Cataluña','fuente':'Sede electrónica de la Generalitat de Catalunya','url':url,'verificado':True})
def add_enaire(items,ok,errors):
 name='ENAIRE Sede electrónica';url='https://servicios-enaire.sede.gob.es/'
 try:text=clean(get(url));ok.append(name)
 except Exception as e:errors.append({'servicio':name,'error':type(e).__name__});return
 low=text.lower()
 if 'sede electrónica en mantenimiento' in low and 'labores de mantenimiento' in low:items.append({'id':'enaire-sede-mantenimiento','tipo':'servicio','servicio':'ENAIRE','titulo':'Sede electrónica de ENAIRE en mantenimiento','resumen':'La propia sede electrónica informa de labores de mantenimiento y de indisponibilidad temporal.','estado':'Mantenimiento','impacto':'Tramitación electrónica','fecha':'','actualizado':'','ambito':'España','fuente':'Sede electrónica de ENAIRE','url':url,'verificado':True})
def add_page_health(ok,errors,name,url):
 """Comprueba accesibilidad de sedes clave sin inventar incidencias por un simple error HTTP."""
 try:get(url);ok.append(name)
 except Exception as e:errors.append({'servicio':name,'error':type(e).__name__})
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
 history={'ultima_revision':now,'nota':'resuelto_detectado indica cuándo Panel Ciudadano dejó de detectar la incidencia; no necesariamente la hora exacta de resolución.','total':len(records),'items':sorted(records.values(),key=lambda x:x.get('primera_deteccion',''),reverse=True)[:500]}
 HISTORY.parent.mkdir(parents=True,exist_ok=True);tmp=HISTORY.with_suffix('.tmp');tmp.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(HISTORY)
def main():
 now=datetime.now(timezone.utc).isoformat();items=[];ok=[];errors=[]
 for row in STATUS_SOURCES:add_status_api(items,ok,errors,*row)
 add_age_mail(items,ok,errors);add_gencat(items,ok,errors);add_enaire(items,ok,errors)
 add_page_health(ok,errors,'Punto de Acceso General','https://sede.administracion.gob.es/')
 add_page_health(ok,errors,'Sede Ministerio de Transportes','https://sede.transportes.gob.es/')
 if not ok:print('REVISIÓN INCOMPLETA: ninguna fuente oficial respondió; se conservan los datos anteriores.');return
 items=list({x['id']:x for x in items}.values());complete=not errors;previous=load(OUT,{});previous_ids={x.get('id') for x in previous.get('items',[])};current_ids={x['id'] for x in items}
 result={'ultima_revision':now,'revision':'completa' if complete else 'parcial','cobertura':{'fuentes_configuradas':len(STATUS_SOURCES)+5,'fuentes_respondieron':len(ok)},'fuentes_ok':ok,'fuentes_error':errors,'cambios':{'nuevas':len(current_ids-previous_ids),'desaparecidas_detectadas':len(previous_ids-current_ids) if complete else 0},'total':len(items),'items':items}
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);update_history(items,complete,now);print(f"Servicios: {len(items)} activas; fuentes {len(ok)}/{len(STATUS_SOURCES)+5}; errores {len(errors)}")
if __name__=='__main__':main()
