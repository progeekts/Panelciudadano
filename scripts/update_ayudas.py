#!/usr/bin/env python3
"""Actualiza el radar de ayudas desde la fuente oficial SNPSAP/BDNS.

El script consulta el API REST público de la BDNS, conserva solo campos
necesarios para el panel y escribe data/ayudas.json. Si la fuente falla,
termina con error y no sustituye datos existentes por información inventada.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = os.environ.get("BDNS_API_URL", "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda")
OUT = Path("data/ayudas.json")
LIMIT = int(os.environ.get("AYUDAS_LIMIT", "100"))


def get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "PanelCiudadano/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rows(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("content", "items", "results", "resultado", "convocatorias", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def first(d, *keys, default=""):
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return default


def normalize(r):
    code = str(first(r, "codigoBDNS", "codigo", "id", "numeroConvocatoria"))
    title = str(first(r, "titulo", "descripcion", "nombre", "tituloConvocatoria"))
    admin = str(first(r, "administracion", "nivelAdministracion"))
    department = str(first(r, "departamento"))
    body = str(first(r, "organo", "organoConvocante", "convocante"))
    registered = str(first(r, "fechaRegistro", "fecha", "fechaPublicacion"))
    detail = f"https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatoria/{code}" if code else "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/convocatorias"
    return {
        "id": f"bdns-{code}" if code else f"bdns-{abs(hash(title + registered))}",
        "tipo": "ayuda",
        "titulo": title.strip(),
        "administracion": admin.strip(),
        "departamento": department.strip(),
        "organismo": body.strip(),
        "fecha_registro": registered.strip(),
        "fuente": "SNPSAP / Base de Datos Nacional de Subvenciones",
        "url": detail,
        "verificado": True,
    }


def main():
    params = urllib.parse.urlencode({"page": 0, "pageSize": LIMIT})
    payload = get_json(f"{API_BASE}?{params}")
    items = [normalize(x) for x in rows(payload) if isinstance(x, dict)]
    items = [x for x in items if x["titulo"]]
    if not items:
        raise RuntimeError("La BDNS no devolvió convocatorias utilizables; se conservan los datos anteriores.")
    result = {
        "fuente": "SNPSAP / BDNS",
        "fuente_url": "https://www.pap.hacienda.gob.es/bdnstrans/GE/es/inicio",
        "ultima_revision": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"Actualizadas {len(items)} convocatorias")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
