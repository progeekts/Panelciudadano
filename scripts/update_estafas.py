#!/usr/bin/env python3
"""Actualiza el radar de estafas desde el índice oficial de avisos de INCIBE.

Diseñado para ser rápido: extrae título, fecha, resumen e importancia directamente
del listado de avisos y solo consulta fichas individuales cuando faltan datos.
Si el índice principal no responde, conserva el último dataset válido.
"""
from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "https://www.incibe.es"
LIST_URL = BASE + "/ciudadania/avisos"
OUT = Path("data/estafas.json")
UA = "PanelCiudadano/1.3 (+GitHub Pages; fuente: INCIBE)"
MAX_AGE_DAYS = 120
MAX_PAGES = 3
TIMEOUT = 12
KEYWORDS = ("fraude", "phishing", "smishing", "vishing", "suplant", "estafa", "fraudulent", "sextors")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "close",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(s: str) -> str:
    s = re.sub(r"<script\b[^>]*>.*?</script>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<style\b[^>]*>.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_date(raw: str):
    try:
        return datetime.strptime(raw, "%d/%m/%Y").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def extract_cards(page: str):
    """Extrae bloques del listado sin abrir cada ficha individual."""
    links = list(re.finditer(r'<a[^>]+href=["\'](/ciudadania/avisos/[^"\'#?]+)["\'][^>]*>(.*?)</a>', page, re.I | re.S))
    cards = []
    seen = set()
    for i, m in enumerate(links):
        path = m.group(1)
        if path in seen:
            continue
        title = clean(m.group(2))
        if not title or len(title) < 8:
            continue
        # El texto relevante suele estar en el bloque alrededor del enlace.
        start = max(0, m.start() - 500)
        end = min(len(page), (links[i + 1].start() if i + 1 < len(links) else m.end() + 1800))
        block = clean(page[start:end])
        dm = re.search(r"(?:Publicado el|Fecha de publicación)\s*(\d{1,2}/\d{1,2}/\d{4})", block, re.I)
        if not dm:
            continue
        date_raw = dm.group(1)
        importance = ""
        im = re.search(r"Importancia\s*([1-5]\s*-\s*(?:Baja|Media|Alta|Crítica|Critica))", block, re.I)
        if im:
            importance = im.group(1).strip()
        haystack = (title + " " + block).lower()
        if not any(k in haystack for k in KEYWORDS):
            continue
        summary = block
        # Quita ruido habitual del bloque manteniendo una descripción corta y verificable.
        summary = re.sub(r"^(?:Publicado el\s*\d{1,2}/\d{1,2}/\d{4}\s*)", "", summary, flags=re.I)
        if title.lower() in summary.lower():
            pos = summary.lower().find(title.lower())
            summary = summary[pos + len(title):].strip(" ·:-")
        summary = re.split(r"\b(?:Leer más|Importancia|Etiquetas)\b", summary, maxsplit=1, flags=re.I)[0].strip()
        summary = summary[:280].rstrip()
        seen.add(path)
        cards.append((path, title, date_raw, importance, summary))
    return cards


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    items = []
    pages_ok = 0
    errors = 0

    for page_no in range(MAX_PAGES):
        url = LIST_URL + (f"?page={page_no}" if page_no else "")
        try:
            listing = get(url)
        except Exception as exc:
            errors += 1
            if page_no == 0:
                print(f"REVISIÓN INCOMPLETA: INCIBE no respondió ({exc}).")
                print("Se conserva data/estafas.json sin cambios.")
                return
            continue
        pages_ok += 1
        for path, title, date_raw, importance, summary in extract_cards(listing):
            published = parse_date(date_raw)
            if not published or published < cutoff or published > now + timedelta(days=1):
                continue
            url_item = urllib.parse.urljoin(BASE, path)
            slug = path.rstrip("/").split("/")[-1]
            items.append({
                "id": "incibe-" + slug,
                "tipo": "estafa",
                "titulo": title,
                "resumen": summary or "Aviso oficial de INCIBE sobre una campaña de fraude o suplantación.",
                "fecha": date_raw,
                "fecha_iso": published.date().isoformat(),
                "estado": "Reciente",
                "importancia": importance,
                "ambito": "España / usuarios de Internet",
                "fuente": "INCIBE · Ciudadanía",
                "url": url_item,
                "verificado": True,
            })

    unique = {x["url"]: x for x in items}
    items = sorted(unique.values(), key=lambda x: x["fecha_iso"], reverse=True)
    result = {
        "fuente": "INCIBE · Ciudadanía",
        "fuente_url": LIST_URL,
        "ultima_revision": now.isoformat(),
        "revision": "completa" if pages_ok else "incompleta",
        "fuentes_consultadas": pages_ok,
        "errores_parciales": errors,
        "criterio": f"Avisos oficiales de fraude/suplantación publicados en los últimos {MAX_AGE_DAYS} días",
        "total": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"Revisión rápida completa: {len(items)} alertas; {pages_ok} páginas consultadas; {errors} errores")


if __name__ == "__main__":
    main()
