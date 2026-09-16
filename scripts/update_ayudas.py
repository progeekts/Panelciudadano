#!/usr/bin/env python3
"""Actualiza el radar de ayudas usando exclusivamente la API oficial SNPSAP/BDNS."""
from __future__ import annotations
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE="https://www.infosubvenciones.es/bdnstrans/api"
SEARCH=os.environ.get("BDNS_API_URL",BASE+"/convocatorias/busqueda")
DETAIL=BASE+"/convocatorias"
OUT=Path("data/ayudas.json")
LIMIT=int(os.environ.get("AYUDAS_LIMIT","100"))
ENRICH_LIMIT=int(os.environ.get("AYUDAS_ENRICH_LIMIT","30"))
UA="PanelCiudadano/1.4 (+GitHub Pages; fuente oficial SNPSAP/BDNS)"

def get_json(url,timeout=20):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

def rows(p):
    return p if isinstance(p,list) else p.get("content",[]) if isinstance(p,dict) else []

def text(v):
    if isinstance(v,list):return ", ".join(str(x.get("descripcion","")).strip() for x in v if isinstance(x,dict) and x.get("descripcion"))
    return str(v or "").strip()

def status(start,end,indef):
    if indef:return "Indefinido"
    def dt(v):
        try:return datetime.fromisoformat(str(v)[:10]).replace(tzinfo=timezone.utc)
        except Exception:return None
    now=datetime.now(timezone.utc);a=dt(start);b=dt(end)
    if a and now<a:return "Próxima"
    if b and now>b:return "Finalizada"
    if (not a or a<=now) and b and now<=b:return "Abierta"
    return "No determinado"

def normalize(r):
    code=str(r.get("numeroConvocatoria") or r.get("codigoBDNS") or "").strip()
    title=str(r.get("descripcion") or "").strip()
    return {"id":f"bdns-{code}","codigo_bdns":code,"tipo":"ayuda","titulo":title,
      "administracion":str(r.get("nivel1") or "").strip(),"departamento":str(r.get("nivel2") or "").strip(),
      "organismo":str(r.get("nivel3") or "").strip(),"fecha_registro":str(r.get("fechaRecepcion") or "").strip(),
      "beneficiarios":"","region_impacto":"","presupuesto":"","inicio_solicitud":"","fin_solicitud":"",
      "solicitud_indefinida":False,"estado_plazo":"No determinado","finalidad":"","sede_electronica":"",
      "fuente":"SNPSAP / Base de Datos Nacional de Subvenciones",
      "url":f"https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{code}","verificado":True}

def enrich(x):
    code=x["codigo_bdns"]
    if not code:return False
    try:d=get_json(DETAIL+"?"+urllib.parse.urlencode({"vpd":"GE","numConv":code}),12)
    except Exception:return False
    if not isinstance(d,dict) or not d:return False
    org=d.get("organo") or {}
    if isinstance(org,dict):
        x["administracion"]=str(org.get("nivel1") or x["administracion"] or "").strip()
        x["departamento"]=str(org.get("nivel2") or x["departamento"] or "").strip()
        x["organismo"]=str(org.get("nivel3") or x["organismo"] or "").strip()
    x["fecha_registro"]=str(d.get("fechaRecepcion") or x["fecha_registro"] or "").strip()
    x["beneficiarios"]=text(d.get("tiposBeneficiarios"))
    x["region_impacto"]=text(d.get("regiones"))
    p=d.get("presupuestoTotal");x["presupuesto"]=p if p not in (None,"") else ""
    x["inicio_solicitud"]=str(d.get("fechaInicioSolicitud") or "").strip()
    x["fin_solicitud"]=str(d.get("fechaFinSolicitud") or "").strip()
    x["solicitud_indefinida"]=d.get("abierto") is True
    x["estado_plazo"]=status(x["inicio_solicitud"],x["fin_solicitud"],x["solicitud_indefinida"])
    x["finalidad"]=str(d.get("descripcionFinalidad") or "").strip()
    x["sede_electronica"]=str(d.get("sedeElectronica") or "").strip()
    return True

def main():
    q={"page":0,"pageSize":LIMIT,"order":"fechaRecepcion","direccion":"desc","vpd":"GE"}
    raw=rows(get_json(SEARCH+"?"+urllib.parse.urlencode(q)))
    items=[normalize(r) for r in raw if isinstance(r,dict) and r.get("descripcion")]
    if not items:raise RuntimeError("La BDNS no devolvió convocatorias; se conservan los datos anteriores.")
    enriched=0
    for x in items[:ENRICH_LIMIT]:
        if enrich(x):enriched+=1
        time.sleep(.08)
    result={"fuente":"SNPSAP / BDNS","fuente_url":"https://www.infosubvenciones.es/bdnstrans/GE/es/inicio",
      "ultima_revision":datetime.now(timezone.utc).isoformat(),"total":len(items),"con_metadatos":sum(bool(x["administracion"] or x["departamento"] or x["organismo"] or x["fecha_registro"]) for x in items),
      "enriquecidas":enriched,"criterio_estado":"El estado del plazo se calcula solo a partir de fechaInicioSolicitud, fechaFinSolicitud o abierto facilitados por la API oficial BDNS.","items":items}
    OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(OUT)
    print(f"Actualizadas {len(items)} convocatorias; {enriched} detalles oficiales enriquecidos")
if __name__=="__main__":
    try:main()
    except Exception as exc:print(f"ERROR: {exc}",file=sys.stderr);sys.exit(1)
