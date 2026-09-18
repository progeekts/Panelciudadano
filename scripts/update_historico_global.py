#!/usr/bin/env python3
"""Histórico común: registra publicaciones, cambios verificables y estados terminales conservadores."""
from __future__ import annotations
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
OUT=Path('data/historico_global.json'); TYPES=('ayudas','estafas','alimentacion','salud','meteo')

def load(path,default):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:return default

def fingerprint(x):
    # Campos que pueden cambiar el significado visible de una ficha.
    fields=('titulo','estado_plazo','estado','nivel','severidad_cap','inicio','fin','fecha','fecha_registro',
            'resumen','descripcion','recomendacion','ambito','region_impacto','beneficiarios','presupuesto',
            'url','referencia','mensaje_cap','categoria','categoria_nombre')
    raw='|'.join(f'{k}={x.get(k,"")}' for k in fields)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def source_time(t,x):
    for k in ('actualizado','fecha','fecha_registro','inicio','publicado'):
        if x.get(k):return str(x[k])
    return ''

def state(t,x):
    if t=='ayudas':return {'Abierta':'plazo_abierto','Próxima':'plazo_proximo','Finalizada':'plazo_finalizado'}.get(x.get('estado_plazo'),'convocatoria_detectada')
    if t=='meteo':return 'aviso_vigente'
    return 'publicada'

def label(s):return {'publicada':'Publicada','actualizado':'Actualizada','convocatoria_detectada':'Convocatoria detectada',
 'plazo_abierto':'Plazo abierto','plazo_proximo':'Próxima','plazo_finalizado':'Plazo finalizado',
 'aviso_vigente':'Aviso vigente','incidencia_activa':'Incidencia activa','expirado_detectado':'Dejó de estar vigente',
 'solucionado':'Solucionada','retirado_monitor':'Retirada del monitor'}.get(s,s)

def event(k,t,kind,now,rec,detail=''):
    e={'clave':k,'tipo':t,'evento':kind,'etiqueta':label(kind),'momento_detectado':now,
       'fecha_fuente':rec.get('fecha_fuente',''),'titulo':rec.get('titulo',''),'url':rec.get('url','')}
    if detail:e['detalle_cambio']=detail
    return e

def main():
    now=datetime.now(timezone.utc).isoformat(); old=load(OUT,{'registros':[]})
    prev={r.get('clave'):r for r in old.get('registros',[]) if r.get('clave')}; current={}; events=[]
    revisions={}
    for t in TYPES:
        data=load(f'data/{t}.json',{})
        revisions[t]=data.get('ultima_revision','')
        valid=data.get('revision','completa') not in ('error',)
        for x in data.get('items',[]) if valid else []:
            ident=str(x.get('id') or x.get('codigo_bdns') or x.get('url') or '').strip()
            if not ident:continue
            k=f'{t}:{ident}'; fp=fingerprint(x); st=state(t,x); before=prev.get(k)
            rec=dict(before or {},clave=k,tipo=t,id=ident,titulo=x.get('titulo',''),fuente=x.get('fuente',data.get('fuente','')),
                     url=x.get('url',''),ambito=x.get('ambito') or x.get('region_impacto') or '',estado=st,huella=fp,
                     ultima_deteccion=now,fecha_fuente=source_time(t,x))
            if not before:
                rec['primera_deteccion']=now
                events.append(event(k,t,st if t in ('ayudas','meteo') else 'publicada',now,rec))
            elif before.get('huella')!=fp or before.get('estado')!=st:
                rec['ultima_modificacion_detectada']=now
                if before.get('estado')!=st:
                    kind=st; detail=f'Estado: {label(before.get("estado",""))} → {label(st)}'
                else:
                    kind='actualizado'; detail='La ficha oficial presenta cambios respecto a la revisión anterior'
                events.append(event(k,t,kind,now,rec,detail))
            elif before:
                rec['ultima_deteccion']=before.get('ultima_deteccion',before.get('primera_deteccion',now))
            current[k]=rec

    meteo=load('data/meteo.json',{}); meteo_valid=meteo.get('revision') not in ('error','parcial')
    for k,r0 in prev.items():
        if k in current or r0.get('tipo')=='servicios':continue
        r=dict(r0)
        if r.get('tipo')=='meteo' and meteo_valid and r.get('estado')=='aviso_vigente':
            r['estado']='expirado_detectado';r['fin_deteccion']=now;r['ultima_modificacion_detectada']=now
            current[k]=r;events.append(event(k,'meteo','expirado_detectado',now,r,'Ya no figura en el conjunto vigente validado por el módulo AEMET'))
        else:current[k]=r

    # Servicios dispone de histórico especializado y timestamps propios.
    hs=load('data/historico_servicios.json',{}); revisions['servicios']=hs.get('ultima_revision','')
    for x in hs.get('items',[]):
        ident=str(x.get('id','')); k=f'servicios:{ident}'
        st={'resuelto':'solucionado','retirado':'retirado_monitor'}.get(x.get('estado_historico'),'incidencia_activa')
        tm=x.get('ultima_deteccion') or x.get('primera_deteccion') or now
        rec={'clave':k,'tipo':'servicios','id':ident,'titulo':x.get('titulo',''),'fuente':x.get('servicio',''),
             'url':x.get('url',''),'ambito':x.get('ambito',''),'estado':st,'primera_deteccion':x.get('primera_deteccion',tm),
             'ultima_deteccion':tm,'ultima_modificacion_detectada':x.get('ultima_modificacion_detectada',''),
             'fin_deteccion':x.get('resuelto_detectado') or x.get('retirado_detectado',''),'fecha_fuente':''}
        before=prev.get(k)
        if before and before.get('estado')==st and before.get('fin_deteccion','')==rec.get('fin_deteccion','') and before.get('ultima_modificacion_detectada','')==rec.get('ultima_modificacion_detectada',''):
            rec=before
        current[k]=rec
        # Importa eventos con sus tiempos reales; la deduplicación posterior evita repetirlos.
        if x.get('primera_deteccion'):events.append(event(k,'servicios','incidencia_activa',x['primera_deteccion'],rec))
        if x.get('ultima_modificacion_detectada') and x.get('ultima_modificacion_detectada')!=x.get('primera_deteccion'):
            events.append(event(k,'servicios','actualizado',x['ultima_modificacion_detectada'],rec,'La incidencia cambió en la fuente oficial'))
        if x.get('resuelto_detectado'):events.append(event(k,'servicios','solucionado',x['resuelto_detectado'],rec))
        if x.get('retirado_detectado'):events.append(event(k,'servicios','retirado_monitor',x['retirado_detectado'],rec))

    oldevents=old.get('eventos',[])
    # Dedupe por identidad+evento+momento: estable incluso al reimportar servicios.
    merged=events+oldevents; seen=set(); unique=[]
    for e in sorted(merged,key=lambda z:z.get('momento_detectado',''),reverse=True):
        sig=(e.get('clave'),e.get('evento'),e.get('momento_detectado'))
        if sig in seen:continue
        seen.add(sig);unique.append(e)

    semantic_changed=bool(events) or set(current)!=set(prev) or any((prev.get(k,{}).get('estado'),prev.get(k,{}).get('huella'),prev.get(k,{}).get('fin_deteccion'))!=(v.get('estado'),v.get('huella'),v.get('fin_deteccion')) for k,v in current.items())
    if not semantic_changed and OUT.exists():
        return
    result={'ultima_revision':now,'fuentes_revision':revisions,
      'criterio':'Histórico de cambios detectados. Solo se asigna un estado terminal cuando la fuente o el módulo permiten afirmarlo de forma conservadora.',
      'total_registros':len(current),'total_eventos':len(unique[:1000]),'registros':list(current.values()),'eventos':unique[:1000]}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
