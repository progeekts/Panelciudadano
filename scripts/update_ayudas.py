#!/usr/bin/env python3
"""Actualiza y enriquece el radar de ayudas desde la API oficial SNPSAP/BDNS.

Usa el listado oficial para descubrir convocatorias y consulta el detalle oficial
solo para un subconjunto reciente. Nunca deduce si una ayuda está abierta: el
estado se calcula únicamente cuando la BDNS facilita fechas de solicitud claras.
"""
from __future__ import annotations
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE="https://www.infosubvenciones.es/bdnstrans/api"
SEARCH=os.environ.get("BDNS_API_URL", BASE+"/convocatorias/busqueda")
DETAIL=BASE+"/convocatorias"
OUT=Path("data/ayudas.json")
LIMIT=int(os.environ.get("AYUDAS_LIMIT","100"))
ENRICH_LIMIT=int(os.environ.get("AYUDAS_ENRICH_LIMIT","30"))
UA="PanelCiudadano/1.2 (+GitHub Pages; fuente oficial SNPSAP/BDNS)"

def get_json(url, timeout=20):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

def rows(p):
    if isinstance(p,list):return p
    if isinstance(p,dict):
        for k in ("content","items","results","resultado","convocatorias","data"):
            if isinstance(p.get(k),list):return p[k]
    return []

def first(d,*keys,default=""):
    if not isinstance(d,dict):return default
    for k in keys:
        if d.get(k) not in (None,""):return d[k]
    return default

def txt(v):
    if isinstance(v,dict):
        return str(first(v,"descripcion","nombre","denominacion","texto","valor","label",default="")).strip()
    if isinstance(v,list):return ", ".join(filter(None,(txt(x) for x in v)))
    return str(v or "").strip()

def normalize(r):
    code=txt(first(r,"codigoBDNS","codigo","id","numeroConvocatoria"))
    title=txt(first(r,"titulo","descripcion","nombre","tituloConvocatoria"))
    admin=txt(first(r,"administracion","nivelAdministracion","tipoAdministracion"))
    dep=txt(first(r,"departamento")); body=txt(first(r,"organo","organoConvocante","convocante"))
    reg=txt(first(r,"fechaRegistro","fecha","fechaPublicacion"))
    return {"id":f"bdns-{code}" if code else f"bdns-{abs(hash(title+reg))}","codigo_bdns":code,"tipo":"ayuda","titulo":title,"administracion":admin,"departamento":dep,"organismo":body,"fecha_registro":reg,"beneficiarios":"","region_impacto":"","presupuesto":"","inicio_solicitud":"","fin_solicitud":"","solicitud_indefinida":False,"estado_plazo":"No determinado","fuente":"SNPSAP / Base de Datos Nacional de Subvenciones","url":f"https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{code}" if code else "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias","verificado":True}

def flatten_detail(p):
    if isinstance(p,list): return p[0] if p and isinstance(p[0],dict) else {}
    if not isinstance(p,dict):return {}
    for k in ("convocatoria","detalle","data","resultado"):
        if isinstance(p.get(k),dict):return p[k]
    return p

def enrich(item):
    code=item["codigo_bdns"]
    if not code:return item
    # El endpoint oficial /convocatorias admite el código como parámetro de consulta.
    candidates=[DETAIL+"?"+urllib.parse.urlencode({"codigoBDNS":code}),DETAIL+"?"+urllib.parse.urlencode({"codigo":code})]
    d={}
    for url in candidates:
        try:
            d=flatten_detail(get_json(url,12))
            if d:break
        except Exception:continue
    if not d:return item
    item["administracion"]=item["administracion"] or txt(first(d,"administracion","tipoAdministracion","nivelAdministracion"))
    item["departamento"]=item["departamento"] or txt(first(d,"departamento"))
    item["organismo"]=item["organismo"] or txt(first(d,"organo","organoConvocante","convocante"))
    item["fecha_registro"]=item["fecha_registro"] or txt(first(d,"fechaRegistro","fechaPublicacion"))
    item["beneficiarios"]=txt(first(d,"tipoBeneficiario","tiposBeneficiarios","beneficiariosElegibles","beneficiario"))
    item["region_impacto"]=txt(first(d,"regionImpacto","regionesImpacto","region"))
    item["presupuesto"]=txt(first(d,"presupuestoTotal","presupuesto","importeTotal"))
    item["inicio_solicitud"]=txt(first(d,"fechaInicioSolicitud","fechaInicioPeriodoSolicitud","inicioSolicitud"))
    item["fin_solicitud"]=txt(first(d,"fechaFinSolicitud","fechaFinalizacionPeriodoSolicitud","finSolicitud"))
    indef=first(d,"solicitudIndefinida","plazoIndefinido","sePuedeSolicitarIndefinidamente",default=False)
    item["solicitud_indefinida"]=str(indef).lower() in ("true","si","sí","1") or indef is True
    item["estado_plazo"]="Indefinido" if item["solicitud_indefinida"] else plazo(item["inicio_solicitud"],item["fin_solicitud"])
    return item

def parse_date(v):
    if not v:return None
    s=str(v).strip()
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y"):
        try:return datetime.strptime(s[:10],fmt).replace(tzinfo=timezone.utc)
        except ValueError:pass
    m=re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})",s)
    if m:
        try:return datetime(int(m.group(3)),int(m.group(2)),int(m.group(1)),tzinfo=timezone.utc)
        except ValueError:return None
    return None

def plazo(start,end):
    now=datetime.now(timezone.utc); a=parse_date(start); b=parse_date(end)
    if a and now<a:return "Próxima"
    if b and now>b:return "Finalizada"
    if a and b and a<=now<=b:return "Abierta"
    if b and now<=b:return "Abierta"
    return "No determinado"

def main():
    p=get_json(SEARCH+"?"+urllib.parse.urlencode({"page":0,"pageSize":LIMIT}))
    items=[normalize(x) for x in rows(p) if isinstance(x,dict)]
    items=[x for x in items if x["titulo"]]
    if not items:raise RuntimeError("La BDNS no devolvió convocatorias utilizables; se conservan los datos anteriores.")
    enriched=0
    for i in range(min(ENRICH_LIMIT,len(items))):
        before=dict(items[i]); items[i]=enrich(items[i])
        if items[i]!=before:enriched+=1
        time.sleep(.05)
    result={"fuente":"SNPSAP / BDNS","fuente_url":"https://www.infosubvenciones.es/bdnstrans/GE/es/inicio","ultima_revision":datetime.now(timezone.utc).isoformat(),"total":len(items),"enriquecidas":enriched,"criterio_estado":"El estado del plazo solo se muestra cuando la BDNS aporta fechas interpretables; en otro caso se indica No determinado.","items":items}
    OUT.parent.mkdir(parents=True,exist_ok=True); tmp=OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(OUT)
    print(f"Actualizadas {len(items)} convocatorias; {enriched} enriquecidas con detalle oficial")
if __name__=="__main__":
    try:main()
    except Exception as exc:print(f"ERROR: {exc}",file=sys.stderr);sys.exit(1)
