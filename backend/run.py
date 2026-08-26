import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db
from backend.pipeline import filtrar_raw_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Tracker V1")
    parser.add_argument("--filtrar", "--importar", action="store_true", dest="filtrar", help="Procesa raw_data y actualiza el ranking")
    args = parser.parse_args()
    init_db()

    if not args.filtrar:
        parser.print_help()
        return

    resultado = filtrar_raw_data()
    if resultado.get("error"):
        print(f"Error: {resultado['error']}")
        raise SystemExit(1)
    print(resultado["stats"])


if __name__ == "__main__":
    main()
