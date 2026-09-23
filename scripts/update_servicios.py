#!/usr/bin/env python3
"""Monitor de incidencias oficiales de servicios digitales relevantes para ciudadanía en España."""
from __future__ import annotations
import html,json,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path
OUT=Path('data/servicios.json');HISTORY=Path('data/historico_servicios.json');UA='PanelCiudadano/1.9 (+GitHub Pages; monitor de estado)'
DEPRECATED_DETECTORS={'enaire-sede-mantenimiento':'Retirado del monitor porque la señal disponible no aporta una vigencia temporal suficientemente fiable.'}
# Solo fuentes de España. Se eliminan detectores globales (GitHub, Cloudflare, Atlassian, DigitalOcean).
STATUS_SOURCES=[]
PUBLIC_PAGES=[('pag','Punto de Acceso General','https://sede.administracion.gob.es/','España'),('aeat','Agencia Tributaria (AEAT)','https://sede.agenciatributaria.gob.es/','España'),('seg-social','Seguridad Social','https://sede.seg-social.gob.es/','España'),('dgt','DGT','https://sede.dgt.gob.es/','España'),('transportes','Ministerio de Transportes','https://sede.transportes.gob.es/','España')]
AUTONOMIC_PAGES=[('andalucia','Junta de Andalucía','https://juntadeandalucia.es/servicios/sede.html','Andalucía'),('aragon','Gobierno de Aragón','https://www.aragon.es/tramites','Aragón'),('asturias','Principado de Asturias','https://sede.asturias.es/','Asturias'),('balears','Govern de les Illes Balears','https://www.caib.es/seucaib/','Illes Balears'),('canarias','Gobierno de Canarias','https://sede.gobiernodecanarias.org/sede/','Canarias'),('cantabria','Gobierno de Cantabria','https://sede.cantabria.es/','Cantabria'),('castilla-leon','Junta de Castilla y León','https://www.tramitacastillayleon.jcyl.es/','Castilla y León'),('castilla-mancha','Junta de Castilla-La Mancha','https://www.jccm.es/sede','Castilla-La Mancha'),('gva','Generalitat Valenciana','https://sede.gva.es/','Comunitat Valenciana'),('galicia','Xunta de Galicia','https://sede.xunta.gal/','Galicia'),('madrid','Comunidad de Madrid','https://sede.comunidad.madrid/','Comunidad de Madrid'),('murcia','Región de Murcia','https://sede.carm.es/','Región de Murcia'),('navarra','Gobierno de Navarra','https://www.navarra.es/es/tramites','Navarra'),('euskadi','Gobierno Vasco','https://www.euskadi.eus/sede-electronica/','País Vasco'),('rioja','Gobierno de La Rioja','https://web.larioja.org/sede-electronica','La Rioja'),('ceuta','Ciudad Autónoma de Ceuta','https://sede.ceuta.es/','Ceuta'),('melilla','Ciudad Autónoma de Melilla','https://sede.melilla.es/','Melilla')]
STATUS_ES={'investigating':'Investigando','identified':'Identificada','monitoring':'Monitorizando'};IMPACT_ES={'none':'Sin impacto indicado','minor':'Menor','major':'Importante','critical':'Crítica'}
def get(url,accept='text/html'):
 req=urllib.request.Request(url,headers={'Accept':accept,'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'});return urllib.request.urlopen(req,timeout=10).read().decode('utf-8',errors='replace')
def get_json(url):return json.loads(get(url,'application/json'))
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def latest_update(i):
 u=i.get('incident_updates') or [];return str(u[0].get('body') or '').strip() if u else ''
def health_add(h,k,n,s,d,scope='',kind='auxiliar'):h.append({'clave':k,'fuente':n,'estado':s,'detalle':d,'ambito':scope,'tipo':kind,'critica_para_resolucion':kind=='incidencias'})
def add_status_api(items,h,key,service,api,page,scope):
 try:p=get_json(api);health_add(h,key,service,'ok','API oficial de estado respondió',scope,'incidencias')
 except Exception as e:health_add(h,key,service,'error',type(e).__name__,scope,'incidencias');return
 for inc in p.get('incidents',[]):
  st=str(inc.get('status') or '').lower()
  if st not in STATUS_ES:continue
  iid=str(inc.get('id') or '');items.append({'id':f'{key}-{iid}','fuente_clave':key,'tipo':'servicio','servicio':service,'titulo':str(inc.get('name') or f'Incidencia en {service}'),'resumen':latest_update(inc),'estado':STATUS_ES[st],'impacto':IMPACT_ES.get(str(inc.get('impact') or '').lower(),'No indicado'),'fecha':str(inc.get('created_at') or ''),'actualizado':str(inc.get('updated_at') or ''),'ambito':scope,'fuente':f'{service} Status','url':str(inc.get('shortlink') or page),'verificado':True})
def fetch_public(h,key,name,url,scope='España',kind='auxiliar'):
 try:t=clean(get(url));health_add(h,key,name,'ok','Fuente oficial accesible',scope,kind);return t
 except Exception as e:health_add(h,key,name,'error',type(e).__name__,scope,kind);return ''
def add_age_mail(items,h):
 key='age';url='https://sede.administracionespublicas.gob.es/ayuda/';t=fetch_public(h,key,'Administraciones Públicas (AGE)',url,'España','incidencias')
 if t and 'actualmente, nuestro sistema de correo electrónico está experimentando incidencias' in t.lower():items.append({'id':'age-correo-consultas','fuente_clave':key,'tipo':'servicio','servicio':'Administraciones Públicas','titulo':'Incidencia en el sistema de correo de consultas de Administraciones Públicas','resumen':'La sede oficial avisa de problemas que pueden afectar a la recepción y envío de comunicaciones relacionadas con consultas.','estado':'Activa','impacto':'No indicado','fecha':'','actualizado':'','ambito':'España','fuente':'Sede de Administraciones Públicas','url':url,'verificado':True})
def add_gencat(items,h):
 key='gencat';url='https://web.gencat.cat/es/seu-electronica/informacio/avisos-i-talls-de-serveis';t=fetch_public(h,key,'Generalitat de Catalunya',url,'Cataluña','incidencias')
 if not t:return
 m=re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*h?)\s+(?:Desconocido|Desconegut)\s+.*?(Tramitar en línea).*?(Incidencia en formularios HTML)',t,re.I)
 if m:items.append({'id':'gencat-formularios-html-'+re.sub(r'\D','',m.group(1)),'fuente_clave':key,'tipo':'servicio','servicio':'Generalitat de Catalunya','titulo':'Incidencia en la tramitación en línea de la Generalitat','resumen':'La Sede electrónica informa de una incidencia en formularios HTML que afecta a la tramitación en línea.','estado':'Activa','impacto':'Tramitación electrónica','fecha':m.group(1),'actualizado':'','ambito':'Cataluña','fuente':'Sede electrónica de la Generalitat de Catalunya','url':url,'verificado':True})
def add_enaire(h):fetch_public(h,'enaire','ENAIRE Sede electrónica','https://servicios-enaire.sede.gob.es/','España','auxiliar')
def add_sepe(items,h):
 key='sepe';url='https://sede.sepe.gob.es/portalSede';t=fetch_public(h,key,'SEPE',url,'España','incidencias');low=t.lower()
 if t and ('aviso de mantenimiento' in low or 'mantenimiento' in low) and ('se producirá un corte' in low or 'servicio no disponible temporalmente' in low or 'cortes en la disponibilidad' in low):items.append({'id':'sepe-aviso-mantenimiento','fuente_clave':key,'tipo':'servicio','servicio':'SEPE','titulo':'Aviso de mantenimiento en la Sede electrónica del SEPE','resumen':'La portada oficial de la Sede del SEPE muestra un aviso de mantenimiento que puede afectar temporalmente a sus servicios.','estado':'Mantenimiento','impacto':'Tramitación electrónica','fecha':'','actualizado':'','ambito':'España','fuente':'Sede electrónica del SEPE','url':url,'verificado':True})
def add_melilla(items,h):
 key='melilla';url='https://sede.melilla.es/';t=fetch_public(h,key,'Ciudad Autónoma de Melilla',url,'Melilla','incidencias');low=t.lower();today=datetime.now(timezone.utc).strftime('%d/%m/%Y')
 if t and today in t and ('labores de mantenimiento' in low or 'interrupción' in low) and ('cortes' in low or 'no disponible' in low):items.append({'id':'melilla-aviso-servicio-'+datetime.now(timezone.utc).strftime('%Y%m%d'),'fuente_clave':key,'tipo':'servicio','servicio':'Ciudad Autónoma de Melilla','titulo':'Aviso de mantenimiento en la Sede electrónica de Melilla','resumen':'La Sede electrónica de Melilla publica un aviso vigente de mantenimiento o cortes del servicio.','estado':'Mantenimiento','impacto':'Tramitación electrónica','fecha':today,'actualizado':'','ambito':'Melilla','fuente':'Sede electrónica de Melilla','url':url,'verificado':True})
def add_public_health(h):
 for k,n,u,s in PUBLIC_PAGES:fetch_public(h,k,n,u,s,'auxiliar')
def add_autonomic_health(h):
 for k,n,u,s in AUTONOMIC_PAGES:
  if k!='melilla':fetch_public(h,k,n,u,s,'auxiliar')
def load(p,d):
 try:return json.loads(p.read_text(encoding='utf-8'))
 except Exception:return d
def fingerprint(x):return '|'.join(str(x.get(k,'')).strip() for k in ('titulo','resumen','estado','impacto','actualizado'))
def infer_source_key(x):
 if x.get('fuente_clave'):return x['fuente_clave']
 iid=str(x.get('id') or '')
 for prefix,key in [('age-','age'),('gencat-','gencat'),('sepe-','sepe'),('melilla-','melilla'),('enaire-','enaire')]:
  if iid.startswith(prefix):return key
 return ''
def update_history(items,healthy,now):
 old=load(HISTORY,{'items':[]});records={x.get('id'):x for x in old.get('items',[]) if x.get('id')};current={x['id']:x for x in items};resolved=retired=0
 # Retirar del histórico del monitor entradas globales que ya no forman parte de la cobertura española.
 global_prefixes=('github-','cloudflare-','atlassian-','digitalocean-')
 records={iid:r for iid,r in records.items() if not str(iid).startswith(global_prefixes)}
 for iid,x in current.items():
  if iid not in records:records[iid]={**x,'primera_deteccion':now,'ultima_deteccion':now,'ultima_modificacion_detectada':now,'resuelto_detectado':'','estado_historico':'activo','fingerprint':fingerprint(x)}
  else:
   r=records[iid];fp=fingerprint(x)
   if r.get('fingerprint')!=fp:r['ultima_modificacion_detectada']=now
   r.update(x);r.update({'ultima_deteccion':now,'resuelto_detectado':'','estado_historico':'activo','fingerprint':fp})
 for iid,r in records.items():
  if iid in current or r.get('estado_historico')!='activo':continue
  if iid in DEPRECATED_DETECTORS:
   r['estado_historico']='retirado';r['retirado_detectado']=now;r['motivo_retirada']=DEPRECATED_DETECTORS[iid];r['resuelto_detectado']='';retired+=1;continue
  key=infer_source_key(r)
  if key and key in healthy:r['estado_historico']='resuelto';r['resuelto_detectado']=now;resolved+=1
 history={'ultima_revision':now,'nota':'Resuelto significa que la propia fuente oficial fue revisada correctamente y dejó de publicar la incidencia. Retirado significa que Panel Ciudadano dejó de usar ese detector por falta de una señal temporal suficientemente fiable; no implica resolución del servicio.','total':len(records),'items':sorted(records.values(),key=lambda x:x.get('primera_deteccion',''),reverse=True)[:500]};HISTORY.parent.mkdir(parents=True,exist_ok=True);tmp=HISTORY.with_suffix('.tmp');tmp.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(HISTORY);return resolved,retired
def main():
 now=datetime.now(timezone.utc).isoformat();items=[];health=[]
 for row in STATUS_SOURCES:add_status_api(items,health,*row)
 add_age_mail(items,health);add_gencat(items,health);add_enaire(health);add_sepe(items,health);add_melilla(items,health);add_public_health(health);add_autonomic_health(health);items=list({x['id']:x for x in items}.values());ok=[x['fuente'] for x in health if x['estado']=='ok'];errors=[{'servicio':x['fuente'],'error':x['detalle'],'tipo':x['tipo']} for x in health if x['estado']=='error'];critical=[x for x in health if x['tipo']=='incidencias'];critical_errors=[x for x in critical if x['estado']=='error'];healthy={x['clave'] for x in critical if x['estado']=='ok'}
 if not healthy:print('REVISIÓN INCOMPLETA: ninguna fuente de incidencias respondió; se conservan los datos anteriores.');return
 previous=load(OUT,{});previous_ids={x.get('id') for x in previous.get('items',[]) if str(x.get('ambito') or '')!='Global'};current_ids={x['id'] for x in items};territorial={}
 for h in health:
  scope=h.get('ambito') or 'Sin ámbito';territorial.setdefault(scope,{'configuradas':0,'respondieron':0});territorial[scope]['configuradas']+=1;territorial[scope]['respondieron']+=h['estado']=='ok'
 resolved,retired=update_history(items,healthy,now);aux_errors=[x for x in health if x['tipo']=='auxiliar' and x['estado']=='error']
 result={'ultima_revision':now,'revision':'completa' if not critical_errors else 'parcial','revision_fuentes_incidentes':'completa' if not critical_errors else 'parcial','salud_auxiliar':'completa' if not aux_errors else 'parcial','cobertura':{'fuentes_configuradas':len(health),'fuentes_respondieron':len(ok),'fuentes_incidentes':len(critical),'fuentes_incidentes_ok':len(critical)-len(critical_errors),'territorial':territorial},'salud_fuentes':health,'fuentes_ok':ok,'fuentes_error':errors,'cambios':{'nuevas':len(current_ids-previous_ids),'resueltas_detectadas':resolved,'retiradas_monitor':retired},'total':len(items),'items':items};OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);print(f'Servicios: {len(items)} activas; incidencias {len(critical)-len(critical_errors)}/{len(critical)}; resueltas {resolved}; retiradas {retired}')
if __name__=='__main__':main()
