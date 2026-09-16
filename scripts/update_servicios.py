#!/usr/bin/env python3
"""Recoge incidencias ACTIVAS desde páginas de estado oficiales.

Solo usa endpoints oficiales estructurados. Una fuente caída no se interpreta
como servicio operativo: se registra como error de revisión. El dataset solo se
actualiza si responde al menos una fuente.
"""
from __future__ import annotations
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/servicios.json")
UA = "PanelCiudadano/1.0 (+GitHub Pages; monitor de estado)"
SOURCES = [
    ("GitHub", "https://www.githubstatus.com/api/v2/incidents/unresolved.json", "https://www.githubstatus.com/"),
    ("Cloudflare", "https://www.cloudflarestatus.com/api/v2/incidents/unresolved.json", "https://www.cloudflarestatus.com/"),
]
STATUS_ES = {"investigating":"Investigando","identified":"Identificada","monitoring":"Monitorizando"}
IMPACT_ES = {"none":"Sin impacto indicado","minor":"Menor","major":"Importante","critical":"Crítica"}

def get_json(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
    with urllib.request.urlopen(req,timeout=10) as r:
        return json.load(r)

def latest_update(incident):
    updates=incident.get("incident_updates") or []
    if not updates:return ""
    return str(updates[0].get("body") or "").strip()

def main():
    now=datetime.now(timezone.utc)
    items=[]; ok=[]; errors=[]
    for service,api,status_page in SOURCES:
        try:
            payload=get_json(api); ok.append(service)
        except Exception as exc:
            errors.append({"servicio":service,"error":type(exc).__name__})
            continue
        for inc in payload.get("incidents",[]):
            status=str(inc.get("status") or "").lower()
            if status not in ("investigating","identified","monitoring"):
                continue
            iid=str(inc.get("id") or "")
            items.append({
                "id":f"{service.lower()}-{iid}","tipo":"servicio","servicio":service,
                "titulo":str(inc.get("name") or f"Incidencia en {service}"),
                "resumen":latest_update(inc),"estado":STATUS_ES.get(status,status),
                "impacto":IMPACT_ES.get(str(inc.get("impact") or "").lower(), str(inc.get("impact") or "")),
                "fecha":str(inc.get("created_at") or ""),"actualizado":str(inc.get("updated_at") or ""),
                "ambito":"Según el proveedor","fuente":f"{service} Status",
                "url":str(inc.get("shortlink") or status_page),"verificado":True
            })
    if not ok:
        print("REVISIÓN INCOMPLETA: ninguna fuente oficial respondió; se conservan los datos anteriores.")
        return
    result={"ultima_revision":now.isoformat(),"revision":"completa" if not errors else "parcial",
            "fuentes_ok":ok,"fuentes_error":errors,"total":len(items),"items":items}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    tmp=OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(OUT)
    print(f"Servicios: {len(items)} incidencias activas; fuentes OK: {', '.join(ok)}")
if __name__=="__main__": main()
