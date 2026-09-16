#!/usr/bin/env python3
"""Recoge incidencias activas desde fuentes oficiales.

Combina APIs de estado estructuradas con avisos públicos de administraciones
españolas. Una fuente caída nunca se interpreta como servicio operativo.
"""
from __future__ import annotations
import html, json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT=Path("data/servicios.json")
UA="PanelCiudadano/1.1 (+GitHub Pages; monitor de estado)"
STATUS_SOURCES=[
 ("GitHub","https://www.githubstatus.com/api/v2/incidents/unresolved.json","https://www.githubstatus.com/"),
 ("Cloudflare","https://www.cloudflarestatus.com/api/v2/incidents/unresolved.json","https://www.cloudflarestatus.com/"),
]
STATUS_ES={"investigating":"Investigando","identified":"Identificada","monitoring":"Monitorizando"}
IMPACT_ES={"none":"Sin impacto indicado","minor":"Menor","major":"Importante","critical":"Crítica"}

def get(url,accept="text/html"):
 req=urllib.request.Request(url,headers={"Accept":accept,"User-Agent":UA,"Accept-Language":"es-ES,es;q=0.9"})
 with urllib.request.urlopen(req,timeout=10) as r:return r.read().decode("utf-8",errors="replace")
def get_json(url):return json.loads(get(url,"application/json"))
def clean(s):return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s))).strip()
def latest_update(i):
 u=i.get("incident_updates") or []
 return str(u[0].get("body") or "").strip() if u else ""
def add_status_api(items,ok,errors,service,api,status_page):
 try:p=get_json(api);ok.append(service)
 except Exception as e:errors.append({"servicio":service,"error":type(e).__name__});return
 for inc in p.get("incidents",[]):
  status=str(inc.get("status") or "").lower()
  if status not in STATUS_ES:continue
  iid=str(inc.get("id") or "")
  items.append({"id":f"{service.lower()}-{iid}","tipo":"servicio","servicio":service,"titulo":str(inc.get("name") or f"Incidencia en {service}"),"resumen":latest_update(inc),"estado":STATUS_ES[status],"impacto":IMPACT_ES.get(str(inc.get("impact") or "").lower(),"No indicado"),"fecha":str(inc.get("created_at") or ""),"actualizado":str(inc.get("updated_at") or ""),"ambito":"Según el proveedor","fuente":f"{service} Status","url":str(inc.get("shortlink") or status_page),"verificado":True})
def add_age_mail(items,ok,errors):
 name="Administraciones Públicas (AGE)";url="https://sede.administracionespublicas.gob.es/ayuda/"
 try:text=clean(get(url));ok.append(name)
 except Exception as e:errors.append({"servicio":name,"error":type(e).__name__});return
 marker="Actualmente, nuestro sistema de correo electrónico está experimentando incidencias"
 if marker.lower() in text.lower():
  items.append({"id":"age-correo-consultas","tipo":"servicio","servicio":"Administraciones Públicas","titulo":"Incidencia en el sistema de correo de consultas de Administraciones Públicas","resumen":"La sede oficial avisa de problemas que pueden afectar a la recepción y envío de comunicaciones relacionadas con consultas.","estado":"Activa","impacto":"No indicado","fecha":"","actualizado":"","ambito":"España","fuente":"Sede de Administraciones Públicas","url":url,"verificado":True})
def add_gencat(items,ok,errors):
 name="Generalitat de Catalunya";url="https://web.gencat.cat/es/seu-electronica/informacio/avisos-i-talls-de-serveis"
 try:text=clean(get(url));ok.append(name)
 except Exception as e:errors.append({"servicio":name,"error":type(e).__name__});return
 # La propia sede utiliza 'Desconocido' en la fecha de fin para incidencias abiertas.
 m=re.search(r"(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s*h?)\s+(?:Desconocido|Desconegut)\s+.*?(Tramitar en línea).*?(Incidencia en formularios HTML)",text,re.I)
 if m:
  items.append({"id":"gencat-formularios-html-"+re.sub(r"\D","",m.group(1)),"tipo":"servicio","servicio":"Generalitat de Catalunya","titulo":"Incidencia en la tramitación en línea de la Generalitat","resumen":"La Sede electrónica informa de una incidencia en formularios HTML que afecta a la tramitación en línea.","estado":"Activa","impacto":"Tramitación electrónica","fecha":m.group(1),"actualizado":"","ambito":"Cataluña","fuente":"Sede electrónica de la Generalitat de Catalunya","url":url,"verificado":True})

def main():
 now=datetime.now(timezone.utc);items=[];ok=[];errors=[]
 for s,a,p in STATUS_SOURCES:add_status_api(items,ok,errors,s,a,p)
 add_age_mail(items,ok,errors);add_gencat(items,ok,errors)
 if not ok:
  print("REVISIÓN INCOMPLETA: ninguna fuente oficial respondió; se conservan los datos anteriores.");return
 # Evita duplicados si una fuente repite el mismo incidente.
 items=list({x["id"]:x for x in items}.values())
 result={"ultima_revision":now.isoformat(),"revision":"completa" if not errors else "parcial","fuentes_ok":ok,"fuentes_error":errors,"total":len(items),"items":items}
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix(".tmp");tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(OUT)
 print(f"Servicios: {len(items)} incidencias activas; fuentes OK: {', '.join(ok)}")
if __name__=="__main__":main()
