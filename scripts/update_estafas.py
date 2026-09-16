#!/usr/bin/env python3
"""Actualiza el radar de estafas con avisos recientes y verificables de INCIBE.

Solo publica avisos de fraude/suplantación con fecha válida dentro de la ventana
de actividad. Los avisos antiguos no se presentan como activos. Si no hay
resultados recientes, publica una lista vacía con la revisión actualizada.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "https://www.incibe.es"
LIST_URL = BASE + "/ciudadania/avisos"
OUT = Path("data/estafas.json")
UA = "PanelCiudadano/1.1 (+GitHub Pages; fuente: INCIBE)"
MAX_AGE_DAYS = 120
MAX_PAGES = 8
KEYWORDS = ("fraude", "phishing", "smishing", "vishing", "suplant", "estafa", "fraudulent")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(s: str) -> str:
    s = re.sub(r"<script\b[^>]*>.*?</script>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<style\b[^>]*>.*?</style>", " ", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def meta(page: str, prop: str) -> str:
    for p in (
        rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)',
        rf'<meta[^>]+name=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(prop)}["\']',
    ):
        m = re.search(p, page, re.I)
        if m:
            return clean(m.group(1))
    return ""


def parse_date(text: str):
    m = re.search(r"Fecha de publicación\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
    if not m:
        return None, ""
    raw = m.group(1)
    try:
        return datetime.strptime(raw, "%d/%m/%Y").replace(tzinfo=timezone.utc), raw
    except ValueError:
        return None, ""


def extract_importance(text: str) -> str:
    m = re.search(r"Importancia\s*([1-5]\s*-\s*(?:Baja|Media|Alta|Crítica|Critica))", text, re.I)
    return m.group(1).strip() if m else ""


def main():
    paths = []
    for page_no in range(MAX_PAGES):
        listing = get(LIST_URL + (f"?page={page_no}" if page_no else ""))
        for p in re.findall(r'href=["\'](/ciudadania/avisos/[^"\'#?]+)', listing, re.I):
            if p not in paths:
                paths.append(p)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    items = []
    for path in paths:
        url = urllib.parse.urljoin(BASE, path)
        try:
            page = get(url)
        except Exception:
            continue
        visible = clean(page)
        published, date_raw = parse_date(visible)
        if not published or published < cutoff or published > now + timedelta(days=1):
            continue
        title = meta(page, "og:title") or meta(page, "twitter:title")
        desc = meta(page, "description") or meta(page, "og:description")
        haystack = (title + " " + desc + " " + visible[:10000]).lower()
        if not any(k in haystack for k in KEYWORDS):
            continue
        slug = path.rstrip("/").split("/")[-1]
        items.append({
            "id": "incibe-" + slug,
            "tipo": "estafa",
            "titulo": title or slug.replace("-", " ").capitalize(),
            "resumen": desc,
            "fecha": date_raw,
            "fecha_iso": published.date().isoformat(),
            "estado": "Reciente",
            "importancia": extract_importance(visible),
            "ambito": "España / usuarios de Internet",
            "fuente": "INCIBE · Ciudadanía",
            "url": url,
            "verificado": True,
        })

    # Una misma alerta solo puede aparecer una vez y se muestran las más recientes primero.
    unique = {x["url"]: x for x in items}
    items = sorted(unique.values(), key=lambda x: x["fecha_iso"], reverse=True)
    result = {
        "fuente": "INCIBE · Ciudadanía",
        "fuente_url": LIST_URL,
        "ultima_revision": now.isoformat(),
        "criterio": f"Avisos oficiales de fraude/suplantación publicados en los últimos {MAX_AGE_DAYS} días",
        "total": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"Actualizadas {len(items)} alertas recientes de estafas")


if __name__ == "__main__":
    main()
