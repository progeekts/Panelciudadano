#!/usr/bin/env python3
"""Radar ciudadano de alertas sanitarias AEMPS.

Publica únicamente entradas que la propia AEMPS clasifica como alertas farmacéuticas,
seguridad de productos sanitarios o medicamentos ilegales. No interpreta consejo médico
ni infiere que una alerta continúe activa.
"""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

OUT=Path('data/salud.json')
UA='PanelCiudadano/1.0 (+GitHub Pages; radar ciudadano)'
SOURCES=[
 ('Alertas farmacéuticas','https://www.aemps.gob.es/category/informa/alertas/medicamentosusohumano-2/','farmaceutica'),
 ('Seguridad de productos sanitarios','https://www.aemps.gob.es/comunicacion/notas-de-seguridad/notas-informativas-de-seguridad-de-productos-sanitarios/','producto_sanitario'),
 ('Medicamentos ilegales','https://www.aemps.gob.es/category/informa/notasinformativas/medilegales-notasinformativas/2026-medilegales-notasinformativas/','medicamento_ilegal'),
]

def fetch(url):
    req=Request(url,headers={'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'})
    with urlopen(req,timeout=20) as r:return r.read().decode('utf-8','replace')

def text(s):
    s=re.sub(r'<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>',' ',s,flags=re.I|re.S)
    s=re.sub(r'<[^>]+>',' ',s);return re.sub(r'\s+',' ',unescape(s)).strip()

def iso_date(raw):
    months={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
    m=re.search(r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(20\d{2})',raw,re.I)
    if not m:return None
    mo=months.get(m.group(2).lower())
    return f'{m.group(3)}-{mo:02d}-{int(m.group(1)):02d}' if mo else None

def parse(html,source_name,category):
    items=[]
    # WordPress/AEMPS archive entries are article blocks; fallback to heading-to-heading chunks.
    blocks=re.findall(r'<article\b.*?</article>',html,re.I|re.S)
    if not blocks: blocks=re.split(r'(?=<h[23]\b)',html,flags=re.I)[1:]
    for b in blocks:
        link=re.search(r'<a\b[^>]*href=["\'](https://www\.aemps\.gob\.es/[^"\']+)["\'][^>]*>(.*?)</a>',b,re.I|re.S)
        if not link:continue
        title=text(link.group(2))
        body=text(b)
        if len(title)<8:continue
        date=iso_date(body)
        if not date:continue
        low=(title+' '+body).lower()
        # Keep only citizen-relevant safety/withdrawal notices; avoid general news accidentally present in archives.
        if category=='farmaceutica' and not (re.search(r'\bR[_ ]?\d+/20\d{2}\b',body,re.I) or 'alerta farmacéutica' in low):continue
        if category=='producto_sanitario' and not any(k in low for k in ('retirada','riesgo','fallo','seguridad','falsific')):continue
        if category=='medicamento_ilegal' and not any(k in low for k in ('retira','retirada','prohibición','medicamento ilegal')):continue
        url=link.group(1).rstrip('/')
        ident='aemps-'+hashlib.sha1(url.encode()).hexdigest()[:10]
        ref=''
        mr=re.search(r'(R[_ ]?\d+/20\d{2}|(?:PS|ICM)[^\s,;)]*\s*\d+/20\d{2})',body,re.I)
        if mr:ref=mr.group(1).strip()
        items.append({'id':ident,'tipo':'salud','categoria':category,'categoria_nombre':source_name,'titulo':title,'fecha':date,'referencia':ref,'ambito':'España','fuente':'Agencia Española de Medicamentos y Productos Sanitarios (AEMPS)','url':url,'verificado':True})
    return items

def main():
    old={}
    if OUT.exists():
        try:old=json.loads(OUT.read_text())
        except Exception:pass
    all_items=[];health=[]
    for name,url,cat in SOURCES:
        try:
            found=parse(fetch(url),name,cat)
            all_items.extend(found);health.append({'fuente':name,'estado':'ok','detectadas':len(found)})
        except Exception as e:
            health.append({'fuente':name,'estado':'error','detalle':type(e).__name__})
    ok=sum(x['estado']=='ok' for x in health)
    if ok==0:
        print('AEMPS: ninguna fuente respondió; se conservan datos anteriores')
        return
    unique={x['id']:x for x in all_items}
    items=sorted(unique.values(),key=lambda x:x['fecha'],reverse=True)[:60]
    # If some source failed, merge its previously verified items rather than silently losing them.
    if ok<len(SOURCES) and old.get('items'):
        for x in old['items']:
            unique.setdefault(x.get('id'),x)
        items=sorted(unique.values(),key=lambda x:x.get('fecha',''),reverse=True)[:60]
    data={'ultima_revision':datetime.now(timezone.utc).isoformat(),'revision':'completa' if ok==len(SOURCES) else 'parcial','fuente_principal':'Agencia Española de Medicamentos y Productos Sanitarios (AEMPS)','nota':'Avisos oficiales de seguridad y retirada. Panel Ciudadano no infiere que sigan activos ni sustituye las recomendaciones de la ficha oficial.','salud_fuentes':health,'total':len(items),'items':items}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(f'AEMPS: {len(items)} publicaciones; fuentes {ok}/{len(SOURCES)}')
if __name__=='__main__':main()
