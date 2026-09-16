#!/usr/bin/env python3
"""Actualiza el radar de ayudas desde la fuente oficial SNPSAP/BDNS.

La tabla oficial de convocatorias ya publica código BDNS, administración,
departamento, órgano, fecha de registro y título. El script admite variantes
de nombres de campo usadas por la API y no deduce estados de solicitud cuando
la fuente no aporta fechas inequívocas.
"""
from __future__ import annotations
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

SEARCH=os.environ.get("BDNS_API_URL","https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda")
OUT=Path("data/ayudas.json")
LIMIT=int(os.environ.get("AYUDAS_LIMIT","100"))
UA="PanelCiudadano/1.3 (+GitHub Pages; fuente oficial SNPSAP/BDNS)"

def get_json(url,timeout=30):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

def rows(p):
    if isinstance(p,list):return p
    if isinstance(p,dict):
        for k in ("content","items","results","resultado","convocatorias","data"):
            if isinstance(p.get(k),list):return p[k]
    return []

def normkey(k):
    return ''.join(ch for ch in str(k).lower() if ch.isalnum())

def value_by_alias(d,*aliases):
    if not isinstance(d,dict):return ""
    lookup={normkey(k):v for k,v in d.items()}
    for a in aliases:
        v=lookup.get(normkey(a))
        if v not in (None,""):return v
    return ""

def txt(v):
    if isinstance(v,dict):
        for k in ("descripcion","nombre","denominacion","texto","valor","label","description","name"):
            x=value_by_alias(v,k)
            if x not in (None,""):return txt(x)
        return ""
    if isinstance(v,list):return ", ".join(x for x in (txt(i) for i in v) if x)
    return str(v or "").strip()

def normalize(r):
    code=txt(value_by_alias(r,"codigoBDNS","codigo_bdns","codigo","id","numeroConvocatoria","numero_convocatoria"))
    title=txt(value_by_alias(r,"titulo","tituloConvocatoria","titulo_convocatoria","descripcion","nombre"))
    admin=txt(value_by_alias(r,"administracion","nivelAdministracion","nivel_administracion","tipoAdministracion","tipo_administracion"))
    dep=txt(value_by_alias(r,"departamento","departamentoConvocante","departamento_convocante"))
    body=txt(value_by_alias(r,"organo","órgano","organoConvocante","organo_convocante","convocante"))
    reg=txt(value_by_alias(r,"fechaRegistro","fecha_registro","fechaPublicacion","fecha_publicacion","fecha"))
    beneficiarios=txt(value_by_alias(r,"tipoBeneficiario","tipo_beneficiario","tiposBeneficiarios","beneficiariosElegibles"))
    region=txt(value_by_alias(r,"regionImpacto","region_impacto","regionesImpacto"))
    presupuesto=txt(value_by_alias(r,"presupuestoTotal","presupuesto_total","importeTotal","importe_total","presupuesto"))
    url=f"https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{code}" if code else "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias"
    return {"id":f"bdns-{code}" if code else f"bdns-{abs(hash(title+reg))}","codigo_bdns":code,"tipo":"ayuda","titulo":title,"administracion":admin,"departamento":dep,"organismo":body,"fecha_registro":reg,"beneficiarios":beneficiarios,"region_impacto":region,"presupuesto":presupuesto,"inicio_solicitud":"","fin_solicitud":"","solicitud_indefinida":False,"estado_plazo":"No determinado","fuente":"SNPSAP / Base de Datos Nacional de Subvenciones","url":url,"verificado":True}

def main():
    payload=get_json(SEARCH+"?"+urllib.parse.urlencode({"page":0,"pageSize":LIMIT}))
    raw=rows(payload)
    items=[normalize(x) for x in raw if isinstance(x,dict)]
    items=[x for x in items if x["titulo"]]
    if not items:raise RuntimeError("La BDNS no devolvió convocatorias utilizables; se conservan los datos anteriores.")
    with_meta=sum(bool(x["administracion"] or x["departamento"] or x["organismo"] or x["fecha_registro"]) for x in items)
    result={"fuente":"SNPSAP / BDNS","fuente_url":"https://www.infosubvenciones.es/bdnstrans/GE/es/inicio","ultima_revision":datetime.now(timezone.utc).isoformat(),"total":len(items),"con_metadatos":with_meta,"criterio_estado":"La BDNS incluye convocatorias abiertas, cerradas, resueltas e instrumentales. Panel Ciudadano no afirma que una convocatoria esté abierta salvo que disponga de un plazo inequívoco.","items":items}
    OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(OUT)
    print(f"Actualizadas {len(items)} convocatorias; {with_meta} con metadatos del listado oficial")
if __name__=="__main__":
    try:main()
    except Exception as exc:print(f"ERROR: {exc}",file=sys.stderr);sys.exit(1)
