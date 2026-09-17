#!/usr/bin/env python3
import hashlib,json,os,re,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone

FEED='https://www.aemet.es/documentos_d/eltiempo/prediccion/avisos/rss/CAP_AFAE_RSS.xml'
OUT='data/meteo.json'
UA='PanelCiudadano/1.0 (+GitHub Pages; fuente AEMET)'

def text(el,name):
    x=el.find(name)
    return (x.text or '').strip() if x is not None else ''

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.5'})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()

def local(root,name):
    for e in root.iter():
        if e.tag.split('}')[-1]==name:return (e.text or '').strip()
    return ''

def all_local(root,name):
    return [(e.text or '').strip() for e in root.iter() if e.tag.split('}')[-1]==name and (e.text or '').strip()]

def cap_item(url):
    root=ET.fromstring(get(url))
    status=local(root,'status'); msg=local(root,'msgType'); severity=local(root,'severity')
    if status and status.lower() not in ('actual','exercise'): return None
    # CAP de AEMET usa Minor también para mensajes sin aviso: no publicarlos.
    if severity.lower() in ('minor','unknown',''): return None
    event=local(root,'event') or 'Fenómeno meteorológico adverso'
    areas=all_local(root,'areaDesc')
    onset=local(root,'onset') or local(root,'effective')
    expires=local(root,'expires')
    certainty=local(root,'certainty')
    desc=local(root,'description')
    instruction=local(root,'instruction')
    identifier=local(root,'identifier') or url
    sev={'moderate':'Amarillo','severe':'Naranja','extreme':'Rojo'}.get(severity.lower(),severity)
    scope=', '.join(dict.fromkeys(areas)) or 'España'
    uid='aemet-'+hashlib.sha1(identifier.encode()).hexdigest()[:12]
    return {'id':uid,'tipo':'meteo','titulo':event,'nivel':sev,'severidad_cap':severity,'certeza':certainty or None,'ambito':scope,'inicio':onset or None,'fin':expires or None,'descripcion':desc or None,'recomendacion':instruction or None,'referencia':identifier,'fuente':'Agencia Estatal de Meteorología (AEMET)','url':url,'verificado':True,'mensaje_cap':msg or None}

def main():
    now=datetime.now(timezone.utc).isoformat()
    old={}
    if os.path.exists(OUT):
        try: old=json.load(open(OUT,encoding='utf-8'))
        except Exception: pass
    try:
        root=ET.fromstring(get(FEED))
        links=[]
        for item in root.iter():
            if item.tag.split('}')[-1] not in ('item','entry'):continue
            for e in item.iter():
                tag=e.tag.split('}')[-1]
                if tag=='link':
                    u=(e.text or '').strip() or e.attrib.get('href','').strip()
                    if u.endswith('.xml') and 'CAP_' in u:links.append(u.replace('http://','https://'))
        links=list(dict.fromkeys(links))
        items=[]; errors=0
        for u in links[:160]:
            try:
                x=cap_item(u)
                if x:items.append(x)
            except Exception: errors+=1
        # Dedupe and sort by severity then end/start. Feed represents current state, so zero alerts is valid if feed was parsed.
        ded={x['id']:x for x in items};items=list(ded.values())
        order={'Rojo':3,'Naranja':2,'Amarillo':1}
        items.sort(key=lambda x:(order.get(x['nivel'],0),x.get('fin') or x.get('inicio') or ''),reverse=True)
        data={'ultima_revision':now,'revision':'completa' if errors==0 else 'parcial','fuente_principal':'Agencia Estatal de Meteorología (AEMET)','nota':'Estado de avisos meteorológicos adversos obtenido del canal oficial CAP. Solo se publican avisos CAP con severidad Moderate, Severe o Extreme; los mensajes Minor sin aviso se excluyen.','feed':FEED,'enlaces_cap_detectados':len(links),'errores_detalle':errors,'total':len(items),'items':items}
    except Exception as e:
        if old:
            data=old;data['ultima_revision']=now;data['revision']='error';data['error_revision']=type(e).__name__;data['nota_revision']='No se pudo consultar AEMET; se conservan los datos de la revisión anterior.'
        else:
            data={'ultima_revision':now,'revision':'error','fuente_principal':'Agencia Estatal de Meteorología (AEMET)','total':0,'items':[],'error_revision':type(e).__name__}
    os.makedirs('data',exist_ok=True)
    with open(OUT,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(f"AEMET: revision={data.get('revision')} avisos={data.get('total')} CAP={data.get('enlaces_cap_detectados','?')}")

if __name__=='__main__':main()
