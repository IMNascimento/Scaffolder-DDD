#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, stat, subprocess, sys
from datetime import datetime
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"

DEFAULTS = {
    "project_name": "fastapi-ddd-service",
    "module_name": "app",
    "context": "customer",
    "api_prefix": "/api",
}

EXECUTABLES = {"scripts/wait-for-db.sh", "scripts/dev.sh", "scripts/migrate.sh"}

BASE_LIBS = [
    # API / Core
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "pydantic-settings",
    # DB
    "sqlalchemy",
    "asyncpg",
    "alembic",
    # DX/Logs/Tests
    "structlog",
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "ruff",
    "mypy",
    "pre-commit",
]


def render_file(src: Path, dst: Path, vars: dict) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    content = Template(text).safe_substitute(vars)
    dst.write_text(content, encoding="utf-8")
    rel = dst.relative_to(vars["project_dir"]) if "project_dir" in vars else dst
    if str(rel).replace("\\", "/") in EXECUTABLES:
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)


def copy_templates(vars: dict) -> None:
    project_dir: Path = vars["project_dir"]
    for src in TPL.rglob("*.tmpl"):
        rel = src.relative_to(TPL)
        rel_str = str(rel.with_suffix("")).replace("${context}", vars["context"])  # paths
        dst = project_dir / rel_str
        render_file(src, dst, vars)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def venv_paths(project_dir: Path):
    venv = project_dir / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    pip = venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    return venv, py, pip


def bootstrap(project_dir: Path, vars: dict, create_venv: bool) -> None:
    if create_venv:
        run([sys.executable, "-m", "venv", ".venv"], cwd=project_dir)
        venv, py, pip = venv_paths(project_dir)
        # Instala libs sem versão fixa (sempre as mais novas)
        run([str(pip), "install", "-U", *BASE_LIBS], cwd=project_dir)
        # Gera requirements via pip freeze
        req = run([str(pip), "freeze"], cwd=project_dir, check=True)
        with (project_dir / "requirements.txt").open("wb") as f:
            # subprocess.run com capture_output=False não retorna stdout; usamos outra chamada
            pass
        # Reexecuta freeze capturando saída
        out = subprocess.check_output([str(pip), "freeze"], cwd=str(project_dir))
        (project_dir / "requirements.txt").write_bytes(out)
    else:
        print("[info] Pulei venv/instalação (use --venv para automatizar)")

    # Alembic: cria estrutura com template oficial e patcha env.py
    _, py, pip = venv_paths(project_dir)
    run([str(py), "-m", "alembic", "init", "-t", "async", "alembic"], cwd=project_dir)
    patch_alembic_env(project_dir, vars)


def patch_alembic_env(project_dir: Path, vars: dict) -> None:
    env_py = project_dir / "alembic" / "env.py"
    if not env_py.exists():
        print("[warn] alembic/env.py não encontrado para patch")
        return
    content = env_py.read_text(encoding="utf-8")
    # Inserir import do Base/engine e do modelo do contexto
    inject = (
        "from app.core.db import Base, engine\n"
        f"from app.infrastructure.{vars['context']} import models  # noqa: F401\n"
        "target_metadata = Base.metadata\n"
    )
    # Remover alvos antigos e injetar nossos
    content = content.replace("target_metadata = None\n", "")
    # Ajeitar offline/online para usar engine existente
    content = content.replace(
        "def run_migrations_offline():",
        (
            "def run_migrations_offline():\n"
            "    url = engine.url.render_as_string(hide_password=False)\n"
            "    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)"
        ),
    )
    content = content.replace(
        "def run_migrations_online():",
        (
            "def run_migrations_online():\n"
            "    connectable = engine.sync_engine"
        ),
    )
    # Garante imports necessários
    if "from app.core.db import Base, engine" not in content:
        content = content.replace("from alembic import context\n", "from alembic import context\n" + inject)
    env_py.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FastAPI DDD Foundry v2 — Scaffolder (sem Poetry/Makefile, latest libs)")
    p.add_argument("name", nargs="?", default=DEFAULTS["project_name"], help="Nome do diretório/projeto")
    p.add_argument("--module", dest="module_name", default=DEFAULTS["module_name"], help="Pacote raiz (ex.: app)")
    p.add_argument("--context", dest="context", default=DEFAULTS["context"], help="Bounded context inicial (ex.: customer)")
    p.add_argument("--api-prefix", dest="api_prefix", default=DEFAULTS["api_prefix"], help="Prefixo da API (ex.: /api)")
    p.add_argument("--venv", action="store_true", help="Criar .venv, instalar libs mais novas e gerar requirements.txt via pip freeze")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    project_dir = (Path.cwd() / args.name).resolve()
    if project_dir.exists() and any(project_dir.iterdir()):
        print(f"[err] diretório {project_dir} não está vazio")
        sys.exit(2)

    vars = {
        "project_name": args.name,
        "module_name": args.module_name,
        "context": args.context,
        "ContextCap": args.context.capitalize(),
        "api_prefix": args.api_prefix,
        "year": datetime.now().strftime("%Y"),
        "date": datetime.now().strftime("%Y_%m_%d"),
        "project_dir": project_dir,
    }

    print(f"[+] Gerando em {project_dir}")
    copy_templates(vars)

    # opcional: bootstrap venv + libs + alembic init
    bootstrap(project_dir, vars, create_venv=args.venv)

    print("\n[ok] Projeto criado!")
    print(f"  cd {args.name}")
    print("  cp .env.example .env  # ajuste variáveis (DB/CORS)")
    if not args.venv:
        print("  python -m venv .venv && . .venv/bin/activate && pip install -U -r requirements.bootstrap.txt && pip freeze > requirements.txt")
        print("  # depois, inicialize o Alembic manualmente se preferir:\n  python -m alembic init -t async alembic")
    print("  # migrações e dev server:\n  ./scripts/migrate.sh\n  ./scripts/dev.sh")
    print("  # ou Docker:\n  docker compose up -d --build")

if __name__ == "__main__":
    main()