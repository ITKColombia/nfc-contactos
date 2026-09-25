#!/usr/bin/env python3
"""
Genera un .vcf por asesor a partir de datos/asesores.csv.

- Los archivos se nombran con un código aleatorio pero ESTABLE
  (HMAC del email con una clave secreta), así el link grabado en el tag
  no cambia aunque se actualicen el nombre o el celular del asesor.
- Los datos vienen del secreto ASESORES_CSV: nunca quedan guardados en el repo.
- Los mensajes de error no muestran datos personales (los logs de un repo público son visibles).
- `links_para_nfc.csv` queda fuera del sitio (se descarga desde GitHub Actions).

Variables de entorno:
  NFC_SECRETO   clave secreta (obligatoria; se guarda en GitHub Secrets)
  BASE_URL      URL pública del sitio, p. ej. https://usuario.github.io/nfc-contactos
  PREFIJO_PAIS  indicativo a agregar si el celular no lo trae (por defecto 57)
"""
import base64, csv, hashlib, hmac, io, os, re, shutil, sys, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV_IN = RAIZ / "datos" / "asesores.csv"
SITIO = RAIZ / "sitio"
LINKS = RAIZ / "links_para_nfc.csv"

secreto = os.environ.get("NFC_SECRETO", "").encode()
if len(secreto) < 16:
    sys.exit("ERROR: falta NFC_SECRETO (mínimo 16 caracteres). Configúralo en Settings > Secrets > Actions.")
base_url = os.environ.get("BASE_URL", "").rstrip("/")
prefijo = os.environ.get("PREFIJO_PAIS", "57")


def norm(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().strip().upper()


def leer_csv(ruta):
    # El CSV viene del secreto ASESORES_CSV (repo público). Si no existe, se usa el archivo local.
    texto = os.environ.get("ASESORES_CSV", "").lstrip("\ufeff")
    if not texto.strip():
        if not ruta.exists():
            sys.exit("ERROR: falta el secreto ASESORES_CSV con los datos de los asesores.")
        texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
    primera = texto.splitlines()[0]
    sep = max([";", ",", "\t"], key=primera.count)
    filas = list(csv.reader(io.StringIO(texto), delimiter=sep))
    enc = [norm(h) for h in filas[0]]

    def col(*claves):
        for i, h in enumerate(enc):
            if any(k in h for k in claves):
                return i
        return None

    idx = {
        "empresa": col("EMPRESA"),
        "nombre": col("NOMBRE"),
        "celular": col("CELULAR", "TELEFONO"),
        "email": col("EMAIL", "CORREO"),
        "codigo": col("CODIGO", "ID"),
    }
    if idx["nombre"] is None:
        sys.exit("ERROR: no encontré la columna NOMBRE. Revisa la primera fila del CSV.")
    for n, f in enumerate(filas[1:], start=2):
        if not any(v.strip() for v in f):
            continue
        d = {k: (f[i].strip() if i is not None and i < len(f) else "") for k, i in idx.items()}
        d["fila"] = n
        yield d


def esc(v):
    return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def telefono(v):
    t = re.sub(r"[^\d+]", "", v)
    if t and not t.startswith("+"):
        t = "+" + t if (t.startswith(prefijo) and len(t) > 10) else "+" + prefijo + t
    return t


def vcard(a):
    partes = a["nombre"].split()
    corte = (len(partes) + 1) // 2
    nom, ape = " ".join(partes[:corte]), " ".join(partes[corte:])
    l = ["BEGIN:VCARD", "VERSION:3.0", f"N:{esc(ape)};{esc(nom)};;;", f"FN:{esc(a['nombre'])}"]
    if a["empresa"]:
        l.append(f"ORG:{esc(a['empresa'])}")
    if a["celular"]:
        l.append(f"TEL;TYPE=CELL:{telefono(a['celular'])}")
    if a["email"]:
        l.append(f"EMAIL;TYPE=WORK:{a['email']}")
    l.append("END:VCARD")
    return "\r\n".join(l) + "\r\n"


def codigo(a):
    clave = (a["codigo"] or a["email"] or a["celular"]).strip().lower()
    if not clave:
        sys.exit(f"ERROR: la fila {a['fila']} del CSV no tiene EMAIL, CELULAR ni CODIGO.")
    d = hmac.new(secreto, clave.encode(), hashlib.sha256).digest()
    return base64.b32encode(d).decode().lower().rstrip("=")[:16]


# --- Construir sitio ---
if SITIO.exists():
    shutil.rmtree(SITIO)
(SITIO / "c").mkdir(parents=True)

(SITIO / ".nojekyll").write_text("")
(SITIO / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
(SITIO / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
    "<title>.</title>\n"
)
(SITIO / "404.html").write_text(
    '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
    "<title>No encontrado</title>\n"
)

vistos, salida = set(), []
for a in leer_csv(CSV_IN):
    c = codigo(a)
    if c in vistos:
        sys.exit(f"ERROR: la fila {a['fila']} está duplicada (mismo email/código que otra fila).")
    vistos.add(c)
    (SITIO / "c" / f"{c}.vcf").write_text(vcard(a), encoding="utf-8", newline="")
    salida.append([a["nombre"], a["email"], f"{base_url}/c/{c}.vcf"])

with LINKS.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["NOMBRE", "EMAIL", "LINK_NFC"])
    w.writerows(salida)

print(f"OK: {len(salida)} contactos generados.")
