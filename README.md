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
