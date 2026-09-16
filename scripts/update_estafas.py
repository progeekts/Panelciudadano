#!/usr/bin/env python3
"""Actualiza el radar de estafas con avisos recientes y verificables de INCIBE.

El recolector tolera fallos temporales: reintenta peticiones, continúa si falla
una página secundaria y conserva el último dataset válido si no puede completar
una revisión mínima fiable. Nunca interpreta una fuente caída como cero alertas.
"""
from __future__ import annotations

import html
import json
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = "https://www.incibe.es"
# La página /ciudadania/avisos es el índice vigente; el antiguo tag /tags/aviso
# contiene principalmente avisos históricos y no sirve como radar de actualidad.
LIST_URL = BASE + "/ciudadania/avisos"
OUT = Path("data/estafas.json")
UA = "PanelCiudadano/1.2 (+GitHub Pages; fuente: INCIBE)"
MAX_AGE_DAYS = 120
MAX_PAGES = 5
MAX_DETAIL_PAGES = 50
RETRIES = 3
TIMEOUT = 20
KEYWORDS = ("fraude", "phishing", "smishing", "vishing", "suplant", "estafa", "fraudulent", "sextors")


def get(url: str) -> str:
    """Descarga una página con reintentos y backoff para fallos transitorios."""
    last_exc = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept-Language": "es-ES,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml",
                "Connection": "close",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt + 1 < RETRIES:
                time.sleep((2 ** attempt) + random.uniform(0.2, 0.8))
    raise RuntimeError(f"No se pudo consultar {url}: {last_exc}")


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
    patterns = (
        r"Fecha de publicación\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"Publicado el\s*(\d{1,2}/\d{1,2}/\d{4})",
    )
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        raw = m.group(1)
        try:
            return datetime.strptime(raw, "%d/%m/%Y").replace(tzinfo=timezone.utc), raw
        except ValueError:
            pass
    return None, ""


def extract_importance(text: str) -> str:
    m = re.search(r"Importancia\s*([1-5]\s*-\s*(?:Baja|Media|Alta|Crítica|Critica))", text, re.I)
    return m.group(1).strip() if m else ""


def previous_items():
    if not OUT.exists():
        return []
    try:
        old = json.loads(OUT.read_text(encoding="utf-8"))
        return old.get("items", []) if isinstance(old, dict) else []
    except Exception:
        return []


def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    paths = []
    list_ok = 0
    list_errors = []

    # La primera página es obligatoria: sin ella no podemos afirmar que la revisión sea actual.
    for page_no in range(MAX_PAGES):
        url = LIST_URL + (f"?page={page_no}" if page_no else "")
        try:
            listing = get(url)
            list_ok += 1
        except Exception as exc:
            list_errors.append(str(exc))
            if page_no == 0:
                print("REVISIÓN INCOMPLETA: no se pudo consultar el índice principal de INCIBE.")
                print("Se conserva data/estafas.json sin cambios.")
                return
            continue
        for p in re.findall(r'href=["\'](/ciudadania/avisos/[^"\'#?]+)', listing, re.I):
            if p not in paths:
                paths.append(p)

    if not paths:
        print("REVISIÓN INCOMPLETA: el índice respondió pero no se pudieron identificar avisos.")
        print("Se conserva data/estafas.json sin cambios.")
        return

    items = []
    detail_ok = 0
    detail_errors = 0
    for path in paths[:MAX_DETAIL_PAGES]:
        url = urllib.parse.urljoin(BASE, path)
        try:
            page = get(url)
            detail_ok += 1
        except Exception:
            detail_errors += 1
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

    # Si falló la mayoría de detalles, no convertimos una revisión parcial en un falso cero.
    attempted = detail_ok + detail_errors
    if attempted and detail_ok / attempted < 0.60:
        print(f"REVISIÓN INCOMPLETA: solo respondieron {detail_ok}/{attempted} avisos de INCIBE.")
        print("Se conserva data/estafas.json sin cambios.")
        return

    unique = {x["url"]: x for x in items}
    items = sorted(unique.values(), key=lambda x: x["fecha_iso"], reverse=True)
    result = {
        "fuente": "INCIBE · Ciudadanía",
        "fuente_url": LIST_URL,
        "ultima_revision": now.isoformat(),
        "revision": "completa",
        "fuentes_consultadas": list_ok,
        "avisos_consultados": detail_ok,
        "errores_parciales": len(list_errors) + detail_errors,
        "criterio": f"Avisos oficiales de fraude/suplantación publicados en los últimos {MAX_AGE_DAYS} días",
        "total": len(items),
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"Revisión completa: {len(items)} alertas recientes; {detail_errors} errores parciales")


if __name__ == "__main__":
    main()
