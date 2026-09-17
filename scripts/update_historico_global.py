#!/usr/bin/env python3
"""Construye un histórico común sin inferir resoluciones que las fuentes no acreditan."""
from __future__ import annotations
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
OUT=Path('data/historico_global.json'); TYPES=('ayudas','estafas','alimentacion','salud','meteo')

def load(path,default):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:return default

def fingerprint(x):
    fields=('titulo','estado_plazo','nivel','inicio','fin','fecha','fecha_registro','url','referencia')
    return hashlib.sha256('|'.join(str(x.get(k,'')) for k in fields).encode()).hexdigest()[:20]

def source_time(t,x):
    for k in ('fecha','fecha_registro','inicio','publicado'):
        if x.get(k):return str(x[k])
    return ''

def state(t,x):
    if t=='ayudas':return {'Abierta':'plazo_abierto','Próxima':'plazo_proximo','Finalizada':'plazo_finalizado'}.get(x.get('estado_plazo'),'publicada')
    if t=='meteo':return 'aviso_vigente' # el parser CAP solo publica Actual/no cancelado/no expirado
    return 'publicada'

def label(s):return {'publicada':'Publicada','plazo_abierto':'Plazo abierto','plazo_proximo':'Próxima','plazo_finalizado':'Plazo finalizado','aviso_vigente':'Aviso vigente','expirado_detectado':'Dejó de estar vigente','solucionado':'Solucionado','retirado_monitor':'Retirado del monitor'}.get(s,s)

def main():
    now=datetime.now(timezone.utc).isoformat(); old=load(OUT,{'registros':[]}); prev={r.get('clave'):r for r in old.get('registros',[]) if r.get('clave')}; current={}; events=[]
    for t in TYPES:
        data=load(f'data/{t}.json',{})
        # No actualizamos ausencia si la revisión declara error.
        valid=data.get('revision','completa') not in ('error',)
        for x in data.get('items',[]) if valid else []:
            ident=str(x.get('id') or x.get('codigo_bdns') or x.get('url') or '').strip()
            if not ident:continue
            k=f'{t}:{ident}'; fp=fingerprint(x); st=state(t,x); before=prev.get(k)
            rec=dict(before or {},clave=k,tipo=t,id=ident,titulo=x.get('titulo',''),fuente=x.get('fuente',data.get('fuente','')),url=x.get('url',''),ambito=x.get('ambito') or x.get('region_impacto') or 'España',estado=st,huella=fp,ultima_deteccion=now,fecha_fuente=source_time(t,x))
            if not before:
                rec['primera_deteccion']=now;events.append({'clave':k,'tipo':t,'evento':st if t in ('ayudas','meteo') else 'publicada','etiqueta':label(st if t in ('ayudas','meteo') else 'publicada'),'momento_detectado':now,'fecha_fuente':rec['fecha_fuente'],'titulo':rec['titulo'],'url':rec['url']})
            elif before.get('huella')!=fp or before.get('estado')!=st:
                rec['ultima_modificacion_detectada']=now;events.append({'clave':k,'tipo':t,'evento':st,'etiqueta':label(st),'momento_detectado':now,'fecha_fuente':rec['fecha_fuente'],'titulo':rec['titulo'],'url':rec['url']})
            current[k]=rec
    # Ausencias: solo AEMET permite concluir aquí que el aviso ya no está en el conjunto vigente,
    # y aun así lo expresamos como "dejó de estar vigente", no como cancelado.
    meteo=load('data/meteo.json',{});meteo_valid=meteo.get('revision') not in ('error','parcial')
    for k,r in prev.items():
        if k in current:continue
        if r.get('tipo')=='meteo' and meteo_valid and r.get('estado')=='aviso_vigente':
            r=dict(r);r['estado']='expirado_detectado';r['fin_deteccion']=now;current[k]=r;events.append({'clave':k,'tipo':'meteo','evento':'expirado_detectado','etiqueta':label('expirado_detectado'),'momento_detectado':now,'fecha_fuente':'','titulo':r.get('titulo',''),'url':r.get('url','')})
        else:current[k]=r
    # Integra el histórico especializado de servicios, que sí dispone de semántica propia.
    hs=load('data/historico_servicios.json',{})
    for x in hs.get('items',[]):
        ident=str(x.get('id',''));k=f'servicios:{ident}';st={'resuelto':'solucionado','retirado':'retirado_monitor'}.get(x.get('estado_historico'),'incidencia_activa');tm=x.get('resuelto_detectado') or x.get('retirado_detectado') or x.get('ultima_modificacion_detectada') or x.get('primera_deteccion') or now
        current[k]={'clave':k,'tipo':'servicios','id':ident,'titulo':x.get('titulo',''),'fuente':x.get('servicio',''),'url':x.get('url',''),'ambito':x.get('ambito',''),'estado':st,'primera_deteccion':x.get('primera_deteccion',tm),'ultima_deteccion':x.get('ultima_deteccion',tm),'fin_deteccion':x.get('resuelto_detectado') or x.get('retirado_detectado','')}
    oldevents=old.get('eventos',[]);seen={(e.get('clave'),e.get('evento'),e.get('momento_detectado')) for e in oldevents};events=[e for e in events if (e.get('clave'),e.get('evento'),e.get('momento_detectado')) not in seen]+oldevents
    result={'ultima_revision':now,'criterio':'Histórico de detecciones. La desaparición solo genera estado terminal cuando el módulo permite afirmarlo de forma conservadora.','total_registros':len(current),'total_eventos':len(events[:1000]),'registros':list(current.values()),'eventos':events[:1000]};OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
