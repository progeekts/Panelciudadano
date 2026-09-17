#!/usr/bin/env python3
import hashlib,json,os,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone

URL='https://nap.dgt.es/datex2/v3/dgt/SituationPublication/all/content.xml'
OUT='data/movilidad.json'
UA='PanelCiudadano/1.0 (+GitHub Pages; fuente DGT NAP)'

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/xml,text/xml;q=0.9,*/*;q=0.5'})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read()

def lname(e):return e.tag.split('}')[-1]
def first(root,names):
    names=set(names)
    for e in root.iter():
        if lname(e) in names and (e.text or '').strip():return (e.text or '').strip()
    return None

def texts(root,names):
    names=set(names); out=[]
    for e in root.iter():
        if lname(e) in names and (e.text or '').strip():
            v=(e.text or '').strip()
            if v not in out:out.append(v)
    return out

def val_attr(root,names):
    names=set(names)
    for e in root.iter():
        if lname(e) in names:
            for k,v in e.attrib.items():
                if k.split('}')[-1] in ('value','id') and v:return v
    return None

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
    desc=first(target,['value','description','generalPublicComment','comment'])
    start=first(target,['overallStartTime','startOfPeriod','validityTimeSpecification'])
    end=first(target,['overallEndTime','endOfPeriod'])
    lat=first(target,['latitude']); lon=first(target,['longitude'])
    cause=first(target,['causeType','roadOrCarriagewayOrLaneManagementType','publicEventType','constructionWorkType','disturbanceActivityType','vehicleObstructionType','environmentalObstructionType','weatherRelatedRoadConditionType'])
    sev=first(target,['severity','probabilityOfOccurrence'])
    title='Incidencia de tráfico'
    if cause:title=f"{cause.replace('_',' ').capitalize()}"
    elif rtype:title=rtype.replace('SituationRecord','').replace('Record','') or title
    scope=' · '.join(x for x in (road,place) if x) or 'Red estatal de carreteras DGT'
    raw=sid or '|'.join(x or '' for x in (title,scope,start,lat,lon))
    uid='dgt-'+hashlib.sha1(raw.encode()).hexdigest()[:14]
    return {'id':uid,'tipo':'movilidad','titulo':title,'categoria':rtype,'carretera':road,'ambito':scope,'descripcion':desc,'inicio':start,'fin':end,'severidad_fuente':sev,'latitud':lat,'longitud':lon,'referencia':sid,'fuente':'Dirección General de Tráfico (DGT) · Punto de Acceso Nacional','url':'https://nap.dgt.es/es/dataset/incidencias-dgt-datex2-v3-7','verificado':True}

def main():
    now=datetime.now(timezone.utc).isoformat(); old={}
    if os.path.exists(OUT):
        try:old=json.load(open(OUT,encoding='utf-8'))
        except Exception:pass
    try:
        root=ET.fromstring(get(URL)); situations=[e for e in root.iter() if lname(e)=='situation']
        items=[]
        for s in situations:
            try:items.append(situation_item(s))
            except Exception:pass
        ded={x['id']:x for x in items};items=list(ded.values())
        data={'ultima_revision':now,'revision':'completa','fuente_principal':'Dirección General de Tráfico (DGT)','cobertura':'Red estatal de carreteras gestionada por DGT; la fuente oficial excluye Cataluña y País Vasco.','nota':'Incidencias publicadas por DGT en DATEX II. Panel Ciudadano no amplía la cobertura a territorios que la fuente no incluye ni infiere cierres o resolución fuera del estado publicado.','endpoint':URL,'total':len(items),'items':items}
    except Exception as e:
        if old:
            data=old;data['ultima_revision']=now;data['revision']='error';data['error_revision']=type(e).__name__;data['nota_revision']='No se pudo consultar DGT; se conservan los datos de la revisión anterior.'
        else:data={'ultima_revision':now,'revision':'error','fuente_principal':'Dirección General de Tráfico (DGT)','total':0,'items':[],'error_revision':type(e).__name__}
    os.makedirs('data',exist_ok=True)
    with open(OUT,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(f"DGT movilidad: revision={data.get('revision')} incidencias={data.get('total')}")
if __name__=='__main__':main()
