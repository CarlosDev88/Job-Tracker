"""
Entry point del pipeline — ejecución manual.
Uso:
  python run.py --perfil "Frontend React Senior"
  python run.py --filtrar
  python run.py --analizar
  python run.py --importar   (--filtrar + --analizar en un solo paso)
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, activar_perfil, get_perfiles
from backend.pipeline import filtrar_raw_data, analizar_con_llm


def main():
    parser = argparse.ArgumentParser(description="Job Tracker Pipeline")
    parser.add_argument("--perfil", type=str, help="Nombre del perfil a activar y usar")
    parser.add_argument(
        "--filtrar", action="store_true", help="Etapa 1: filtrar raw_data/ por keywords → filtradas.json"
    )
    parser.add_argument(
        "--analizar", action="store_true", help="Etapa 2: analizar filtradas.json con el LLM → DB"
    )
    parser.add_argument(
        "--importar", action="store_true", help="Etapas 1 y 2 en un solo paso"
    )
    parser.add_argument(
        "--listar-perfiles", action="store_true", help="Listar perfiles disponibles"
    )
    args = parser.parse_args()

    init_db()

    if args.listar_perfiles:
        perfiles = get_perfiles()
        print("\nPerfiles disponibles:")
        for p in perfiles:
            activo = "✅" if p["activo"] else "  "
            print(f"  {activo} [{p['id']}] {p['nombre']}")
        return

    if args.filtrar or args.importar:
        print("🔍 Filtrando raw_data/...")
        stats = filtrar_raw_data()
        stats_sin_ranking = {k: v for k, v in stats.items() if k != "ranking"}
        print(f"✅ Resultado: {stats_sin_ranking}")

    if args.analizar or args.importar:
        print("🤖 Analizando filtradas.json con el LLM...")
        stats = analizar_con_llm()
        print(f"✅ Resultado: {stats}")

    if args.filtrar or args.analizar or args.importar:
        return

    if args.perfil:
        perfiles = get_perfiles()
        perfil = next(
            (p for p in perfiles if p["nombre"].lower() == args.perfil.lower()), None
        )
        if not perfil:
            print(f"❌ Perfil '{args.perfil}' no encontrado. Usa --listar-perfiles")
            return
        activar_perfil(perfil["id"])
        print(f"✅ Perfil activado: {perfil['nombre']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
