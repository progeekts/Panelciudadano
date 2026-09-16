# Panel Ciudadano

Panel público pensado para reunir información de utilidad cotidiana en España y mostrarla de forma clara y rápida.

## Módulos iniciales

- Ayudas y subvenciones
- Estafas activas
- Incidencias de servicios digitales

La portada prioriza la lectura de un vistazo. Cada ficha se puede abrir para consultar contexto adicional y la fuente original.

## Principios

1. No presentar rumores como hechos.
2. Mantener siempre la fuente original.
3. Diferenciar claramente fecha, ámbito, estado y relevancia.
4. Resumir en lenguaje comprensible sin sustituir la información oficial.
5. No publicar fichas automáticas cuando la fuente no pueda validarse.

## Estructura

- `index.html`: interfaz principal.
- `assets/style.css`: diseño responsive.
- `assets/app.js`: filtros, búsqueda y detalle.
- `data/data.js`: almacén de fichas mostrado por la web.

## Publicación

El proyecto está preparado como web estática para GitHub Pages. Los futuros recolectores podrán actualizar `data/data.js` mediante GitHub Actions sin cambiar la interfaz.
