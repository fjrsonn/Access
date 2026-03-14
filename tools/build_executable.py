#!/usr/bin/env python3
"""Build do executável do sistema via PyInstaller."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


APP_NAME = "ControleAcesso"
ENTRYPOINT = "main.py"
DATA_FILES = [
    "dados",
    "dadosend.json",
    "dadosinit.json",
    "encomendasend.json",
    "encomendasinit.json",
    "analises.json",
    "avisos.json",
    "orientacoes.json",
    "observacoes.json",
    "keyword_rules.json",
    "config",
    "prompts",
]


def _run(cmd: list[str]) -> None:
    print("[build]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _ensure_dependencies() -> None:
    _run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    _run([sys.executable, "-m", "pip", "install", "pyinstaller", "pillow"])


def _ensure_logo(repo_root: Path) -> Path:
    _run([sys.executable, str(repo_root / "tools" / "create_logo.py")])
    icon_path = repo_root / "assets" / "access_logo.ico"
    if not icon_path.exists():
        raise FileNotFoundError(f"Ícone não encontrado: {icon_path}")
    return icon_path


def _build_pyinstaller_command(repo_root: Path, icon_path: Path) -> list[str]:
    add_data_sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--icon",
        str(icon_path),
    ]

    for item in DATA_FILES:
        src = repo_root / item
        if src.exists():
            dst = item if src.is_dir() else "."
            cmd.extend(["--add-data", f"{src}{add_data_sep}{dst}"])

    cmd.append(str(repo_root / ENTRYPOINT))
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Build do executável ControleAcesso")
    parser.add_argument("--dry-run", action="store_true", help="Apenas exibe o comando final de build")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    if args.dry_run:
        icon_path = repo_root / "assets" / "access_logo.ico"
        command = _build_pyinstaller_command(repo_root, icon_path)
        print("\nComando PyInstaller gerado:\n")
        print(" ".join(command))
        return 0

    _ensure_dependencies()
    icon_path = _ensure_logo(repo_root)
    command = _build_pyinstaller_command(repo_root, icon_path)
    _run(command)
    print("\nBuild concluído.")
    print(f"- Executável/pasta: {repo_root / 'dist' / APP_NAME}")
    print("- Atalho de desktop: crie um atalho apontando para o executável gerado em dist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
