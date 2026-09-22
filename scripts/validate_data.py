#!/usr/bin/env python3
"""Validación conservadora de los JSON públicos antes de hacer commit."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

MIN_RATIO = float(os.environ.get("MIN_JSON_SIZE_RATIO", "0.20"))
errors=[]

for raw in sys.argv[1:]:
    path=Path(raw)
    if not path.exists():
        errors.append(f"{path}: no existe")
        continue
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path}: JSON inválido ({exc})")
        continue
    if data is None:
        errors.append(f"{path}: contenido nulo")
    elif isinstance(data, (dict,list)) and len(data)==0:
        errors.append(f"{path}: estructura raíz vacía")

    # Compara con la versión de HEAD para detectar truncados/corrupción evidente.
    try:
        import subprocess
        old=subprocess.check_output(["git","show",f"HEAD:{path.as_posix()}"])
        new_size=path.stat().st_size
        old_size=len(old)
        if old_size >= 1024 and new_size < old_size * MIN_RATIO:
            errors.append(
                f"{path}: tamaño cayó de {old_size} a {new_size} bytes "
                f"(< {MIN_RATIO:.0%} de la versión anterior)"
            )
    except Exception:
        pass

if errors:
    print("VALIDACIÓN FALLIDA:")
    for e in errors: print(f"- {e}")
    sys.exit(1)

print("Validación de datos superada:", ", ".join(sys.argv[1:]))
