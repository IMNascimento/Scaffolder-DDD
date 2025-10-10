#!/usr/bin/env python3
"""
FastAPI Multi-Architecture Scaffolder — v3.4 (src layout + package=project)
- múltiplos contexts (via --context A --context B ou --context A,B ou --contexts A,B)
- arquitetura/ORM/DB com deps certas
- copia templates por arquitetura/ORM + docker por banco
- pre-commit/ruff/mypy/pytest/coverage via templates/common/**
- patch do Alembic para TODOS os contexts (quando ORM=sqlalchemy)
- cria src/<package>/, onde <package> = nome do projeto normalizado (ou --module)
- força extensão .py quando templates de código vierem sem extensão
- mantém arquivos de topo (LICENSE, CONTRIBUTING.md, etc.) na raiz do projeto
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from string import Template
from typing import Iterable, Literal

ROOT = Path(__file__).resolve().parent
TPL = ROOT / "templates"

ArchType = Literal["ddd", "hexagonal", "mvc", "hybrid"]
OrmType = Literal["sqlalchemy", "peewee"]
DbType = Literal["postgresql", "mysql"]

DEFAULTS = {
    "project_name": "fastapi-service",
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
    "scripts/lint.sh",
}

BASE_LIBS = {
    "common": [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pydantic-settings",
        "httpx",
        "structlog",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "ruff",
        "mypy",
        "pre-commit",
    ],
    "sqlalchemy": ["sqlalchemy", "alembic"],
    "peewee": ["peewee", "peewee-async"],
    "postgresql": [],
    "mysql": [],
}

# Itens que devem continuar na raiz do repositório
TOP_LEVEL_DIRS = {"docs", "scripts", "tests", ".github"}
TOP_LEVEL_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    ".env",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "Conventions.md",
    "ISSUE_TEMPLATE.md",
    "PULL_REQUEST_TEMPLATE.md",
    "pytest.ini",
    "requirements.bootstrap.txt",
    ".pre-commit-config.yaml",
}


def normalize_package_name(name: str) -> str:
    """Normaliza nome do pacote para um identificador Python válido."""
    pkg = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip().lower())
    if not pkg:
        return "apppkg"
    if pkg[0].isdigit():
        pkg = f"pkg_{pkg}"
    return pkg


def get_db_url(db: str, project_name: str) -> str:
    if db == "postgresql":
        return f"postgresql+asyncpg://postgres:postgres@localhost:5432/{project_name}"
    return f"mysql+aiomysql://appuser:apppass@localhost:3306/{project_name}"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def venv_paths(project_dir: Path):
    venv = project_dir / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    pip = venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    return venv, py, pip


def get_dependencies(orm: str, db: str) -> list[str]:
    deps = BASE_LIBS["common"].copy()
    deps.extend(BASE_LIBS[orm])

    # Drivers por banco, ajustando para cada ORM
    if db == "postgresql":
        # SQLAlchemy assíncrono usa asyncpg; Peewee (peewee-async) usa aiopg
        deps.append("psycopg2-binary")
        if orm == "sqlalchemy":
            deps.append("asyncpg")
        else:  # peewee
            deps.append("aiopg")
    elif db == "mysql":
        # Mantém ambos para compat (sync e async)
        deps.extend(["pymysql", "aiomysql"])

    # Compat Python 3.12: fixe peewee-async numa versão estável
    if orm == "peewee":
        deps = [("peewee-async==0.7.1" if d == "peewee-async" else d) for d in deps]

    return deps


def mark_executable_if_needed(dst: Path, project_dir: Path):
    rel = dst.relative_to(project_dir)
    rel_str = str(rel).replace("\\", "/")
    if rel_str in EXECUTABLES:
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)


# ---------------------- helpers de renderização ----------------------

_PY_SNIPPET_RE = re.compile(
    r"(^\s*from\s+\w+)|(^\s*import\s+\w+)|(^\s*class\s+\w+)|(^\s*def\s+\w+)|dataclass|typing",
    re.M,
)


def _looks_like_python(text: str) -> bool:
    return bool(_PY_SNIPPET_RE.search(text))


def _ensure_pkg_in_parents(dst: Path, src_root: Path):
    """Garante __init__.py em cada diretório do pacote dentro de src_root."""
    try:
        src_root = src_root.resolve()
        parent = dst.parent.resolve()
        if src_root not in parent.parents and parent != src_root:
            return
        cur = parent
        while cur != src_root.parent:
            if src_root in cur.parents or cur == src_root:
                initf = cur / "__init__.py"
                if not initf.exists():
                    initf.touch()
            if cur == src_root:
                break
            cur = cur.parent
    except Exception:
        pass


def _arch_conventions(vars: dict) -> dict:
    """
    Define onde ficam os artefatos por arquitetura,
    para ser usado na montagem dos imports/paths.
    """
    module = vars["module_name"]
    arch = vars["arch"]

    # onde ficam os "shared" (db/uow)
    # hybrid/hexagonal => adapters/shared
    # ddd/mvc         => infrastructure/shared (ajuste se seu MVC usar adapters)
    if arch in ("hybrid", "hexagonal"):
        shared_pkg = "adapters"
    else:  # "ddd", "mvc"
        shared_pkg = "infrastructure"

    # base dos repositórios de implementação por contexto
    # ajuste se seu hexagonal usar inbound/outbound diferente
    if arch == "ddd":
        def repo_base(c: str) -> str:
            return f"{module}.infrastructure.{c}.repository"
    elif arch == "hexagonal":
        def repo_base(c: str) -> str:
            return f"{module}.adapters.outbound.{c}.repository"
    elif arch == "mvc":
        def repo_base(c: str) -> str:
            return f"{module}.infrastructure.{c}.repository"
    else:  # "hybrid"
        def repo_base(c: str) -> str:
            return f"{module}.adapters.{c}.repository"

    return {
        "module": module,
        "arch": arch,
        "shared_pkg": shared_pkg,   # ex.: "adapters" | "infrastructure"
        "repo_base": repo_base,     # função que devolve base de import por contexto
    }

def _build_shared_uow_strings(vars: dict) -> dict:
    conv = _arch_conventions(vars)
    module = conv["module"]
    repo_base = conv["repo_base"]
    contexts = list(dict.fromkeys(vars["contexts"]))  # ordem estável

    def Cap(name: str) -> str:
        return "".join(part.capitalize() for part in name.split("_"))

    def prop(name: str) -> str:
        # plural simples: se já termina com 's', mantém
        return name if name.endswith("s") else f"{name}s"

    # Ports do domínio (sempre estável: domain.<context>.repositories)
    domain_repo_imports = "\n".join(
        f"from {module}.domain.{c}.repositories import {Cap(c)}Repository"
        for c in contexts
    )

    # Implementações por ORM, usando a convenção por arquitetura para a base
    sa_adapter_repo_imports = "\n".join(
        f"from {repo_base(c)}.sqlalchemy_{c}_repo import SA{Cap(c)}Repository"
        for c in contexts
    )
    pw_adapter_repo_imports = "\n".join(
        f"from {repo_base(c)}.peewee_{c}_repo import PW{Cap(c)}Repository"
        for c in contexts
    )

    # Propriedades do UoW (um atributo por contexto)
    uow_properties = "".join(
        f"    {prop(c)}: {Cap(c)}Repository\n"
        for c in contexts
    )

    # Caches
    uow_cache_fields = "".join(
        f"        self._{prop(c)}: {Cap(c)}Repository | None = None\n"
        for c in contexts
    )

    # Inits no __aenter__
    sa_uow_repo_inits = "".join(
        f"        self._{prop(c)} = SA{Cap(c)}Repository(self._session)\n"
        for c in contexts
    )
    pw_uow_repo_inits = "".join(
        f"        self._{prop(c)} = PW{Cap(c)}Repository(self._mgr)\n"
        for c in contexts
    )

    # Resets no __aexit__
    uow_cache_resets = "".join(
        f"            self._{prop(c)} = None\n"
        for c in contexts
    )

    # Getters
    uow_properties_getters = "\n".join(
        f"    @property\n"
        f"    def {prop(c)}(self) -> {Cap(c)}Repository:\n"
        f"        assert self._{prop(c)} is not None, \"UoW fora do contexto (use `async with`)\"\n"
        f"        return self._{prop(c)}\n"
        for c in contexts
    )

    return {
        "domain_repo_imports": domain_repo_imports,
        "sa_adapter_repo_imports": sa_adapter_repo_imports,
        "pw_adapter_repo_imports": pw_adapter_repo_imports,
        "uow_properties": uow_properties,
        "uow_cache_fields": uow_cache_fields,
        "sa_uow_repo_inits": sa_uow_repo_inits,
        "pw_uow_repo_inits": pw_uow_repo_inits,
        "uow_cache_resets": uow_cache_resets,
        "uow_properties_getters": uow_properties_getters,
        # também exporta shared_pkg para os templates
        "shared_pkg": conv["shared_pkg"],
    }


def _is_top_level_file(dst: Path, project_dir: Path) -> bool:
    """Retorna True se o destino estiver na raiz do projeto e for um dos TOP_LEVEL_FILES."""
    try:
        rel = PurePosixPath(dst.resolve().relative_to(project_dir.resolve()).as_posix())
    except Exception:
        return False
    name = rel.name  # já sem .tmpl
    return rel.parent == PurePosixPath(".") and name in TOP_LEVEL_FILES

def _walk_and_render(base_dir: Path, dst_root: Path, contexts: list[str], vars: dict) -> None:
    """
    Percorre base_dir e renderiza todos os *.tmpl respeitando:
      - substituição de ${context} (duplicação)
      - remapeamento para src/<package>/...
      - render_file(...)
    """
    if not base_dir.exists():
        return
    for src in base_dir.rglob("*.tmpl"):
        rel = src.relative_to(base_dir)
        _render_for_each_context(src, rel, dst_root, contexts, vars)


def _emit_arch_neutral(arch_root: Path, dst_root: Path, contexts: list[str], vars: dict) -> None:
    """
    Copia TUDO da arquitetura que NÃO esteja dentro de 'orm/'.
    Ex.: templates/hybrid/src/app/**, templates/hybrid/docs/**, etc.
    """
    if not arch_root.exists():
        return
    for src in arch_root.rglob("*.tmpl"):
        rel = src.relative_to(arch_root)
        parts = rel.parts
        if parts and parts[0] == "orm":
            continue  # pula conteúdo específico de ORM
        _render_for_each_context(src, rel, dst_root, contexts, vars)


def _emit_arch_combo(arch_root: Path, orm: str, db: str, dst_root: Path, contexts: list[str], vars: dict) -> None:
    """
    Copia SOMENTE o combo selecionado dentro da arquitetura:
      - orm/<orm>/_common/**        (ex.: settings.py)
      - orm/<orm>/_context/**       (ex.: models/repository por contexto)
      - orm/<orm>/<db>/**           (ex.: db.py/uow.py/main.py do combo)
    """
    base = arch_root / "orm" / orm

    # Parte comum do ORM
    _walk_and_render(base / "_common", dst_root, contexts, vars)

    # Arquivos por contexto do ORM
    _walk_and_render(base / "_context", dst_root, contexts, vars)

    # Combo ORM×DB
    _walk_and_render(base / db, dst_root, contexts, vars)
    
def render_file(src: Path, dst: Path, vars: dict) -> None:
    """
    Renderiza o template e aplica:
    - fallback para imports "app." -> "<package>."
    - força extensão .py somente para arquivos dentro de src/<package> que pareçam Python
    - NUNCA força .py em arquivos de topo (LICENSE, README, etc.)
    - cria __init__.py ao longo do caminho dentro de src/<package>
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")

    # Renderiza placeholders
    content = Template(text).safe_substitute(vars)

    # Fallback: corrige imports "app." legados para o nome real do pacote
    module = vars["module_name"]
    content = re.sub(r"\bfrom\s+app\.", f"from {module}.", content)
    content = re.sub(r"\bimport\s+app\.", f"import {module}.", content)

    # Decide se deve forçar ".py"
    force_py = False
    if dst.suffix == "" and _looks_like_python(content):
        # 1) nunca para arquivos de topo (LICENSE, README, etc.)
        if not _is_top_level_file(dst, vars["project_dir"]):
            # 2) apenas se o destino estiver dentro de src/<package>/**
            try:
                rel = PurePosixPath(
                    dst.resolve().relative_to(vars["project_dir"].resolve()).as_posix()
                )
            except Exception:
                rel = PurePosixPath(dst.as_posix())

            parts = rel.parts
            in_src_pkg = (
                len(parts) >= 3
                and parts[0] == "src"
                and parts[1] == vars["package_name"]
            )
            if in_src_pkg:
                force_py = True

    if force_py:
        dst = dst.with_suffix(".py")

    dst.write_text(content, encoding="utf-8")
    mark_executable_if_needed(dst, vars["project_dir"])

    # Garante __init__.py apenas dentro de src/<package>
    _ensure_pkg_in_parents(dst, vars["project_dir"] / "src" / vars["package_name"])



# ---------------------- mapeamento de caminhos ----------------------

def _apply_ctx_in_path(rel: Path, ctx: str) -> Path:
    return Path(str(rel.with_suffix("")).replace("${context}", ctx))


def _remap_dst_rel_for_package(rel_from_base: Path, package_name: str) -> Path:
    """
    Reposiciona templates para o layout 'src/<package>/**' quando apropriado.
    Agora detecta 'files de topo' mesmo quando o template termina com .tmpl.
    """
    s = str(rel_from_base).replace("\\", "/")

    # 1) mapeamentos diretos 'src/app' e 'app'
    if s.startswith("src/app/"):
        return Path(s.replace("src/app/", f"src/{package_name}/", 1))
    if s.startswith("app/"):
        return Path(s.replace("app/", f"src/{package_name}/", 1))

    p = PurePosixPath(s)
    parts = p.parts

    # Nome do arquivo para checar 'top-level', removendo o sufixo .tmpl
    base_name = parts[-1] if parts else ""
    base_name_no_tmpl = base_name[:-5] if base_name.endswith(".tmpl") else base_name

    # 2) se começa por 'src/' e ainda não é 'src/<package>/', injeta package
    if len(parts) >= 2 and parts[0] == "src" and parts[1] != package_name:
        new_parts = ("src", package_name, *parts[1:])
        return Path(PurePosixPath(*new_parts))

    # 3) se é diretório/arquivo que deve ficar no topo do repo, respeite
    # (agora compara com o nome sem .tmpl)
    if parts and (parts[0] in TOP_LEVEL_DIRS or base_name_no_tmpl in TOP_LEVEL_FILES):
        return Path(s)

    # 4) caso contrário, qualquer coisa “solta” vai para 'src/<package>/...'
    return Path(PurePosixPath("src") / package_name / p)


def _render_for_each_context(
    src_abs: Path,
    rel_from_base: Path,
    dst_root: Path,
    contexts: list[str],
    base_vars: dict,
):
    rel_str = str(rel_from_base)
    has_ctx = "${context}" in rel_str

    if has_ctx:
        for ctx in contexts:
            ctx_rel = _apply_ctx_in_path(rel_from_base, ctx)
            ctx_rel = _remap_dst_rel_for_package(ctx_rel, base_vars["package_name"])
            dst = dst_root / ctx_rel.with_suffix("")  # remove .tmpl
            vars_ctx = base_vars | {"context": ctx, "ContextCap": ctx.capitalize()}
            render_file(src_abs, dst, vars_ctx)
    else:
        adj_rel = _remap_dst_rel_for_package(rel_from_base, base_vars["package_name"])
        dst = dst_root / adj_rel.with_suffix("")  # remove .tmpl
        render_file(src_abs, dst, base_vars)


# ---------------------- cópia de templates ----------------------

def copy_templates(vars: dict, docker_enabled: bool, contexts: list[str]) -> None:
    project_dir: Path = vars["project_dir"]
    arch: str = vars["arch"]
    orm: str = vars["orm"]
    db: str = vars["db"]

    print("\n📁 Copiando templates...")

    # 1) COMMON (sempre)
    common_tpl = TPL / "common"
    _walk_and_render(common_tpl, project_dir, contexts, vars)

    # 2) ARQUITETURA (somente a escolhida)
    arch_root = TPL / arch

    # 2.1) NEUTRO da arquitetura (qualquer coisa FORA de 'orm/')
    _emit_arch_neutral(arch_root, project_dir, contexts, vars)

    # 2.2) COMBO (ORM × DB) da arquitetura
    _emit_arch_combo(arch_root, orm, db, project_dir, contexts, vars)

    # 3) DOCKER (condicional por DB)
    if docker_enabled:
        docker_base = TPL / "docker"
        compose_src = docker_base / db / "docker-compose.yml.tmpl"
        if compose_src.exists():
            render_file(compose_src, project_dir / "docker-compose.yml", vars)
            print(f"   ✓ docker-compose.yml ({db})")
        dockerfile_src = docker_base / "Dockerfile.tmpl"
        if dockerfile_src.exists():
            render_file(dockerfile_src, project_dir / "Dockerfile", vars)
            print("   ✓ Dockerfile")


# ---------------------- Bootstrap / Alembic ----------------------

def bootstrap(project_dir: Path, vars: dict, create_venv: bool) -> None:
    if not create_venv:
        print("\n[info] Pulando criação de venv (use --venv para automatizar)")
        return

    print("\n[+] Criando ambiente virtual...")
    run([sys.executable, "-m", "venv", ".venv"], cwd=project_dir)

    _, py, pip = venv_paths(project_dir)

    print("\n[+] Atualizando pip...")
    run([str(py), "-m", "pip", "install", "-U", "pip"], cwd=project_dir)

    print("\n[+] Instalando dependências...")
    deps = get_dependencies(vars["orm"], vars["db"])
    run([str(py), "-m", "pip", "install", "-U"] + deps, cwd=project_dir)

    print("\n[+] Gerando requirements.txt...")
    out = subprocess.check_output([str(py), "-m", "pip", "freeze"], cwd=str(project_dir))
    (project_dir / "requirements.txt").write_bytes(out)

    if vars["orm"] == "sqlalchemy":
        print("\n[+] Inicializando Alembic...")
        run([str(py), "-m", "alembic", "init", "-t", "async", "alembic"], cwd=project_dir)
        patch_alembic_env(project_dir, vars, contexts=vars["contexts"])


def _models_import_path(arch: str, context: str, module_name: str) -> str:
    if arch in ("ddd", "hybrid"):
        return f"{module_name}.infrastructure.{context}"
    if arch == "hexagonal":
        return f"{module_name}.adapters.outbound.{context}"
    return f"{module_name}.models"


def patch_alembic_env(project_dir: Path, vars: dict, contexts: Iterable[str]) -> None:
    env_py = project_dir / "alembic" / "env.py"
    if not env_py.exists():
        print("[warn] alembic/env.py não encontrado")
        return

    content = env_py.read_text(encoding="utf-8")

    module_name = vars["module_name"]
    import_lines = [
        f"from {_models_import_path(vars['arch'], ctx, module_name)} import models  # noqa: F401"
        for ctx in contexts
    ]

    inject = (
        f"from {module_name}.core.db import Base, engine\n"
        + "\n".join(import_lines)
        + "\n"
        + "target_metadata = Base.metadata\n"
    )

    if f"from {module_name}.core.db import Base, engine" not in content:
        content = content.replace("from alembic import context\n", f"from alembic import context\n{inject}")

    content = content.replace("target_metadata = None\n", "")

    env_py.write_text(content, encoding="utf-8")


# ---------------------- CLI / Helpers ----------------------

def _normalize_contexts(args: argparse.Namespace) -> list[str]:
    out: list[str] = []

    def push_many(raw: str | None):
        if not raw:
            return
        for part in raw.split(","):
            p = part.strip()
            if p:
                out.append(p)

    if isinstance(args.context, list):
        for item in args.context:
            push_many(item)
    else:
        push_many(args.context)
    push_many(args.contexts)

    if not out:
        out = ["customer"]

    norm = [c.strip().replace(" ", "_").lower() for c in out]
    uniq: list[str] = []
    seen = set()
    for c in norm:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="FastAPI Multi-Architecture Scaffolder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python foundry.py my-api --arch hybrid --orm sqlalchemy --db postgresql \
    --context customer --context order --venv

  python foundry.py svc-orders --arch hexagonal --orm peewee --db mysql \
    --contexts order,payment --no-docker
""",
    )
    p.add_argument("name", help="Nome do projeto/diretório")
    p.add_argument(
        "--module",
        dest="module_name",
        default=None,  # será inferido do name se não for fornecido
        help="Pacote raiz (padrão: nome do projeto normalizado)",
    )
    p.add_argument("--api-prefix", dest="api_prefix", default=DEFAULTS["api_prefix"], help="Prefixo da API (padrão: /api)")
    p.add_argument("--context", action="append", help="Bounded context (pode repetir ou usar vírgula)")
    p.add_argument("--contexts", help="Lista separada por vírgula (ex.: customer,order)")
    p.add_argument("--arch", choices=["ddd", "hexagonal", "mvc", "hybrid"], default=DEFAULTS["arch"], help="Arquitetura")
    p.add_argument("--orm", choices=["sqlalchemy", "peewee"], default=DEFAULTS["orm"], help="ORM")
    p.add_argument("--db", choices=["postgresql", "mysql"], default=DEFAULTS["db"], help="Banco de dados")
    p.add_argument("--venv", action="store_true", help="Criar .venv e instalar dependências automaticamente")
    p.add_argument("--no-docker", action="store_true", help="Não gerar arquivos Docker")
    return p.parse_args()


def print_summary(vars: dict) -> None:
    print("\n" + "=" * 72)
    print("✨ PROJETO CRIADO COM SUCESSO!")
    print("=" * 72)
    print(f"\n📦 Projeto: {vars['project_name']}")
    print(f"🏗️  Arquitetura: {vars['arch'].upper()}")
    print(f"💾 ORM: {vars['orm'].upper()}")
    print(f"🗄️  Database: {vars['db'].upper()}")
    print(f"📁 Pacote: {vars['package_name']}")
    print(f"📁 Contexts: {', '.join(vars['contexts'])}")

    print("\n📚 Próximos passos:\n")
    print(f"  cd {vars['project_name']}")
    print("  cp .env.example .env  # ajuste variáveis")

    if not vars.get("venv_created"):
        print("\n  python -m venv .venv")
        print("  source .venv/bin/activate  # Windows: .venv\\Scripts\\activate")
        print("  pip install -r requirements.txt")

    if vars["orm"] == "sqlalchemy":
        print("\n  ./scripts/migrate.sh")

    print("\n  ./scripts/dev.sh")

    if vars["docker_enabled"]:
        print("\n  docker compose up -d --build")

    print("\n🔗 http://localhost:8000")
    print(f"   http://localhost:8000{vars['api_prefix']}/docs")
    print("\n" + "=" * 72 + "\n")


def main() -> None:
    args = parse_args()
    contexts = _normalize_contexts(args)

    project_dir = (Path.cwd() / args.name).resolve()
    if project_dir.exists() and any(project_dir.iterdir()):
        print(f"❌ Erro: diretório {project_dir} não está vazio")
        sys.exit(2)

    package_name = normalize_package_name(args.module_name or args.name)

    vars = {
        "project_name": args.name,
        "module_name": package_name,  # compat
        "package_name": package_name,
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
        "contexts": contexts,
        "context": contexts[0],
        "ContextCap": contexts[0].capitalize(),
    }

    uowv = _build_shared_uow_strings(vars)
    vars |= {
        "domain_repo_imports": uowv["domain_repo_imports"],
        "uow_properties": uowv["uow_properties"],
        "uow_cache_fields": uowv["uow_cache_fields"],
        "uow_cache_resets": uowv["uow_cache_resets"],
        "uow_properties_getters": uowv["uow_properties_getters"],
        "shared_pkg": uowv["shared_pkg"],
    }
    if vars["orm"] == "sqlalchemy":
        vars["adapter_repo_imports"] = uowv["sa_adapter_repo_imports"]
        vars["uow_repo_inits"] = uowv["sa_uow_repo_inits"]
    else:
        vars["adapter_repo_imports"] = uowv["pw_adapter_repo_imports"]
        vars["uow_repo_inits"] = uowv["pw_uow_repo_inits"]

    print(f"\n🚀 Gerando projeto: {args.name}")
    print(f"   Arquitetura: {args.arch}")
    print(f"   ORM: {args.orm}")
    print(f"   Database: {args.db}")
    print(f"   Package: {package_name}")
    print(f"   Contexts: {', '.join(contexts)}")

    # cria diretórios base
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "src" / package_name).mkdir(parents=True, exist_ok=True)

    copy_templates(vars, docker_enabled=vars["docker_enabled"], contexts=contexts)
    bootstrap(project_dir, vars, create_venv=args.venv)
    print_summary(vars)


if __name__ == "__main__":
    main()
