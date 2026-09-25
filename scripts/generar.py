#!/usr/bin/env python3
"""
Genera un .vcf por asesor a partir de datos/asesores.csv.

- Los archivos se nombran con un código aleatorio pero ESTABLE
  (HMAC del email con una clave secreta), así el link grabado en el tag
  no cambia aunque se actualicen el nombre o el celular del asesor.
- Los datos vienen del secreto ASESORES_CSV: nunca quedan guardados en el repo.
- Los mensajes de error no muestran datos personales (los logs de un repo público son visibles).
- Por cada asesor se publica c/<código>.vcf (contacto) y c/<código>.html (tarjeta web).
- web/grabar.html se publica como grabar.html (herramienta para grabar tags, sin datos).

Variables de entorno:
  NFC_SECRETO   clave secreta (obligatoria; se guarda en GitHub Secrets)
  BASE_URL      URL pública del sitio, p. ej. https://usuario.github.io/nfc-contactos
  PREFIJO_PAIS  indicativo a agregar si el celular no lo trae (por defecto 57)
"""
import base64, csv, hashlib, hmac, html, io, os, re, shutil, sys, unicodedata
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
        return None
    d = hmac.new(secreto, clave.encode(), hashlib.sha256).digest()
    return base64.b32encode(d).decode().lower().rstrip("=")[:16]


TARJETA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<title>{nombre}</title>
<style>
:root{{--bg:#f4f5f7;--card:#fff;--tx:#1b1f24;--mut:#6b7280;--pri:#ffcc00;--bd:#e3e5e8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121417;--card:#1c1f24;--tx:#eef0f3;--mut:#9aa3ad;--bd:#2c3139}}}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;
font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--tx)}}
.card{{width:100%;max-width:420px;background:var(--card);border:1px solid var(--bd);border-radius:18px;overflow:hidden}}
.top{{background:#1b1f24;color:#fff;padding:28px 20px;text-align:center}}
.av{{width:84px;height:84px;border-radius:50%;background:var(--pri);color:#1b1f24;display:flex;align-items:center;
justify-content:center;font-size:2rem;font-weight:700;margin:0 auto 12px}}
h1{{margin:0;font-size:1.4rem}}
.org{{margin:4px 0 0;color:#c7ccd3}}
.body{{padding:18px 20px 22px}}
.dato{{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--bd);font-size:.95rem}}
.dato span{{color:var(--mut)}}
.dato b{{font-weight:500;word-break:break-all;text-align:right}}
a.btn{{display:block;text-align:center;text-decoration:none;font-weight:600;padding:14px;border-radius:12px;margin-top:10px}}
.pri{{background:var(--pri);color:#1b1f24;margin-top:18px!important;font-size:1.05rem}}
.sec{{background:var(--bd);color:var(--tx)}}
.fila{{display:grid;grid-template-columns:repeat({ncols},1fr);gap:8px}}
</style></head>
<body><div class="card">
<div class="top"><div class="av">{iniciales}</div><h1>{nombre}</h1>{org_html}</div>
<div class="body">
{datos}
<a class="btn pri" href="{vcf}">Guardar contacto</a>
<div class="fila">{botones}</div>
</div></div></body></html>
"""


def tarjeta(a, codigo_vcf):
    e = html.escape
    nombre = a["nombre"]
    iniciales = "".join(p[0] for p in nombre.split()[:2]).upper()
    tel_ = telefono(a["celular"]) if a["celular"] else ""
    datos, botones = [], []
    if tel_:
        datos.append(f'<div class="dato"><span>Celular</span><b>{e(tel_)}</b></div>')
        botones.append(f'<a class="btn sec" href="tel:{e(tel_)}">Llamar</a>')
        botones.append(f'<a class="btn sec" href="https://wa.me/{e(tel_.lstrip("+"))}">WhatsApp</a>')
    if a["email"]:
        datos.append(f'<div class="dato"><span>Email</span><b>{e(a["email"])}</b></div>')
        botones.append(f'<a class="btn sec" href="mailto:{e(a["email"])}">Correo</a>')
    return TARJETA.format(
        nombre=e(nombre), iniciales=e(iniciales),
        org_html=f'<p class="org">{e(a["empresa"])}</p>' if a["empresa"] else "",
        datos="\n".join(datos), botones="".join(botones), ncols=max(len(botones), 1),
        vcf=f"{codigo_vcf}.vcf",
    )


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

grabar = RAIZ / "web" / "grabar.html"
if grabar.exists():
    shutil.copy(grabar, SITIO / "grabar.html")

vistos, salida, omitidas = set(), [], []
for a in leer_csv(CSV_IN):
    c = codigo(a)
    if not a["nombre"] or c is None:
        print(f"::warning::Fila {a['fila']} omitida: le falta NOMBRE o (EMAIL/CELULAR/CODIGO).")
        omitidas.append(a["fila"])
        continue
    if c in vistos:
        print(f"::warning::Fila {a['fila']} omitida: duplicada (mismo email/código que otra fila).")
        omitidas.append(a["fila"])
        continue
    vistos.add(c)
    (SITIO / "c" / f"{c}.vcf").write_text(vcard(a), encoding="utf-8", newline="")
    (SITIO / "c" / f"{c}.html").write_text(tarjeta(a, c), encoding="utf-8")
    salida.append([a["nombre"], a["email"], f"{base_url}/c/{c}.html"])

with LINKS.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["NOMBRE", "EMAIL", "LINK_NFC"])
    w.writerows(salida)

if not salida:
    sys.exit("ERROR: no se generó ningún contacto. Revisa el CSV.")
print(f"OK: {len(salida)} contactos generados. Filas omitidas: {omitidas or 'ninguna'}")
