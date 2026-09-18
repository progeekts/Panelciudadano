#!/usr/bin/env python3
"""Radar conservador de avisos oficiales de fraude de INCIBE."""
from __future__ import annotations
import html,json,re,urllib.parse,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
BASE='https://www.incibe.es';LIST_URL=BASE+'/ciudadania/avisos';OUT=Path('data/estafas.json');UA='PanelCiudadano/1.4 (+GitHub Pages; fuente: INCIBE)';MAX_AGE_DAYS=120;MAX_PAGES=3;TIMEOUT=12
KEYWORDS=('fraude','phishing','smishing','vishing','suplant','estafa','fraudulent','sextors')
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'es-ES,es;q=0.9','Accept':'text/html,application/xhtml+xml','Connection':'close'})
 with urllib.request.urlopen(req,timeout=TIMEOUT) as r:return r.read().decode('utf-8',errors='replace')
def clean(s):
 s=re.sub(r'<script\b[^>]*>.*?</script>',' ',s,flags=re.I|re.S);s=re.sub(r'<style\b[^>]*>.*?</style>',' ',s,flags=re.I|re.S);s=re.sub(r'<[^>]+>',' ',s);return re.sub(r'\s+',' ',html.unescape(s)).strip()
def parse_date(raw):
 try:return datetime.strptime(raw,'%d/%m/%Y').replace(tzinfo=timezone.utc)
 except (ValueError,TypeError):return None
def extract_cards(page):
 links=list(re.finditer(r'<a[^>]+href=["\'](/ciudadania/avisos/[^"\'#?]+)["\'][^>]*>(.*?)</a>',page,re.I|re.S));cards=[];seen=set()
 for i,m in enumerate(links):
  path=m.group(1)
  if path in seen:continue
  title=clean(m.group(2))
  if not title or len(title)<8:continue
  start=max(0,m.start()-500);end=min(len(page),(links[i+1].start() if i+1<len(links) else m.end()+1800));block=clean(page[start:end]);dm=re.search(r'(?:Publicado el|Fecha de publicación)\s*(\d{1,2}/\d{1,2}/\d{4})',block,re.I)
  if not dm:continue
  importance='';im=re.search(r'Importancia\s*([1-5]\s*-\s*(?:Baja|Media|Alta|Crítica|Critica))',block,re.I)
  if im:importance=im.group(1).strip()
  if not any(k in (title+' '+block).lower() for k in KEYWORDS):continue
  summary=re.sub(r'^(?:Publicado el\s*\d{1,2}/\d{1,2}/\d{4}\s*)','',block,flags=re.I)
  if title.lower() in summary.lower():summary=summary[summary.lower().find(title.lower())+len(title):].strip(' ·:-')
  summary=re.split(r'\b(?:Leer más|Importancia|Etiquetas)\b',summary,maxsplit=1,flags=re.I)[0].strip()[:280].rstrip();seen.add(path);cards.append((path,title,dm.group(1),importance,summary))
 return cards
def preserve(now,reason):
 try:data=json.loads(OUT.read_text(encoding='utf-8'))
 except Exception:data={'fuente':'INCIBE · Ciudadanía','fuente_url':LIST_URL,'total':0,'items':[]}
 data['ultima_revision']=now.isoformat();data['revision']='error';data['nota_revision']='No se pudo validar la revisión de INCIBE; se conservan los últimos datos válidos.';data['error_revision']=reason
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT)
def detail_info(page):
 t=clean(page)
 def grab(label,next_labels):
  nxt='|'.join(re.escape(x) for x in next_labels)
  m=re.search(re.escape(label)+r'\\s+(.+?)(?=\\s+(?:'+nxt+r')\\s+|$)',t,re.I)
  return m.group(1).strip() if m else ''
 return {
  'identificador':grab('Identificador',['Importancia','Recursos Afectados','Descripción']),
  'importancia':grab('Importancia',['Recursos Afectados','Descripción']),
  'afectados':grab('Recursos Afectados',['Descripción','Solución','Detalle'])[:700],
  'descripcion':grab('Descripción',['Solución','Detalle'])[:1400],
  'solucion':grab('Solución',['Detalle'])[:1800],
 }
def detail_state(page):
 t=clean(page).lower()
 # Solo estados explícitos en la propia ficha; ausencia de estas frases no implica finalización.
 if re.search(r'campaña (?:ha sido |está |se encuentra )?(?:finalizada|finalizado|cerrada|cesada)',t):return 'Finalizada'
 if re.search(r'(?:campaña|fraude|smishing|phishing) (?:sigue|continúa|permanece) activ',t):return 'Activa'
 return ''
def main():
 now=datetime.now(timezone.utc);cutoff=now-timedelta(days=MAX_AGE_DAYS);items=[];pages_ok=0;errors=0;cards_seen=0
 for page_no in range(MAX_PAGES):
  url=LIST_URL+(f'?page={page_no}' if page_no else '')
  try:listing=get(url);cards=extract_cards(listing)
  except Exception as exc:
   errors+=1
   if page_no==0:preserve(now,type(exc).__name__);print('INCIBE: revisión no validada; datos anteriores conservados.');return
   continue
  pages_ok+=1;cards_seen+=len(cards)
  for path,title,date_raw,importance,summary in cards:
   published=parse_date(date_raw)
   if not published or published<cutoff or published>now+timedelta(days=1):continue
   url_item=urllib.parse.urljoin(BASE,path);slug=path.rstrip('/').split('/')[-1];explicit='';info={}
   try:
    detail_page=get(url_item);explicit=detail_state(detail_page);info=detail_info(detail_page)
   except Exception:pass
   items.append({'id':'incibe-'+slug,'tipo':'estafa','titulo':title,'resumen':info.get('descripcion') or summary or 'Aviso oficial de INCIBE sobre una campaña de fraude o suplantación.','descripcion':info.get('descripcion',''),'afectados':info.get('afectados',''),'solucion':info.get('solucion',''),'identificador_incibe':info.get('identificador',''),'fecha':date_raw,'fecha_iso':published.date().isoformat(),'estado':explicit or 'Publicada','importancia':info.get('importancia') or importance,'ambito':'España / usuarios de Internet','fuente':'INCIBE · Ciudadanía','url':url_item,'verificado':True})
 # Si el parser deja de reconocer por completo una portada accesible, no convertirlo en "cero alertas".
 if pages_ok and cards_seen==0:preserve(now,'parser_sin_resultados');print('INCIBE: posible cambio de formato; datos anteriores conservados.');return
 unique={x['url']:x for x in items};items=sorted(unique.values(),key=lambda x:x['fecha_iso'],reverse=True);revision='completa' if pages_ok==MAX_PAGES and errors==0 else 'parcial'
 result={'fuente':'INCIBE · Ciudadanía','fuente_url':LIST_URL,'ultima_revision':now.isoformat(),'revision':revision,'paginas_previstas':MAX_PAGES,'fuentes_consultadas':pages_ok,'errores_parciales':errors,'criterio':f'Avisos oficiales de fraude/suplantación publicados en los últimos {MAX_AGE_DAYS} días','nota_estado':'“Publicada” indica que INCIBE mantiene una ficha oficial reciente. Solo se muestra “Activa” o “Finalizada” cuando la propia ficha contiene una indicación explícita que el detector puede validar.','total':len(items),'items':items}
 OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(OUT);print(f'INCIBE: revision={revision}; alertas={len(items)}; paginas={pages_ok}/{MAX_PAGES}; errores={errors}')
if __name__=='__main__':main()
