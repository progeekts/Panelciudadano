#!/usr/bin/env python3
import hashlib,json,os,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
FEED='https://www.aemet.es/documentos_d/eltiempo/prediccion/avisos/rss/CAP_AFAE_RSS.xml';OUT='data/meteo.json';UA='PanelCiudadano/1.1 (+GitHub Pages; fuente AEMET)'
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.5'});return urllib.request.urlopen(req,timeout=20).read()
def local(root,name):
 for e in root.iter():
  if e.tag.split('}')[-1]==name:return (e.text or '').strip()
 return ''
def all_local(root,name):return [(e.text or '').strip() for e in root.iter() if e.tag.split('}')[-1]==name and (e.text or '').strip()]
def dt(v):
 if not v:return None
 try:return datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(timezone.utc)
 except Exception:return None
def cap_item(url,now):
 root=ET.fromstring(get(url));status=local(root,'status');msg=local(root,'msgType');severity=local(root,'severity')
 # Solo mensajes reales. Exercise/Test/Draft/System no deben llegar al ciudadano.
 if status.lower()!='actual':return None
 # Cancel cancela un aviso anterior y no es un aviso vigente por sí mismo.
 if msg.lower()=='cancel':return None
 if severity.lower() in ('minor','unknown',''):return None
 onset=local(root,'onset') or local(root,'effective');expires=local(root,'expires');end=dt(expires)
 if end and end<=now:return None
 event=local(root,'event') or 'Fenómeno meteorológico adverso';areas=all_local(root,'areaDesc');identifier=local(root,'identifier') or url
 sev={'moderate':'Amarillo','severe':'Naranja','extreme':'Rojo'}.get(severity.lower(),severity);scope=', '.join(dict.fromkeys(areas)) or 'España'
 return {'id':'aemet-'+hashlib.sha1(identifier.encode()).hexdigest()[:12],'tipo':'meteo','titulo':event,'nivel':sev,'severidad_cap':severity,'certeza':local(root,'certainty') or None,'ambito':scope,'inicio':onset or None,'fin':expires or None,'descripcion':local(root,'description') or None,'recomendacion':local(root,'instruction') or None,'referencia':identifier,'fuente':'Agencia Estatal de Meteorología (AEMET)','url':url,'verificado':True,'mensaje_cap':msg or None}
def main():
 nowdt=datetime.now(timezone.utc);now=nowdt.isoformat();old={}
 if os.path.exists(OUT):
  try:old=json.load(open(OUT,encoding='utf-8'))
  except Exception:pass
 try:
  root=ET.fromstring(get(FEED));links=[]
  for item in root.iter():
   if item.tag.split('}')[-1] not in ('item','entry'):continue
   for e in item.iter():
    if e.tag.split('}')[-1]=='link':
     u=(e.text or '').strip() or e.attrib.get('href','').strip()
     if u.endswith('.xml') and 'CAP_' in u:links.append(u.replace('http://','https://'))
  links=list(dict.fromkeys(links))
  # Un feed parseado sin enlaces CAP es ambiguo: no borrar silenciosamente avisos anteriores.
  if not links:raise ValueError('feed_sin_enlaces_cap')
  items=[];errors=0
  for u in links[:200]:
   try:
    x=cap_item(u,nowdt)
    if x:items.append(x)
   except Exception:errors+=1
  ded={x['id']:x for x in items};items=list(ded.values());order={'Rojo':3,'Naranja':2,'Amarillo':1};items.sort(key=lambda x:(order.get(x['nivel'],0),x.get('fin') or x.get('inicio') or ''),reverse=True)
  data={'ultima_revision':now,'revision':'completa' if errors==0 else 'parcial','fuente_principal':'Agencia Estatal de Meteorología (AEMET)','nota':'Avisos meteorológicos del canal oficial CAP. Solo mensajes Actual no cancelados, no expirados y con severidad Moderate, Severe o Extreme.','feed':FEED,'enlaces_cap_detectados':len(links),'errores_detalle':errors,'total':len(items),'items':items}
 except Exception as e:
  if old:data=old;data['ultima_revision']=now;data['revision']='error';data['error_revision']=type(e).__name__;data['nota_revision']='No se pudo validar la revisión AEMET; se conservan los datos anteriores.'
  else:data={'ultima_revision':now,'revision':'error','fuente_principal':'Agencia Estatal de Meteorología (AEMET)','total':0,'items':[],'error_revision':type(e).__name__}
 os.makedirs('data',exist_ok=True);json.dump(data,open(OUT,'w',encoding='utf-8'),ensure_ascii=False,indent=2);print(f"AEMET: revision={data.get('revision')} avisos={data.get('total')} CAP={data.get('enlaces_cap_detectados','?')}")
if __name__=='__main__':main()
