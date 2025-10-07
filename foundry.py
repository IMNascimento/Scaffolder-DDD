#!/usr/bin/env python3
"""
FastAPI Multi-Architecture Scaffolder - VERSÃO CORRIGIDA
Escolhe o docker-compose correto baseado no banco de dados

Uso:
    python foundry.py meu-projeto --context customer --db postgresql --venv
"""
from __future__ import annotations
import argparse
import os
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Literal

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"

ArchType = Literal["ddd", "hexagonal", "mvc", "hybrid"]
OrmType = Literal["sqlalchemy", "peewee"]
DbType = Literal["postgresql", "mysql"]

DEFAULTS = {
    "project_name": "fastapi-service",
    "module_name": "app",
    "context": "customer",
    "api_prefix": "/api",
    "arch": "hybrid",
    "orm": "sqlalchemy",
    "db": "postgresql",
}

EXECUTABLES = {
    "scripts/wait-for-db.sh",
    "scripts/dev.sh",
    "scripts/migrate.sh",
    "scripts/test.sh",
    "scripts/lint.sh"
}

BASE_LIBS = {
    "common": [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pydantic-settings",
        "structlog",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "httpx",
        "ruff",
        "mypy",
        "pre-commit",
    ],
    "sqlalchemy": ["sqlalchemy", "alembic"],
    "peewee": ["peewee", "peewee-async"],
    "postgresql": ["asyncpg", "psycopg2-binary"],
    "mysql": ["aiomysql", "pymysql"],
}


def get_db_url(db: str, project_name: str) -> str:
    """Retorna a DATABASE_URL correta para o banco escolhido"""
    if db == "postgresql":
        return f"postgresql+asyncpg://postgres:postgres@localhost:5432/{project_name}"
    else:  # mysql
        return f"mysql+aiomysql://appuser:apppass@localhost:3306/{project_name}"


def render_file(src: Path, dst: Path, vars: dict) -> None:
    """Renderiza template com substituição de variáveis"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    content = Template(text).safe_substitute(vars)
    dst.write_text(content, encoding="utf-8")
    
    rel = dst.relative_to(vars["project_dir"]) if "project_dir" in vars else dst
    rel_str = str(rel).replace("\\", "/")
    
    if rel_str in EXECUTABLES:
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)


def copy_templates(vars: dict) -> None:
    """Copia templates baseado na arquitetura e DB escolhidos"""
    project_dir: Path = vars["project_dir"]
    arch: str = vars["arch"]
    db: str = vars["db"]
    context: str = vars["context"]
    
    print(f"\n📁 Copiando templates...")
    
    # 1. Templates comuns (exceto docker que vem depois)
    common_tpl = TPL / "common"
    if common_tpl.exists():
        for src in common_tpl.rglob("*.tmpl"):
            rel = src.relative_to(common_tpl)
            dst = project_dir / rel.with_suffix("")
            render_file(src, dst, vars)
    
    # 2. Templates específicos da arquitetura
    arch_tpl = TPL / arch
    if arch_tpl.exists():
        for src in arch_tpl.rglob("*.tmpl"):
            # Pular docker-compose.yml e Dockerfile da arquitetura
            # (vamos pegar do templates/docker)
            if src.name in ["docker-compose.yml.tmpl", "Dockerfile.tmpl"]:
                continue
            
            rel = src.relative_to(arch_tpl)
            rel_str = str(rel.with_suffix("")).replace("${context}", context)
            dst = project_dir / rel_str
            render_file(src, dst, vars)
    
    # 3. Docker templates (escolhe o correto baseado no DB)
    docker_base = TPL / "docker"
    
    # docker-compose.yml - escolhe PostgreSQL ou MySQL
    docker_compose_src = docker_base / db / "docker-compose.yml.tmpl"
    if docker_compose_src.exists():
        docker_compose_dst = project_dir / "docker-compose.yml"
        render_file(docker_compose_src, docker_compose_dst, vars)
        print(f"   ✓ docker-compose.yml ({db})")
    
    # Dockerfile - comum para ambos
    dockerfile_src = docker_base / "Dockerfile.tmpl"
    if dockerfile_src.exists():
        dockerfile_dst = project_dir / "Dockerfile"
        render_file(dockerfile_src, dockerfile_dst, vars)
        print(f"   ✓ Dockerfile")
    
    # 4. Templates de ORM (se não for SQLAlchemy padrão)
    if vars["orm"] != "sqlalchemy":
        orm_tpl = TPL / "orm" / vars["orm"]
        if orm_tpl.exists():
            for src in orm_tpl.rglob("*.tmpl"):
                rel = src.relative_to(orm_tpl)
                rel_str = str(rel.with_suffix("")).replace("${context}", context)
                dst = project_dir / rel_str
                render_file(src, dst, vars)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Executa comando shell"""
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def venv_paths(project_dir: Path):
    """Retorna caminhos do virtualenv"""
    venv = project_dir / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    pip = venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    return venv, py, pip


def get_dependencies(arch: str, orm: str, db: str) -> list[str]:
    """Retorna lista de dependências baseado nas escolhas"""
    deps = BASE_LIBS["common"].copy()
    deps.extend(BASE_LIBS[orm])
    deps.extend(BASE_LIBS[db])
    return deps


def bootstrap(project_dir: Path, vars: dict, create_venv: bool) -> None:
    """Bootstrap do projeto: venv, dependências, alembic"""
    if not create_venv:
        print("\n[info] Pulando criação de venv (use --venv para automatizar)")
        return
    
    print("\n[+] Criando ambiente virtual...")
    run([sys.executable, "-m", "venv", ".venv"], cwd=project_dir)
    
    venv, py, pip = venv_paths(project_dir)
    
    # Atualiza pip
    print("\n[+] Atualizando pip...")
    run([str(pip), "install", "-U", "pip"], cwd=project_dir)
    
    # Instala dependências
    deps = get_dependencies(vars["arch"], vars["orm"], vars["db"])
    print(f"\n[+] Instalando dependências...")
    run([str(pip), "install", "-U"] + deps, cwd=project_dir)
    
    # Gera requirements.txt
    print("\n[+] Gerando requirements.txt...")
    out = subprocess.check_output([str(pip), "freeze"], cwd=str(project_dir))
    (project_dir / "requirements.txt").write_bytes(out)
    
    # Inicializa alembic se SQLAlchemy
    if vars["orm"] == "sqlalchemy":
        print("\n[+] Inicializando Alembic...")
        run([str(py), "-m", "alembic", "init", "-t", "async", "alembic"], cwd=project_dir)
        patch_alembic_env(project_dir, vars)


def patch_alembic_env(project_dir: Path, vars: dict) -> None:
    """Patcha alembic/env.py para usar nossa configuração"""
    env_py = project_dir / "alembic" / "env.py"
    if not env_py.exists():
        print("[warn] alembic/env.py não encontrado")
        return
    
    content = env_py.read_text(encoding="utf-8")
    
    # Inject imports based on architecture
    if vars["arch"] in ["ddd", "hybrid"]:
        models_path = f"app.{'infrastructure' if vars['arch'] == 'ddd' else 'adapters'}.{vars['context']}"
    elif vars["arch"] == "hexagonal":
        models_path = f"app.adapters.outbound.{vars['context']}"
    else:  # mvc
        models_path = "app.models"
    
    inject = (
        "from app.core.db import Base, engine\n"
        f"from {models_path} import models  # noqa: F401\n"
        "target_metadata = Base.metadata\n"
    )
    
    content = content.replace("target_metadata = None\n", "")
    if "from app.core.db import Base, engine" not in content:
        content = content.replace("from alembic import context\n", f"from alembic import context\n{inject}")
    
    env_py.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse argumentos da linha de comando"""
    p = argparse.ArgumentParser(
        description="FastAPI Multi-Architecture Scaffolder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Híbrido + SQLAlchemy + PostgreSQL (com venv)
  python foundry.py meu-projeto --context customer --venv
  
  # Hexagonal + Peewee + MySQL
  python foundry.py api-orders --arch hexagonal --orm peewee --db mysql --context order
  
  # MVC + SQLAlchemy + PostgreSQL
  python foundry.py blog-api --arch mvc --context post --venv
        """
    )
    
    p.add_argument("name", help="Nome do projeto/diretório")
    p.add_argument("--module", dest="module_name", default=DEFAULTS["module_name"],
                   help="Nome do módulo Python (padrão: app)")
    p.add_argument("--context", dest="context", default=DEFAULTS["context"],
                   help="Bounded context inicial (ex: customer, order)")
    p.add_argument("--api-prefix", dest="api_prefix", default=DEFAULTS["api_prefix"],
                   help="Prefixo da API (padrão: /api)")
    
    p.add_argument("--arch", choices=["ddd", "hexagonal", "mvc", "hybrid"],
                   default=DEFAULTS["arch"], help="Arquitetura do projeto (padrão: hybrid)")
    p.add_argument("--orm", choices=["sqlalchemy", "peewee"], default=DEFAULTS["orm"],
                   help="ORM a ser usado (padrão: sqlalchemy)")
    p.add_argument("--db", choices=["postgresql", "mysql"], default=DEFAULTS["db"],
                   help="Banco de dados (padrão: postgresql)")
    
    p.add_argument("--venv", action="store_true",
                   help="Criar .venv e instalar dependências automaticamente")
    p.add_argument("--no-docker", action="store_true",
                   help="Não gerar arquivos Docker")
    
    return p.parse_args()


def print_summary(vars: dict) -> None:
    """Imprime resumo do projeto criado"""
    print("\n" + "="*70)
    print("✨ PROJETO CRIADO COM SUCESSO!")
    print("="*70)
    print(f"\n📦 Projeto: {vars['project_name']}")
    print(f"🏗️  Arquitetura: {vars['arch'].upper()}")
    print(f"💾 ORM: {vars['orm'].upper()}")
    print(f"🗄️  Database: {vars['db'].upper()}")
    print(f"📁 Context: {vars['context']}")
    
    print("\n📚 Próximos passos:\n")
    print(f"  cd {vars['project_name']}")
    print("  cp .env.example .env")
    print("  # Edite o .env se necessário")
    
    if not vars.get("venv_created"):
        print("\n  # Criar ambiente virtual:")
        print("  python -m venv .venv")
        print("  source .venv/bin/activate  # Windows: .venv\\Scripts\\activate")
        print("  pip install -r requirements.txt")
    
    if vars["orm"] == "sqlalchemy":
        print("\n  # Executar migrações:")
        print("  ./scripts/migrate.sh")
    
    print("\n  # Iniciar servidor:")
    print("  ./scripts/dev.sh")
    
    print("\n  # Ou com Docker:")
    print("  docker compose up -d --build")
    
    print("\n🔗 URLs:")
    print("  API: http://localhost:8000")
    print(f"  Docs: http://localhost:8000{vars['api_prefix']}/docs")
    
    print("\n" + "="*70 + "\n")


def main() -> None:
    """Main function"""
    args = parse_args()
    project_dir = (Path.cwd() / args.name).resolve()
    
    if project_dir.exists() and any(project_dir.iterdir()):
        print(f"❌ Erro: diretório {project_dir} não está vazio")
        sys.exit(2)
    
    vars = {
        "project_name": args.name,
        "module_name": args.module_name,
        "context": args.context,
        "ContextCap": args.context.capitalize(),
        "api_prefix": args.api_prefix,
        "arch": args.arch,
        "orm": args.orm,
        "db": args.db,
        "db_url": get_db_url(args.db, args.name),
        "year": datetime.now().strftime("%Y"),
        "date": datetime.now().strftime("%Y_%m_%d"),
        "project_dir": project_dir,
        "venv_created": args.venv,
        "docker_enabled": not args.no_docker,
    }
    
    print(f"\n🚀 Gerando projeto: {args.name}")
    print(f"   Arquitetura: {args.arch}")
    print(f"   ORM: {args.orm}")
    print(f"   Database: {args.db}")
    
    # Cria estrutura
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Copia templates
    copy_templates(vars)
    
    # Bootstrap
    bootstrap(project_dir, vars, create_venv=args.venv)
    
    # Resumo
    print_summary(vars)


if __name__ == "__main__":
    main()
