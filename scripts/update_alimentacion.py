#!/usr/bin/env python3
"""Radar conservador de alertas alimentarias publicadas por AESAN."""
from __future__ import annotations
import html,json,re,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urljoin

OUT=Path('data/alimentacion.json')
BASE='https://www.aesan.gob.es'
UA='PanelCiudadano/1.0 (+GitHub Pages; radar ciudadano)'
SOURCES=[
 ('general','Interés para toda la población','https://www.aesan.gob.es/alertas/buscador-alertas?type=b5c27f12-7f21-4d2e-bc5c-d5186b4d6259'),
 ('alergenos','Alergias e intolerancias','https://www.aesan.gob.es/alertas/buscador-alertas?type=8c7503b4-b714-4c08-9d8e-0039a2d03624'),
 ('complementos','Complementos alimenticios','https://www.aesan.gob.es/alertas/buscador-alertas'),
]
MONTHS={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'})
 with urllib.request.urlopen(req,timeout=15) as r:return r.read().decode('utf-8',errors='replace')
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def iso_date(text):
 m=re.search(r'(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})',text,re.I)
 if not m:return ''
 return f'{int(m.group(3)):04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}'
def ref_of(title):
 m=re.search(r'(?:Ref\.?\s*:?[ ]*)(ES\s*\d{4}\s*/\s*\d+)',title,re.I)
 return re.sub(r'\s+','',m.group(1)).upper() if m else ''
def extract(page,kind,label):
 # Las fichas públicas de AESAN enlazan a /alertas/<slug>. Excluimos navegación y deduplicamos por URL.
 found=[];seen=set()
 for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']*/alertas/[^"\']+)["\'][^>]*>(.*?)</a>',page,re.I|re.S):
  href=urljoin(BASE,html.unescape(m.group(1)));text=clean(m.group(2))
  if not text or href in seen or 'buscador-alertas' in href:continue
  # La fecha suele estar en el bloque inmediatamente anterior al enlace.
  before=clean(page[max(0,m.start()-700):m.start()]);date=iso_date(before+' '+text)
  if not date:continue
  title=re.sub(r'^\d{1,2}\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4}\s*','',text,flags=re.I).strip()
  if len(title)<18:continue
  seen.add(href);ref=ref_of(title)
  found.append({'id':'aesan-'+(ref.lower().replace('/','-') if ref else re.sub(r'\W+','-',href.rsplit('/',1)[-1].lower()).strip('-')),'tipo':'alimentacion','categoria':kind,'categoria_nombre':label,'titulo':title,'fecha':date,'referencia':ref,'ambito':'España','fuente':'AESAN · Red de alerta alimentaria','url':href,'verificado':True})
 return found

def main():
 now=datetime.now(timezone.utc).isoformat();items=[];health=[]
 for kind,label,url in SOURCES:
  try:
   page=get(url);rows=extract(page,kind,label);health.append({'fuente':label,'estado':'ok','detectadas':len(rows)});items.extend(rows)
  except Exception as e:health.append({'fuente':label,'estado':'error','error':type(e).__name__})
 ok=[x for x in health if x['estado']=='ok']
 if not ok:
  print('AESAN no respondió: se conserva el fichero anterior.');return
 # Deduplicación: una ampliación con la misma referencia puede coexistir si tiene URL distinta; ID debe ser único.
 unique={}
 for x in items:
  key=x['url'];x['id']=x['id']+'-'+str(abs(hash(key))%1000000);unique[key]=x
 items=list(unique.values())
 cutoff=(datetime.now(timezone.utc)-timedelta(days=180)).date().isoformat();items=[x for x in items if x['fecha']>=cutoff]
 items.sort(key=lambda x:x['fecha'],reverse=True)
 result={'ultima_revision':now,'revision':'completa' if len(ok)==len(SOURCES) else 'parcial','fuente_principal':'Agencia Española de Seguridad Alimentaria y Nutrición (AESAN)','nota':'Se muestran publicaciones oficiales recientes. La presencia en este radar no permite inferir que una retirada siga activa; consulta la ficha oficial para las medidas vigentes.','salud_fuentes':health,'total':len(items),'items':items[:80]}
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);print(f'Alertas alimentarias: {len(result["items"])}; fuentes {len(ok)}/{len(SOURCES)}')
if __name__=='__main__':main()
