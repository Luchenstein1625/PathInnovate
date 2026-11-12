"""Genera Anexo_B_v2.xlsx con FORMULAS trazables (todo recalcula al cambiar un supuesto en la hoja Supuestos).
Uso: python build_anexo_b.py [salida.xlsx]   y luego recalcular con LibreOffice o abrir en Excel."""
import sys, json
from pathlib import Path
B = json.loads((Path(__file__).resolve().parent / "config/budget_current.json").read_text(encoding="utf-8"))["assumptions"]
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.comments import Comment

OUT = sys.argv[1] if len(sys.argv) > 1 else "entrega/Anexo_B_PathInnovate.xlsx"
F = "Arial"; BLUE = Font(name=F, color="0000FF"); BLK = Font(name=F); BOLD = Font(name=F, bold=True)
HEAD = PatternFill("solid", fgColor="D9E2F3"); WARN = PatternFill("solid", fgColor="FFF2CC")
wb = Workbook()

def head(ws, row, vals):
    for i, v in enumerate(vals, 1):
        c = ws.cell(row=row, column=i, value=v); c.font = BOLD; c.fill = HEAD; c.alignment = Alignment(wrap_text=True, vertical="top")

# ---------------- Leyenda ----------------
lg = wb.active; lg.title = "Leyenda"
for r, t in enumerate(["Anexo B · Supuestos y presupuesto del Asesor de tecnología de IA (Camino Digital SpA, consultora ficticia)",
    "Azul = dato de entrada editable (hoja Supuestos). Negro = fórmula. Todas las hojas recalculan al cambiar una entrada.",
    "Tipo de dato: MEDIDO (sale de las evaluaciones del proyecto), FUENTE (página oficial con fecha) o SUPUESTO (del grupo; debe justificarse).",
    "Hojas: Supuestos > TCO > Equilibrio > Sensibilidad > Escenarios.",
    "Cambios respecto de la versión anterior: tokens medidos del asesor (522,7 de entrada y 55,3 de salida), GPU disponible 24/7 (730 h),",
    "personal por rol y dedicación, y líneas de datos, licencias y capacitación. Todo con fórmulas."], 1):
    lg.cell(row=r, column=1, value=t).font = BOLD if r == 1 else BLK
lg.column_dimensions["A"].width = 130

# ---------------- Supuestos ----------------
sp = wb.create_sheet("Supuestos"); head(sp, 1, ["Variable", "Valor", "Unidad", "Tipo", "Fuente o justificación", "Fecha"])
R = {}
def inp(key, label, val, unit, tipo, src, date="2026-11-12", fmt=None):
    r = sp.max_row + 1
    sp.cell(row=r, column=1, value=label).font = BLK
    c = sp.cell(row=r, column=2, value=val); c.font = BLUE
    if fmt: c.number_format = fmt
    for col, v in ((3, unit), (4, tipo), (5, src), (6, date)): sp.cell(row=r, column=col, value=v).font = BLK
    if tipo == "SUPUESTO": sp.cell(row=r, column=4).fill = WARN
    R[key] = f"Supuestos!$B${r}"
SRC_EV = "eval_asesor/resultados_asesor_FINAL3.json, config híbrido, 96 respuestas (incluye reintentos)"
inp("Q", "Consultas al mes", 50000, "consultas/mes", "SUPUESTO", "Consultora ficticia: 10.000 clientes activos × 5 consultas al mes", fmt="#,##0")
inp("TIN", "Tokens de entrada por consulta", B["prompt_tokens"], "tokens", "MEDIDO", SRC_EV, "2026-11-12", "0.0")
inp("TOUT", "Tokens de salida por consulta", B["completion_tokens"], "tokens", "MEDIDO", SRC_EV, "2026-11-12", "0.0")
inp("PIN", "Precio de entrada del modelo (gpt-4o-mini)", B["api_in_per_mtok"], "USD por millón de tokens", "FUENTE", "https://developers.openai.com/api/docs/models/gpt-4o-mini", "2026-11-12", "0.00")
inp("POUT", "Precio de salida del modelo (gpt-4o-mini)", B["api_out_per_mtok"], "USD por millón de tokens", "FUENTE", "https://developers.openai.com/api/docs/models/gpt-4o-mini", "2026-11-12", "0.00")
inp("GPU", "Costo por hora de GPU", 1.20, "USD/h", "SUPUESTO", "Sin fuente: reemplazar por precio de lista del proveedor de nube, con fecha", fmt="0.00")
inp("H", "Horas de GPU al mes", 730, "h/mes", "SUPUESTO", "Servicio disponible 24/7 (corrige las 19,3 h de cómputo medido en la corrida)", fmt="#,##0")
inp("INFRA_API", "Infraestructura base (alternativa API)", 50, "USD/mes", "SUPUESTO", "Cloud Run con escala a cero, registros y secretos", fmt="#,##0")
inp("INFRA_SELF", "Infraestructura base (híbrido y modelo propio)", 100, "USD/mes", "SUPUESTO", "Contenedores, almacenamiento de modelos y observabilidad", fmt="#,##0")
inp("LIC", "Licencias y herramientas", 50, "USD/mes", "SUPUESTO", "Monitoreo y herramientas de desarrollo", fmt="#,##0")
inp("SHARE", "Fracción de consultas atendidas por el modelo propio (híbrido)", 0.8, "fracción", "SUPUESTO", "Diseño del híbrido: 80 % modelo propio y 20 % API", fmt="0%")
inp("DEV_API", "CAPEX de desarrollo inicial: API", 5000, "USD", "SUPUESTO", "Ingeniería inicial del servicio y la integración", fmt="#,##0")
inp("DEV_HIB", "CAPEX de desarrollo inicial: híbrido", 10000, "USD", "SUPUESTO", "Incluye puesta en marcha del modelo propio", fmt="#,##0")
inp("DEV_SLM", "CAPEX de desarrollo inicial: modelo propio", 15000, "USD", "SUPUESTO", "Incluye entrenamiento o ajuste e infraestructura", fmt="#,##0")
inp("DATOS", "Datos y anotación (una vez)", 1500, "USD", "SUPUESTO", "Etiquetado de 200 a 300 casos por consultores", fmt="#,##0")
inp("CAP", "Capacitación y cambio organizacional (una vez)", 1000, "USD", "SUPUESTO", "Capacitación de los 25 consultores", fmt="#,##0")
inp("CASO", "Costo de atender un caso a mano", 0.40, "USD/caso", "SUPUESTO", "3 minutos de un ejecutivo de primer nivel a 8 USD por hora", fmt="0.00")
inp("AUTO", "Tasa de automatización", 0.5, "fracción", "SUPUESTO", "Sin fuente: validar en el piloto", fmt="0%")
inp("TASA", "Tasa de descuento anual", 0.10, "tasa", "SUPUESTO", "Sin fuente: justificar con una referencia financiera", fmt="0%")
inp("DELTA", "Variación para la sensibilidad", 0.30, "fracción", "SUPUESTO", "±30 % sobre cada variable", fmt="0%")

sp.cell(row=sp.max_row + 2, column=1, value="Personal por rol: tarifas internas de planificacion; no remuneraciones verificadas").font = BOLD
r0 = sp.max_row + 1; head(sp, r0, ["Rol", "Costo mensual completo (USD)", "Dedicación API", "Dedicación híbrido", "Dedicación modelo propio", ""])
roles = [("Ingeniero de IA", 5000, .3, .5, .8), ("DevOps", 4500, .1, .2, .25), ("Consultor revisor de casos derivados", 3000, .2, .2, .15)]
for i, (n, c, a, h, s) in enumerate(roles, r0 + 1):
    sp.cell(row=i, column=1, value=n).font = BLK
    for col, v in ((2, c), (3, a), (4, h), (5, s)):
        x = sp.cell(row=i, column=col, value=v); x.font = BLUE; x.number_format = "#,##0" if col == 2 else "0%"
rl = r0 + len(roles); rt = rl + 1
sp.cell(row=rt, column=1, value="Costo de personal al mes (fórmula)").font = BOLD
for col, key in ((3, "PERS_API"), (4, "PERS_HIB"), (5, "PERS_SLM")):
    L = sp.cell(row=rt, column=col).column_letter
    c = sp.cell(row=rt, column=col, value=f"=SUMPRODUCT($B${r0+1}:$B${rl},{L}{r0+1}:{L}{rl})"); c.font = BOLD; c.number_format = "#,##0"
    R[key] = f"Supuestos!${L}${rt}"
sp.cell(row=rt + 2, column=1, value="Cifras derivadas (fórmulas)").font = BOLD
def der(key, label, formula, fmt):
    r = sp.max_row + 1
    sp.cell(row=r, column=1, value=label).font = BLK
    c = sp.cell(row=r, column=2, value=formula); c.font = BLK; c.number_format = fmt
    R[key] = f"Supuestos!$B${r}"
der("CC", "Costo de API por consulta (USD)", f"=({R['TIN']}*{R['PIN']}+{R['TOUT']}*{R['POUT']})/1000000", "0.000000")
der("I", "Tasa de descuento mensual", f"=(1+{R['TASA']})^(1/12)-1", "0.0000%")
der("A12", "Factor de anualidad a 12 meses", f"=(1-(1+{R['I']})^(-12))/{R['I']}", "0.0000")
der("A36", "Factor de anualidad a 36 meses", f"=(1-(1+{R['I']})^(-36))/{R['I']}", "0.0000")
der("BEN", "Beneficio mensual por automatización (USD)", f"={R['Q']}*{R['AUTO']}*{R['CASO']}", "#,##0")
for col, w in zip("ABCDEF", (58, 20, 24, 14, 80, 12)): sp.column_dimensions[col].width = w

# ---------------- formulas parametrizadas ----------------
ALTS = {"api": dict(nom="API comercial + RAG + verificador", tok="1", gpu="0", infra=R["INFRA_API"], pers=R["PERS_API"], dev=R["DEV_API"]),
        "hib": dict(nom="Híbrido (modelo propio + API)", tok=f"(1-{R['SHARE']})", gpu="1", infra=R["INFRA_SELF"], pers=R["PERS_HIB"], dev=R["DEV_HIB"]),
        "slm": dict(nom="Modelo propio (SLM)", tok="0", gpu="1", infra=R["INFRA_SELF"], pers=R["PERS_SLM"], dev=R["DEV_SLM"])}
ONE = dict(q="1", p="1", g="1", pers="1", cap="1", caso="1", auto="1")
def opex(a, m=ONE):
    A = ALTS[a]; return (f"({R['Q']}*{m['q']}*{R['CC']}*{m['p']}*{A['tok']}+{R['GPU']}*{m['g']}*{R['H']}*{A['gpu']}"
                         f"+{A['infra']}+{A['pers']}*{m['pers']}+{R['LIC']})")
def capex(a, m=ONE): return f"(({ALTS[a]['dev']}+{R['DATOS']}+{R['CAP']})*{m['cap']})"
def benef(m=ONE): return f"({R['Q']}*{m['q']}*{R['AUTO']}*{m['auto']}*{R['CASO']}*{m['caso']})"
def tco(a, n, m=ONE): return f"={capex(a, m)}+{n}*{opex(a, m)}"
def van(a, n, m=ONE): return f"=-{capex(a, m)}+({benef(m)}-{opex(a, m)})*{R['A'+str(n)]}"

# ---------------- TCO ----------------
t = wb.create_sheet("TCO"); head(t, 1, ["Concepto (USD)", ALTS["api"]["nom"], ALTS["hib"]["nom"], ALTS["slm"]["nom"]])
rows = {}
def line(key, label, fn, fmt="#,##0"):
    r = t.max_row + 1; t.cell(row=r, column=1, value=label).font = BLK; rows[key] = r
    for col, a in zip((2, 3, 4), ("api", "hib", "slm")):
        c = t.cell(row=r, column=col, value=fn(a, col)); c.font = BLK; c.number_format = fmt
L = lambda col: t.cell(row=1, column=col).column_letter
line("tok", "Tokens de la API al mes", lambda a, c: f"={R['Q']}*{R['CC']}*{ALTS[a]['tok']}", "#,##0.00")
line("gpu", "GPU al mes (disponible 24/7)", lambda a, c: f"={R['GPU']}*{R['H']}*{ALTS[a]['gpu']}")
line("inf", "Infraestructura base al mes", lambda a, c: f"={ALTS[a]['infra']}")
line("per", "Personal al mes (por rol y dedicación)", lambda a, c: f"={ALTS[a]['pers']}")
line("lic", "Licencias y herramientas al mes", lambda a, c: f"={R['LIC']}")
line("opx", "OPEX mensual total", lambda a, c: f"=SUM({L(c)}{rows['tok']}:{L(c)}{rows['lic']})")
line("dev", "CAPEX: desarrollo inicial", lambda a, c: f"={ALTS[a]['dev']}")
line("dat", "CAPEX: datos y anotación", lambda a, c: f"={R['DATOS']}")
line("cap", "CAPEX: capacitación y cambio organizacional", lambda a, c: f"={R['CAP']}")
line("cpx", "CAPEX total", lambda a, c: f"=SUM({L(c)}{rows['dev']}:{L(c)}{rows['cap']})")
line("t12", "TCO a 12 meses", lambda a, c: f"={L(c)}{rows['cpx']}+12*{L(c)}{rows['opx']}")
line("t36", "TCO a 36 meses", lambda a, c: f"={L(c)}{rows['cpx']}+36*{L(c)}{rows['opx']}")
line("ben", "Beneficio mensual (ahorro por automatización)", lambda a, c: f"={R['BEN']}")
line("net", "Beneficio neto mensual", lambda a, c: f"={L(c)}{rows['ben']}-{L(c)}{rows['opx']}")
line("v12", "VAN a 12 meses", lambda a, c: f"=-{L(c)}{rows['cpx']}+{L(c)}{rows['net']}*{R['A12']}")
line("v36", "VAN a 36 meses", lambda a, c: f"=-{L(c)}{rows['cpx']}+{L(c)}{rows['net']}*{R['A36']}")
line("eq", "Punto de equilibrio (mes)", lambda a, c: f'=IF({L(c)}{rows["net"]}>0,ROUNDUP({L(c)}{rows["cpx"]}/{L(c)}{rows["net"]},0),"no se paga")', "0")
for r in (rows["opx"], rows["cpx"], rows["t12"], rows["t36"], rows["v36"]):
    for col in range(1, 5): t.cell(row=r, column=col).font = BOLD
t.column_dimensions["A"].width = 52
for col in "BCD": t.column_dimensions[col].width = 34

# ---------------- Equilibrio ----------------
e = wb.create_sheet("Equilibrio"); head(e, 1, ["Concepto", "Valor", "Nota"])
fx = lambda col: f"(TCO!{col}{rows['opx']}-TCO!{col}{rows['tok']})"
items = [("Costo variable de la API por consulta (USD)", f"={R['CC']}", "0.000000", "Tokens medidos × precio"),
 ("Costo fijo mensual: API (sin tokens)", f"={fx('B')}", "#,##0", "Infraestructura, personal y licencias"),
 ("Costo fijo mensual: modelo propio (sin tokens)", f"={fx('D')}", "#,##0", "Incluye GPU disponible 24/7"),
 ("Consultas al mes en que el modelo propio iguala a la API (OPEX)", "=(B4-B3)/B2", "#,##0", "Sobre este volumen el modelo propio es más barato por mes"),
 ("Consultas al mes supuestas", f"={R['Q']}", "#,##0", ""),
 ("Veces que el equilibrio supera el volumen supuesto", "=B5/B6", "#,##0.0", "")]
for r, (a, f_, fm, n) in enumerate(items, 2):
    e.cell(row=r, column=1, value=a).font = BLK; c = e.cell(row=r, column=2, value=f_); c.font = BLK; c.number_format = fm; e.cell(row=r, column=3, value=n).font = BLK
e.column_dimensions["A"].width = 66; e.column_dimensions["B"].width = 20; e.column_dimensions["C"].width = 60

# ---------------- Sensibilidad ----------------
s = wb.create_sheet("Sensibilidad"); head(s, 1, ["Alternativa", "Variable", "TCO36 −30 %", "TCO36 +30 %", "Oscilación TCO36", "VAN36 −30 %", "VAN36 +30 %", "Oscilación VAN36", "Rango (VAN36)"])
VARS = [("Costo de personal", "pers"), ("CAPEX", "cap"), ("Consultas al mes", "q"), ("Precio de los tokens", "p"),
        ("Costo por hora de GPU", "g"), ("Costo por caso manual", "caso"), ("Tasa de automatización", "auto")]
lo, hi = f"(1-{R['DELTA']})", f"(1+{R['DELTA']})"
r = 2
for a in ("api", "hib", "slm"):
    first = r
    for nom, k in VARS:
        ml, mh = dict(ONE, **{k: lo}), dict(ONE, **{k: hi})
        s.cell(row=r, column=1, value=ALTS[a]["nom"]).font = BLK; s.cell(row=r, column=2, value=nom).font = BLK
        s.cell(row=r, column=3, value=tco(a, 36, ml)); s.cell(row=r, column=4, value=tco(a, 36, mh))
        s.cell(row=r, column=5, value=f"=ABS(D{r}-C{r})")
        s.cell(row=r, column=6, value=van(a, 36, ml)); s.cell(row=r, column=7, value=van(a, 36, mh))
        s.cell(row=r, column=8, value=f"=ABS(G{r}-F{r})")
        for col in range(3, 9): s.cell(row=r, column=col).number_format = "#,##0"; s.cell(row=r, column=col).font = BLK
        r += 1
    for rr in range(first, r): s.cell(row=rr, column=9, value=f"=RANK(H{rr},$H${first}:$H${r-1})").font = BLK
    r += 1
s.cell(row=r, column=1, value="Chequeo: la fórmula base de la hoja coincide con TCO (debe ser 0)").font = BOLD
s.cell(row=r, column=3, value=f"=ROUND({tco('api', 36)[1:]}-TCO!B{rows['t36']},2)").font = BLK
s.cell(row=r + 1, column=1, value="Nota: la oscilación del VAN incluye el efecto sobre el beneficio; la del TCO solo sobre costos.").font = BLK
for col, w in zip("ABCDEFGHI", (36, 28, 16, 16, 18, 16, 16, 18, 14)): s.column_dimensions[col].width = w

# ---------------- Escenarios ----------------
x = wb.create_sheet("Escenarios"); head(x, 1, ["Escenario", "TCO36 API", "TCO36 base", "Diferencia (USD)", "Diferencia (%)"])
for r, (nom, m) in enumerate([("Precio de los tokens ÷ 10", dict(ONE, p="0.1")), ("Precio de los tokens × 3", dict(ONE, p="3")),
                              ("Consultas × 10 (500.000 al mes)", dict(ONE, q="10"))], 2):
    x.cell(row=r, column=1, value=nom).font = BLK
    x.cell(row=r, column=2, value=tco("api", 36, m)); x.cell(row=r, column=3, value=f"=TCO!B{rows['t36']}")
    x.cell(row=r, column=4, value=f"=B{r}-C{r}"); x.cell(row=r, column=5, value=f"=D{r}/C{r}")
    for col in (2, 3, 4): x.cell(row=r, column=col).number_format = "#,##0"
    x.cell(row=r, column=5).number_format = "0.00%"
    for col in range(2, 6): x.cell(row=r, column=col).font = BLK
x.column_dimensions["A"].width = 40
for col in "BCDE": x.column_dimensions[col].width = 18
# Interpretacion financiera y capacidad; mismos controles del anexo final.
e['C5'] = 'Cruce algebraico de OPEX con costos y capacidad constantes; no es un umbral operativo validado.'
e.append([]);e.append(['Limite de capacidad','No medido','No extrapolar una GPU a millones de consultas.'])
e.append(['Comparacion de calidad','No equivalente','Validar automatizacion por alternativa.'])
for address,value in {'A6':'Monetizacion alternativa (no sumar al ahorro interno)','A7':'Clientes de pago (supuesto)','B7':1000,'A8':'Precio mensual USD (supuesto)','B8':5,'A9':'Ingresos mensuales','B9':'=B7*B8','A10':'OPEX mensual API','B10':'=TCO!B7','A11':'Margen operativo mensual antes de CAPEX e impuestos','B11':'=B9-B10','A12':'Margen operativo porcentual','B12':'=IF(B9>0,B11/B9,0)','A14':'Revision humana (capacidad supuesta)','A15':'Horas laborales/mes por FTE','B15':160,'A16':'Minutos por derivacion','B16':3,'A17':'Capacidad mensual del consultor API','B17':'=Supuestos!C27*B15*60/B16','A18':'Abstencion interna FINAL3','B18':.156,'A19':'Derivaciones mensuales','B19':'=Supuestos!B2*B18','A20':'Brecha de capacidad mensual','B20':'=MAX(0,B19-B17)','A22':'Conclusion','B22':'No escalar sin dimensionar y financiar capacidad humana.'}.items():
    x[address]=value
x['B12'].number_format='0.0%';x['B18'].number_format='0.0%'
for cell in ['B9','B10','B11']:x[cell].number_format='#,##0.00'
sp['B33']='=IF(Supuestos!$B$32=0,12,(1-(1+Supuestos!$B$32)^(-12))/Supuestos!$B$32)'
sp['B34']='=IF(Supuestos!$B$32=0,36,(1-(1+Supuestos!$B$32)^(-36))/Supuestos!$B$32)'
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT); print("escrito", OUT)
