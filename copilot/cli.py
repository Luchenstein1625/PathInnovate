"""Línea de comandos: python -m copilot <comando>."""

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

from . import outline as outlinemod, planner, scan as scanmod, trace as tracemod
from .index import Index, build, build_prompt, cite
from .textutil import snippet

DATA, OUT, CFG = "data", "output", "config"
ROOT_NAMES = ("MAGISTER", "Magister", "magister")
PROJECT_DIR = Path(__file__).resolve().parent.parent


def resolve_root(root=None, env=None, cwd=None):
    """--root, luego MAGISTER_ROOT, luego una carpeta MAGISTER en el directorio actual o en la raíz del proyecto."""
    given = root or env
    if given:
        return Path(given)
    for base in (Path(cwd) if cwd else Path.cwd(), PROJECT_DIR):
        for name in ROOT_NAMES:
            if (base / name).is_dir():
                return base / name
    raise SystemExit("No encuentro la carpeta del magíster. Déjala como MAGISTER/ en la raíz del proyecto, "
                     "o indícala con --root o con la variable MAGISTER_ROOT.")


def _root(args):
    return resolve_root(args.root, os.environ.get("MAGISTER_ROOT"))


def cmd_init(args):
    topics = Path(args.config) / "topics.csv"
    if not topics.exists():
        tracemod.write_topics(topics)
    planner.write_defaults(args.config)
    print(f"Archivos de configuración listos en {args.config}/ (topics.csv, sections.csv, team.csv). Edítalos.")


def cmd_scan(args):
    root = _root(args)
    rows = scanmod.scan(root, args.include_otros, args.include_capstone, args.max_mb)
    path = Path(args.data) / "inventory.csv"
    scanmod.write_inventory(rows, path)
    print(f"Carpeta: {root}\n")
    print(scanmod.summary(rows))
    print(f"\nInventario: {path}  (puedes editar la columna 'status': indexar / excluido)")


def cmd_ingest(args):
    root = _root(args)
    inv = Path(args.data) / "inventory.csv"
    if args.rescan or not inv.exists():
        rows = scanmod.scan(root, args.include_otros, args.include_capstone, args.max_mb)
        scanmod.write_inventory(rows, inv)
    else:
        rows = scanmod.read_inventory(inv)
    stats = build(rows, root, args.data)
    dup = sum(1 for r in rows if r["status"] == "duplicado")
    print(f"Indexados {stats['archivos']} archivos en {stats['chunks']} trozos -> {args.data}/ "
          f"({dup} duplicados omitidos)")
    for rel, n_empty, n_pages in stats["pdf_parcial"][:15]:
        print(f"  ! {rel}: {n_empty}/{n_pages} páginas sin texto (¿escaneadas? requiere OCR)")
    for rel in stats["sin_texto"][:15]:
        print(f"  ! sin texto extraíble: {rel}")
    for rel, err in stats["errores"][:15]:
        print(f"  ! error en {rel}: {err}")


def cmd_ask(args):
    idx = Index(args.data)
    hits = idx.search(args.question, k=args.k, course=args.course, kind=args.kind, session=args.session,
                      per_file=args.per_file)
    if not hits:
        print("Sin resultados. Prueba con otras palabras o sin filtros.")
        return
    if args.prompt:
        prompt = build_prompt(args.question, hits)
        print(prompt)
        print(f"--- ≈ {len(prompt) // 4} tokens de entrada (estimación gruesa: caracteres/4) ---")
        return
    for i, h in enumerate(hits, 1):
        print(f"[{i}] {cite(h)}  (puntaje {h['score']})")
        print("    " + snippet(h["text"], args.question).replace("\n", " ") + "\n")


def cmd_trace(args):
    idx = Index(args.data)
    topics = tracemod.load_topics(Path(args.config) / "topics.csv")
    rows = tracemod.trace(idx, topics)
    counts = tracemod.write_trace(rows, args.out)
    print(f"Tópicos: {len(rows)}")
    for estado, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:>3}  {estado}")
    pend = [r for r in rows if not r["estado_material"].startswith(tracemod.GOOD)]
    if pend:
        print("\nA revisar (no están dictados de forma clara en su sesión):")
        for r in pend:
            print(f"  {r['id']:<6}{r['estado_material']:<32}{r['topico']}")
    print(f"\nSalida: {args.out}/trazabilidad_borrador.md y .csv")


def cmd_outline(args):
    idx = Index(args.data)
    text = outlinemod.outline(idx, args.course, args.window, args.top)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    name = "temario_" + "_".join(args.course) + ".md"
    (Path(args.out) / name).write_text(text, encoding="utf-8")
    print(text)
    print(f"\nSalida: {args.out}/{name}")


def cmd_check(args):
    topics = tracemod.load_topics(Path(args.config) / "topics.csv")
    text = tracemod.render_check(tracemod.check(args.draft, topics))
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "chequeo_borrador.md").write_text(text, encoding="utf-8")
    print(text)


def cmd_plan(args):
    rows, load, cap, spent = planner.plan(args.config)
    text = planner.render(rows, load, cap, spent)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    (Path(args.out) / "plan_14_dias.md").write_text(text, encoding="utf-8")
    with open(Path(args.out) / "plan_14_dias.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(text)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="copilot", description="Copiloto del Magíster (apoyo a la tarea TAAI2)")
    p.add_argument("--data", default=DATA)
    p.add_argument("--out", default=OUT)
    p.add_argument("--config", default=CFG)
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_root(sp):
        sp.add_argument("--root", help="carpeta del magíster (por defecto MAGISTER/ en la raíz del proyecto)")
        sp.add_argument("--include-otros", action="store_true")
        sp.add_argument("--include-capstone", action="store_true")
        sp.add_argument("--max-mb", type=float, default=15)

    sub.add_parser("init").set_defaults(fn=cmd_init)
    s = sub.add_parser("scan")
    with_root(s)
    s.set_defaults(fn=cmd_scan)
    s = sub.add_parser("ingest")
    with_root(s)
    s.add_argument("--rescan", action="store_true", help="vuelve a recorrer la carpeta y rehace el inventario")
    s.set_defaults(fn=cmd_ingest)
    s = sub.add_parser("ask")
    s.add_argument("question")
    s.add_argument("-k", type=int, default=6)
    s.add_argument("--course", action="append", help="filtra por curso (ej. 16); se puede repetir")
    s.add_argument("--session", action="append", help="sesión TAAI2 (S1..S5); se puede repetir")
    s.add_argument("--kind", help="transcript, chat, slides, material, ...")
    s.add_argument("--per-file", type=int, default=2, help="máximo de resultados por archivo (0 = sin límite)")
    s.add_argument("--prompt", action="store_true", help="imprime un prompt con fuentes para pegarlo en un LLM")
    s.set_defaults(fn=cmd_ask)
    s = sub.add_parser("outline", help="temario por tramos de tiempo de las clases de un curso")
    s.add_argument("--course", action="append", required=True, help="curso, ej. 16; se puede repetir")
    s.add_argument("--window", type=int, default=15, help="minutos por tramo")
    s.add_argument("--top", type=int, default=8, help="términos por tramo")
    s.set_defaults(fn=cmd_outline)
    sub.add_parser("trace").set_defaults(fn=cmd_trace)
    s = sub.add_parser("check")
    s.add_argument("draft", help="borrador del informe (.md, .txt, .docx o .pdf)")
    s.set_defaults(fn=cmd_check)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
