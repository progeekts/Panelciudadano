# Despliegue fuera de GitHub Pages

Panel Ciudadano separa la recopilación de datos de la web pública. GitHub puede seguir ejecutando los recolectores mientras un hosting externo sirve únicamente la copia estática.

## Despliegue automático por SFTP

El workflow `Exportar y desplegar web` genera el paquete `panel-ciudadano-web` y, cuando están configurados los secretos, sincroniza automáticamente `dist/` con el directorio público del hosting.

### Secrets necesarios

En el repositorio abre **Settings → Secrets and variables → Actions → New repository secret** y crea:

- `DEPLOY_HOST` — servidor SFTP facilitado por el hosting. Ejemplo de formato: `ftp.example.net` o `ssh.example.net`. No incluyas `sftp://`.
- `DEPLOY_USER` — usuario SFTP.
- `DEPLOY_PASSWORD` — contraseña del usuario SFTP.
- `DEPLOY_PATH` — ruta remota exacta donde debe publicarse Panel Ciudadano, por ejemplo `/www/panel/`. Debe ser la carpeta pública asignada al dominio o subdominio.
- `DEPLOY_PORT` — opcional. Puerto SFTP. Si se omite, el workflow usa `22`.

No guardes estas credenciales en archivos del repositorio.

## Primera puesta en marcha

1. Crea primero el dominio o subdominio en el hosting.
2. Confirma cuál es su carpeta raíz pública.
3. Confirma que el proveedor permite SFTP.
4. Crea los secretos anteriores.
5. Ve a **Actions → Exportar y desplegar web → Run workflow**.
6. Comprueba el resultado del paso **Desplegar por SFTP**.
7. Abre el dominio y verifica la portada, los estilos y varias fichas.

Hasta que los secretos estén creados, el workflow no falla: genera el artefacto descargable y omite el despliegue externo.

## Funcionamiento posterior

Cuando cambia la interfaz o `data/`, el workflow vuelve a generar la web y sincroniza el hosting. Además existe una ejecución programada cada hora como respaldo.

La opción `--delete` mantiene el hosting como espejo del paquete público: elimina del directorio remoto los archivos que ya no existan en `dist/`. Por eso `DEPLOY_PATH` debe apuntar a una carpeta dedicada exclusivamente a Panel Ciudadano.

## Qué se publica

Solo:

- `index.html`
- `metodologia.html`
- `privacidad.html`
- `assets/`
- `data/`
- `.htaccess`
- `DEPLOY.txt`

No se suben `scripts/`, `.github/`, los workflows ni el código de recopilación.

## Seguridad

El paquete incluye un `.htaccess` opcional para Apache con desactivación del listado de directorios, UTF-8, cabeceras básicas de seguridad y reglas de caché.

Las credenciales quedan en GitHub Actions Secrets y se referencian como `secrets.DEPLOY_*`; no deben escribirse directamente en el YAML.
