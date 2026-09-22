# Despliegue fuera de GitHub Pages

Panel Ciudadano está preparado para funcionar como una web estática independiente de GitHub Pages.

## Arquitectura

Hay dos partes separadas:

1. **Actualización de datos**
   - Los scripts de `scripts/` consultan las fuentes.
   - GitHub Actions ejecuta esos scripts.
   - Los resultados se guardan en `data/`.

2. **Web pública**
   - `index.html`, `metodologia.html` y `privacidad.html`.
   - `assets/` contiene estilos y JavaScript.
   - `data/` contiene los datos que consume la interfaz.
   - No necesita PHP, Node, Python ni base de datos en el hosting.

Esto permite mantener GitHub como motor de actualización y alojar la web pública en cualquier hosting estático.

## Obtener el paquete para hosting

1. Ve a **Actions**.
2. Ejecuta o abre el workflow **Exportar web para hosting**.
3. Descarga el artefacto **panel-ciudadano-web**.
4. Descomprime el ZIP.
5. Sube su contenido al directorio público del hosting.

El paquete contiene solo los archivos necesarios para publicar la web.

## Hosting compatible

Funciona en cualquier servidor capaz de servir archivos estáticos por HTTPS, por ejemplo:

- hosting tradicional Apache;
- Nginx;
- OVH;
- Cloudflare Pages;
- Netlify;
- Vercel como sitio estático;
- almacenamiento web estático equivalente.

## Actualizaciones

Los workflows de recopilación pueden seguir ejecutándose en GitHub y modificando `data/`.

El workflow de exportación genera periódicamente un nuevo paquete con la versión más reciente.

Si quieres automatizar también la subida al hosting, puede añadirse posteriormente un despliegue mediante SFTP/FTP/rsync o el mecanismo que proporcione el proveedor.

## Rutas

La web utiliza rutas relativas, por lo que no está ligada al dominio de GitHub Pages.

Para instalarla en la raíz de un dominio o subdominio basta con copiar el contenido del paquete manteniendo la estructura de carpetas.

## Seguridad

El paquete incluye un `.htaccess` opcional para Apache con:

- desactivación del listado de directorios;
- UTF-8 por defecto;
- cabeceras básicas de seguridad;
- caché corta para datos dinámicos y moderada para recursos estáticos.

Si el servidor no usa Apache, el archivo puede ignorarse.
