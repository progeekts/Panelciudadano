#!/usr/bin/env python3
import hashlib,json,os,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from datetime import datetime,timezone

DATASET='https://nap.dgt.es/es/dataset/incidencias-dgt-datex2-v3-7'
API='https://nap.dgt.es/api/3/action/package_show?id=incidencias-dgt-datex2-v3-7'
OUT='data/movilidad.json'
UA='PanelCiudadano/1.1 (+GitHub Pages; fuente DGT NAP)'

def get(url,accept='application/xml,text/xml;q=0.9,*/*;q=0.5'):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':accept})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read()

def lname(e):return e.tag.split('}')[-1]
def first(root,names):
    names=set(names)
    for e in root.iter():
        if lname(e) in names and (e.text or '').strip():return (e.text or '').strip()
    return None

def discover_endpoint():
    # El NAP es CKAN. No fijamos una ruta interna: obtenemos la URL publicada en los metadatos oficiales.
    meta=json.loads(get(API,'application/json').decode('utf-8'))
    if not meta.get('success'):raise RuntimeError('CKAN package_show sin éxito')
    resources=meta.get('result',{}).get('resources',[])
    candidates=[]
    for r in resources:
        fmt=(r.get('format') or '').lower(); name=(r.get('name') or '').lower(); url=(r.get('url') or '').strip()
        if not url:continue
        score=0
        if 'datex2' in fmt or 'datex' in fmt:score+=4
        if 'v3.7' in fmt or 'v37' in fmt or 'v37' in name:score+=3
        if name.endswith('.xml') or url.lower().endswith('.xml'):score+=2
        if 'xsd' in fmt or url.lower().endswith('.xsd'):score-=5
        if 'pdf' in fmt or url.lower().endswith('.pdf'):score-=5
        candidates.append((score,url,r.get('name') or r.get('format') or 'recurso'))
    candidates.sort(reverse=True)
    if not candidates or candidates[0][0] <= 0:raise RuntimeError('No se encontró recurso DATEX II XML')
    return candidates[0][1],candidates[0][2]

def situation_item(s):
    sid=s.attrib.get('id') or s.attrib.get('{http://www.w3.org/XML/1998/namespace}id') or first(s,['situationId'])
    records=[e for e in s.iter() if lname(e) in ('situationRecord','situationRecordReference')]
    target=records[0] if records else s
    rtype=None
    for e in target.iter():
        n=lname(e)
        if n.endswith('Record') and n not in ('situationRecord','situationRecordReference'):
            rtype=n;break
    road=first(target,['roadName','roadNumber','roadIdentifier'])
    place=first(target,['locationName','areaName','namedArea','localityName','municipality','administrativeArea'])
    desc=first(target,['description','generalPublicComment','comment','value'])
    start=first(target,['overallStartTime','startOfPeriod'])
    end=first(target,['overallEndTime','endOfPeriod'])
    lat=first(target,['latitude']); lon=first(target,['longitude'])
    cause=first(target,['causeType','roadOrCarriagewayOrLaneManagementType','publicEventType','constructionWorkType','disturbanceActivityType','vehicleObstructionType','environmentalObstructionType','weatherRelatedRoadConditionType','accidentType'])
    sev=first(target,['severity','probabilityOfOccurrence'])
    title=(cause or (rtype or '').replace('SituationRecord','').replace('Record','') or 'Incidencia de tráfico').replace('_',' ')
    title=title[:1].upper()+title[1:]
    scope=' · '.join(x for x in (road,place) if x) or 'Red estatal de carreteras DGT'
    raw=sid or '|'.join(x or '' for x in (title,scope,start,lat,lon))
    uid='dgt-'+hashlib.sha1(raw.encode()).hexdigest()[:14]
    return {'id':uid,'tipo':'movilidad','titulo':title,'categoria':rtype,'carretera':road,'ambito':scope,'descripcion':desc,'inicio':start,'fin':end,'severidad_fuente':sev,'latitud':lat,'longitud':lon,'referencia':sid,'fuente':'Dirección General de Tráfico (DGT) · Punto de Acceso Nacional','url':DATASET,'verificado':True}

def main():
    now=datetime.now(timezone.utc).isoformat(); old={}
    if os.path.exists(OUT):
        try:old=json.load(open(OUT,encoding='utf-8'))
        except Exception:pass
    try:
        endpoint,recurso=discover_endpoint()
        root=ET.fromstring(get(endpoint)); situations=[e for e in root.iter() if lname(e)=='situation']
        items=[]; errores=0
        for s in situations:
            try:items.append(situation_item(s))
            except Exception:errores+=1
        ded={x['id']:x for x in items};items=list(ded.values())
        data={'ultima_revision':now,'revision':'completa' if errores==0 else 'parcial','fuente_principal':'Dirección General de Tráfico (DGT)','cobertura':'Red estatal de carreteras gestionada por DGT; la fuente oficial excluye Cataluña y País Vasco.','nota':'Incidencias publicadas por DGT en DATEX II. El endpoint se descubre desde los metadatos oficiales del NAP para evitar depender de rutas internas. Panel Ciudadano no amplía la cobertura a territorios que la fuente no incluye.','dataset':DATASET,'recurso':recurso,'endpoint':endpoint,'situaciones_detectadas':len(situations),'errores_parseo':errores,'total':len(items),'items':items}
    except Exception as e:
        if old and old.get('items'):
            data=old;data['ultima_revision']=now;data['revision']='error';data['error_revision']=type(e).__name__;data['nota_revision']='No se pudo consultar DGT; se conservan los últimos datos válidos.'
        else:data={'ultima_revision':now,'revision':'error','fuente_principal':'Dirección General de Tráfico (DGT)','dataset':DATASET,'total':0,'items':[],'error_revision':type(e).__name__,'error_detalle':str(e)[:240]}
    os.makedirs('data',exist_ok=True)
    with open(OUT,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(f"DGT movilidad: revision={data.get('revision')} incidencias={data.get('total')} error={data.get('error_revision','-')}")
if __name__=='__main__':main()
