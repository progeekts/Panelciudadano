# Panel Ciudadano

Panel público pensado para reunir información de utilidad cotidiana en España y mostrarla de forma clara y rápida.

## Módulos

- Ayudas y subvenciones
- Estafas activas
- Incidencias de servicios digitales
- Alimentación
- Salud
- Meteorología
- Movilidad
- Histórico global

La portada prioriza la lectura de un vistazo. Cada ficha puede abrirse para consultar contexto adicional y la fuente original.

## Principios

1. No presentar rumores como hechos.
2. Mantener siempre la fuente original.
3. Diferenciar claramente fecha, ámbito, estado y relevancia.
4. Resumir en lenguaje comprensible sin sustituir la información oficial.
5. No publicar fichas automáticas cuando la fuente no pueda validarse.

## Arquitectura

- `index.html`: interfaz principal.
- `assets/`: diseño y lógica de interfaz.
- `data/`: datos públicos consumidos por la web.
- `scripts/`: recolectores y procesadores.
- `.github/workflows/`: automatización de actualización y exportación.

La interfaz pública utiliza archivos relativos y no depende de GitHub Pages.

## Publicación

El proyecto puede publicarse en GitHub Pages o trasladarse a otro hosting.

El workflow **Exportar web para hosting** genera el artefacto `panel-ciudadano-web`, que contiene únicamente la web pública lista para subir a un servidor estático.

Consulta `HOSTING.md` para el procedimiento de migración.

## Actualización y estado de las fuentes

El workflow `actualizar-panel-ciudadano.yml` consulta los módulos cuatro veces al día: 05:00, 11:00, 17:00 y 23:00 UTC. GitHub Actions puede retrasar el inicio de las ejecuciones programadas. En España peninsular corresponden a las 06:00, 12:00, 18:00 y 00:00 en horario de invierno; durante el horario de verano son una hora más tarde.

Cada recolector se ejecuta y valida de forma independiente. Los fallos no se presentan como ausencia de incidencias. El fichero `data/source_health.json` registra la frescura y el estado de las consultas. El diagnóstico se genera durante las ejecuciones del workflow.

El conjunto de incidencias de la DGT consultado por el módulo de movilidad excluye Cataluña y País Vasco. Si la consulta automática falla, la portada ofrece un enlace directo a la información oficial de tráfico de la DGT. Las publicaciones antiguas y los avisos meteorológicos previstos se distinguen de los vigentes, sin inferir una resolución no confirmada por la fuente.
