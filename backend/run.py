"""
Entry point del pipeline — ejecución manual.
Uso:
  python run.py --perfil "Frontend React Senior"
  python run.py --importar
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, activar_perfil, get_perfiles
from backend.pipeline import importar_raw_data


def main():
    parser = argparse.ArgumentParser(description="Job Tracker Pipeline")
    parser.add_argument("--perfil", type=str, help="Nombre del perfil a activar y usar")
    parser.add_argument(
        "--importar", action="store_true", help="Importar JSONs de raw_data/"
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

    if args.importar:
        print("📂 Importando raw_data/...")
        stats = importar_raw_data()
        print(f"✅ Resultado: {stats}")
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
