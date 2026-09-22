#!/usr/bin/env python3
"""Genera un resumen público de salud/frescura de los módulos de datos."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path

MODULES={
 "servicios":("Servicios digitales",2),
 "movilidad":("Movilidad · DGT",2),
 "meteo":("Meteorología · AEMET",2),
 "ayudas":("Ayudas · BDNS",30),
 "estafas":("Estafas · INCIBE",30),
 "alimentacion":("Alimentación · AESAN",30),
 "salud":("Salud · AEMPS",30),
}
def parse(v):
 if not v:return None
 try:return datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(timezone.utc)
 except Exception:return None


def validate_output(out):
 required={"generado","estado_general","resumen","modulos","nota"}
 missing=required-set(out)
 if missing: raise ValueError(f"Faltan campos de salud: {sorted(missing)}")
 if len(out["modulos"]) != len(MODULES): raise ValueError("Número de módulos inesperado")
 ids=[m.get("id") for m in out["modulos"]]
 if len(ids)!=len(set(ids)): raise ValueError("Módulos duplicados")

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--data-dir",default="data");ap.add_argument("--out",default="data/source_health.json");a=ap.parse_args()
 now=datetime.now(timezone.utc); rows=[]
 for key,(name,maxh) in MODULES.items():
  p=Path(a.data_dir)/f"{key}.json"; status="error"; detail="Datos no disponibles"; rev=None
  try:
   d=json.loads(p.read_text(encoding="utf-8"));rev=parse(d.get("ultima_revision"))
   declared=str(d.get("revision_fuentes_incidentes") if key=="servicios" else d.get("revision","completa")).lower()
   age=(now-rev).total_seconds()/3600 if rev else None
   if age is not None and age < -0.25:
    status="unknown";detail="La fecha de revisión está en el futuro; reloj no verificable"
   elif declared=="error":
    status="error";detail="La última consulta no pudo validarse"
   elif age is None:status="unknown";detail="Sin fecha de revisión verificable"
   elif age>maxh:status="stale";detail=f"Última revisión hace {age:.1f} h; supera el umbral de {maxh} h"
   elif declared=="parcial":status="partial";detail="La fuente respondió de forma parcial"
   else:status="ok";detail="Revisión dentro del intervalo esperado"
  except Exception as e: detail=f"No se pudo validar el fichero ({type(e).__name__})"
  rows.append({"id":key,"nombre":name,"estado":status,"ultima_revision":rev.isoformat() if rev else None,"umbral_horas":maxh,"detalle":detail})
 counts={s:sum(r["estado"]==s for r in rows) for s in ("ok","partial","stale","error","unknown")}
 overall="ok" if counts["partial"]+counts["stale"]+counts["error"]+counts["unknown"]==0 else ("degraded" if counts["ok"] else "unavailable")
 out={"generado":now.isoformat(),"estado_general":overall,"resumen":counts,"modulos":rows,
 "nota":"El estado técnico indica si Panel Ciudadano ha podido revisar sus fuentes recientemente. No describe por sí mismo la existencia o ausencia de incidencias ciudadanas."}
 validate_output(out)
 target=Path(a.out)
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Salud de fuentes: {overall}; "+", ".join(f"{k}={v}" for k,v in counts.items()))
if __name__=="__main__":main()
