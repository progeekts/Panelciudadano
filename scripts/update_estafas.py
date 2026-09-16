#!/usr/bin/env python3
"""Actualiza el radar de estafas a partir de publicaciones oficiales de INCIBE.

Extrae únicamente páginas de Ciudadanía que sean avisos y estén relacionadas
con fraude/suplantación. Conserva siempre la URL oficial. Si no puede obtener
resultados válidos, falla sin sobrescribir los datos existentes.
"""
from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.incibe.es"
LIST_URL = BASE + "/ciudadania/tags/aviso"
OUT = Path("data/estafas.json")
UA = "PanelCiudadano/1.0 (+GitHub Pages; fuente: INCIBE)"


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def meta(page: str, prop: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)',
        rf'<meta[^>]+name=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)',
    ]
    for p in patterns:
        m = re.search(p, page, re.I)
        if m:
            return clean(m.group(1))
    return ""


def main():
    listing = get(LIST_URL)
    paths = re.findall(r'href=["\'](/ciudadania/avisos/[^"\'#?]+)', listing, re.I)
    seen = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    items = []
    for path in seen[:30]:
        url = urllib.parse.urljoin(BASE, path)
        try:
            page = get(url)
        except Exception:
            continue
        title = meta(page, "og:title")
        desc = meta(page, "description") or meta(page, "og:description")
        text = clean(page).lower()
        # El radar es de estafas, no un agregador general de vulnerabilidades.
        if not any(k in (title + " " + desc + " " + text[:12000]).lower() for k in
                   ("fraude", "phishing", "smishing", "vishing", "suplant", "estafa")):
            continue
        date = ""
        m = re.search(r"Fecha de publicación\s*(\d{1,2}/\d{1,2}/\d{4})", clean(page), re.I)
        if m:
            date = m.group(1)
        importance = ""
        m = re.search(r"Importancia\s*([1-5]\s*-\s*[^<\n]+)", clean(page), re.I)
        if m:
            importance = m.group(1).strip()[:60]
        slug = path.rstrip("/").split("/")[-1]
        items.append({
            "id": "incibe-" + slug,
            "tipo": "estafa",
            "titulo": title or slug.replace("-", " ").capitalize(),
            "resumen": desc,
            "fecha": date,
            "importancia": importance,
            "ambito": "España / usuarios de Internet",
            "fuente": "INCIBE · Ciudadanía",
            "url": url,
            "verificado": True,
        })
    if not items:
        raise RuntimeError("INCIBE no devolvió avisos de fraude utilizables; se conservan los datos anteriores.")
    result = {
        "fuente": "INCIBE · Ciudadanía",
        "fuente_url": LIST_URL,
        "ultima_revision": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"Actualizadas {len(items)} alertas de estafas")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
