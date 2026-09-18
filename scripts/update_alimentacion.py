#!/usr/bin/env python3
"""Radar conservador de alertas alimentarias publicadas por AESAN."""
from __future__ import annotations
import hashlib,html,json,re,time,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urljoin
OUT=Path('data/alimentacion.json');BASE='https://www.aesan.gob.es';UA='PanelCiudadano/1.3 (+GitHub Pages; radar ciudadano)'
SOURCES=[('general','Interés para toda la población','https://www.aesan.gob.es/alertas/buscador-alertas?type=b5c27f12-7f21-4d2e-bc5c-d5186b4d6259'),('alergenos','Alergias e intolerancias','https://www.aesan.gob.es/alertas/buscador-alertas?type=8c7503b4-b714-4c08-9d8e-0039a2d03624')]
MONTHS={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12};DATE_RE=r'\d{1,2}\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4}'
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9'});return urllib.request.urlopen(req,timeout=15).read().decode('utf-8',errors='replace')
def detail(page):
 t=clean(re.sub(r'<script\\b[^>]*>.*?</script>|<style\\b[^>]*>.*?</style>',' ',page,flags=re.I|re.S))
 def pick(patterns,limit=1400):
  for p in patterns:
   m=re.search(p,t,re.I|re.S)
   if m:return re.sub(r'\\s+',' ',m.group(1)).strip()[:limit]
  return ''
 return {
  'producto':pick([r'(?:datos del producto|producto afectado|nombre del producto)\\s*[:.-]?\\s*(.*?)(?=\\s+(?:marca|lote|número de lote|peso|fecha|distribución|medidas|recomendaciones)\\b)'],700),
  'lotes':pick([r'(?:lotes? afectados?|número de lote)\\s*[:.-]?\\s*(.*?)(?=\\s+(?:fecha|caducidad|consumo preferente|distribución|medidas|recomendaciones)\\b)'],900),
  'distribucion':pick([r'(?:distribución|distribuido)\\s*[:.-]?\\s*(.*?)(?=\\s+(?:medidas|recomendaciones|información|como medida)\\b)'],1200),
  'medidas':pick([r'(?:medidas adoptadas|medidas|recomendaciones)\\s*[:.-]?\\s*(.*?)(?=\\s+(?:información adicional|fuente|fecha)\\b|$)'],1600)
 }
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def iso_date(t):
 m=re.search(r'(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{4})',t,re.I);return f'{int(m.group(3)):04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}' if m else ''
def ref_of(t):
 m=re.search(r'Ref\.?\s*:?[ ]*(ES\s*\d{4}\s*/\s*\d+)',t,re.I);return re.sub(r'\s+','',m.group(1)).upper() if m else ''
def revision_key(x):
 ref=(x.get('referencia') or '').strip().upper()
 if ref:return ref
 title=(x.get('titulo') or '').lower()
 title=re.sub(r'^(?:ampliación|actualización|ampliacion|actualizacion)\s+de\s+información\s+sobre\s+','',title)
 return re.sub(r'\W+',' ',title).strip()[:120]
def revision_rank(x):
 title=(x.get('titulo') or '').lower()
 return (1 if any(k in title for k in ('ampliación','actualización','ampliacion','actualizacion')) else 0,x.get('fecha',''),x.get('url',''))
def tidy(t):return re.sub(r'\s+Ver\s+m[aá]s\s*$','',re.sub(r'^'+DATE_RE+r'\s*','',re.sub(r'^(?:cookie|error_outline)\s+','',t,flags=re.I),flags=re.I),flags=re.I).strip()
def extract(page,kind,label):
 found=[];seen=set()
 for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']*/alertas/[^"\']+)["\'][^>]*>(.*?)</a>',page,re.I|re.S):
  href=urljoin(BASE,html.unescape(m.group(1)));raw=clean(m.group(2))
  if not raw or href in seen or 'buscador-alertas' in href:continue
  date=iso_date(raw)
  if not date:continue
  title=tidy(raw)
  if len(title)<18:continue
  info={}
  try:time.sleep(.2);info=detail(get(href))
  except Exception:pass
  seen.add(href);found.append({'id':'aesan-'+hashlib.sha1(href.encode()).hexdigest()[:10],'tipo':'alimentacion','categoria':kind,'categoria_nombre':label,'titulo':title,'fecha':date,'referencia':ref_of(title),'producto':info.get('producto',''),'lotes':info.get('lotes',''),'distribucion':info.get('distribucion',''),'medidas':info.get('medidas',''),'ambito':'España','fuente':'AESAN · Red de alerta alimentaria','url':href,'verificado':True})
 return found
def main():
 now=datetime.now(timezone.utc).isoformat();old={}
 if OUT.exists():
  try:old=json.loads(OUT.read_text(encoding='utf-8'))
  except Exception:pass
 items=[];health=[];failed_categories=set()
 for kind,label,url in SOURCES:
  try:
   page=get(url);rows=extract(page,kind,label)
   # Una categoría que antes tenía datos y de pronto produce cero se trata como parser dudoso, no como desaparición masiva.
   had_old=any(x.get('categoria')==kind for x in old.get('items',[]))
   if not rows and had_old:health.append({'fuente':label,'estado':'error','error':'parser_sin_resultados'});failed_categories.add(kind);continue
   health.append({'fuente':label,'estado':'ok','detectadas':len(rows)});items.extend(rows)
  except Exception as e:health.append({'fuente':label,'estado':'error','error':type(e).__name__});failed_categories.add(kind)
 ok=[x for x in health if x['estado']=='ok']
 if not ok:print('AESAN: ninguna categoría pudo validarse; se conserva el fichero anterior.');return
 # Mantener únicamente los datos previos de categorías cuya revisión falló.
 for x in old.get('items',[]):
  if x.get('categoria') in failed_categories:items.append(x)
 unique={x['url']:x for x in items}
 # Una ampliación/actualización con la misma referencia oficial sustituye a la ficha anterior en el panel actual.
 grouped={}
 for x in unique.values():
  k=revision_key(x);cur=grouped.get(k)
  if not cur or revision_rank(x)>revision_rank(cur):grouped[k]=x
 items=list(grouped.values());cutoff=(datetime.now(timezone.utc)-timedelta(days=180)).date().isoformat();items=[x for x in unique.values() if x.get('fecha','')>=cutoff];items.sort(key=lambda x:x.get('fecha',''),reverse=True)
 result={'ultima_revision':now,'revision':'completa' if len(ok)==len(SOURCES) else 'parcial','fuente_principal':'Agencia Española de Seguridad Alimentaria y Nutrición (AESAN)','cobertura':['Alertas de interés para toda la población','Alertas para personas con alergias o intolerancias'],'nota':'Publicaciones oficiales recientes. Cuando AESAN publica una ampliación con la misma referencia, el panel muestra la versión más reciente. No se infiere una retirada o finalización sin evidencia oficial.','salud_fuentes':health,'detalle_enriquecido':sum(1 for x in items if x.get('producto') or x.get('lotes') or x.get('distribucion') or x.get('medidas')),'total':len(items[:80]),'items':items[:80]}
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);print(f'AESAN: publicaciones={result["total"]}; fuentes={len(ok)}/{len(SOURCES)}; revision={result["revision"]}')
if __name__=='__main__':main()
