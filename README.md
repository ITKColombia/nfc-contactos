# Contactos NFC – Asesores

Cada asesor tiene un link secreto a su tarjeta de contacto (`.vcf`), que se graba en un tag NFC.
Al acercar un celular (iPhone o Android) al tag, se abre el contacto listo para guardar.

## Seguridad con repo público

- El repo solo contiene **código**. Los datos de los asesores viven en el secreto **ASESORES_CSV**, que nadie puede leer (ni siquiera los administradores: solo se reemplaza).
- Los `.vcf` **no se guardan en el repo**. Se publican directo en GitHub Pages con nombres aleatorios de 16 caracteres, sin página índice y con `robots.txt` que bloquea buscadores.
- El listado asesor → link se descarga **cifrado** con la clave NFC_SECRETO.
- Los errores no muestran datos personales en los logs (son públicos).
- **Nunca** subas el CSV al repo. Guarda el archivo maestro en tu PC o en OneDrive/SharePoint de la empresa.

## Configuración inicial (una sola vez)

1. Sube al repo `README.md`, `.gitignore`, la carpeta `scripts` y `.github/workflows/publicar.yml`.
2. **Settings → Secrets and variables → Actions → New repository secret**:
   - `NFC_SECRETO`: una frase larga y aleatoria. Guárdala: es la clave del zip de links y **si cambia, cambian todos los links**.
   - `ASESORES_CSV`: abre tu CSV con el Bloc de notas, copia **todo** el texto y pégalo aquí.
3. **Settings → Pages → Source: GitHub Actions**.
4. **Actions → Publicar contactos NFC → Run workflow**.

## Actualizar asesores

1. Edita el CSV en tu PC.
2. **Settings → Secrets and variables → Actions → ASESORES_CSV → lápiz (Update)** → pega el contenido completo → **Update secret**.
3. **Actions → Publicar contactos NFC → Run workflow**.
4. Entra a la ejecución → **Artifacts → links_para_nfc** → descomprime con la clave `NFC_SECRETO` (usa 7-Zip si Windows no lo abre) → abre `links_para_nfc.csv`.
5. En **NFC Tools**: Escribir → Agregar registro → URL/URI → pega el link → Escribir → acerca el tag.

Los asesores que ya tenían tag conservan su link (depende del EMAIL o de la columna CODIGO). Solo graba los nuevos.

## Formato del CSV

`EMPRESA;NOMBRE;CELULAR;EMAIL` (también acepta `,`). Columna opcional `CODIGO` (cédula o código interno) para que el link no dependa del email.
A los celulares sin indicativo se les agrega `+57`. Límite del secreto: 48 KB (aprox. 500 asesores).

## Recomendaciones

- Después de probar cada tag, **bloquéalo** en NFC Tools (Otros → Bloquear etiqueta). Es irreversible.
- Para desactivar a un asesor que se retiró, bórralo del CSV, actualiza el secreto y ejecuta de nuevo.
