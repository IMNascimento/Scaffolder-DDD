#!/usr/bin/env python3
"""
Script para configurar automaticamente a estrutura do Scaffolder-DDD
Cria todas as pastas e arquivos básicos necessários.

Uso:
    python setup_scaffolder.py
"""
from pathlib import Path
import sys

# Estrutura de diretórios
STRUCTURE = {
    "templates/common/docs": [],
    "templates/common/scripts": [],
    "templates/common/.github/workflows": [],
    "templates/common/tests": [],
    
    # Hybrid architecture
    "templates/hybrid/src/app/core": [],
    "templates/hybrid/src/app/domain/${context}": [],
    "templates/hybrid/src/app/domain/ports": [],
    "templates/hybrid/src/app/domain/events": [],
    "templates/hybrid/src/app/domain/value_objects": [],
    "templates/hybrid/src/app/domain/services": [],
    "templates/hybrid/src/app/application/${context}": [],
    "templates/hybrid/src/app/adapters/${context}": [],
    "templates/hybrid/src/app/adapters/uow": [],
    "templates/hybrid/src/app/api/deps": [],
    "templates/hybrid/src/app/api/routers": [],
    "templates/hybrid/src/app/api/schemas": [],
    
    # DDD pure
    "templates/ddd/src/app/core": [],
    "templates/ddd/src/app/domain/${context}": [],
    "templates/ddd/src/app/application/${context}": [],
    "templates/ddd/src/app/infrastructure/${context}": [],
    "templates/ddd/src/app/infrastructure/uow": [],
    "templates/ddd/src/app/api/routers": [],
    "templates/ddd/src/app/api/schemas": [],
    
    # Hexagonal
    "templates/hexagonal/src/app/core": [],
    "templates/hexagonal/src/app/domain/${context}": [],
    "templates/hexagonal/src/app/ports": [],
    "templates/hexagonal/src/app/adapters/inbound": [],
    "templates/hexagonal/src/app/adapters/outbound/${context}": [],
    "templates/hexagonal/src/app/api/routers": [],
    
    # MVC
    "templates/mvc/src/app/models": [],
    "templates/mvc/src/app/views": [],
    "templates/mvc/src/app/controllers": [],
    "templates/mvc/src/app/services": [],
    "templates/mvc/src/app/core": [],
    
    # ORM templates
    "templates/orm/sqlalchemy/core": [],
    "templates/orm/peewee/core": [],
    "templates/orm/peewee/scripts": [],
}

# Arquivos __init__.py que devem ser criados (vazios)
INIT_FILES = [
    # Hybrid
    "templates/hybrid/src/app/__init__.py.tmpl",
    "templates/hybrid/src/app/core/__init__.py.tmpl",
    "templates/hybrid/src/app/domain/__init__.py.tmpl",
    "templates/hybrid/src/app/domain/${context}/__init__.py.tmpl",
    "templates/hybrid/src/app/domain/ports/__init__.py.tmpl",
    "templates/hybrid/src/app/domain/events/__init__.py.tmpl",
    "templates/hybrid/src/app/domain/value_objects/__init__.py.tmpl",
    "templates/hybrid/src/app/domain/services/__init__.py.tmpl",
    "templates/hybrid/src/app/application/__init__.py.tmpl",
    "templates/hybrid/src/app/application/${context}/__init__.py.tmpl",
    "templates/hybrid/src/app/adapters/__init__.py.tmpl",
    "templates/hybrid/src/app/adapters/${context}/__init__.py.tmpl",
    "templates/hybrid/src/app/adapters/uow/__init__.py.tmpl",
    "templates/hybrid/src/app/api/__init__.py.tmpl",
    "templates/hybrid/src/app/api/deps/__init__.py.tmpl",
    "templates/hybrid/src/app/api/routers/__init__.py.tmpl",
    "templates/hybrid/src/app/api/schemas/__init__.py.tmpl",
    
    # MVC
    "templates/mvc/src/app/__init__.py.tmpl",
    "templates/mvc/src/app/models/__init__.py.tmpl",
    "templates/mvc/src/app/views/__init__.py.tmpl",
    "templates/mvc/src/app/controllers/__init__.py.tmpl",
    "templates/mvc/src/app/services/__init__.py.tmpl",
    "templates/mvc/src/app/core/__init__.py.tmpl",
    
    # Tests
    "templates/common/tests/__init__.py.tmpl",
]

# Arquivos de placeholder que devem ser criados
PLACEHOLDER_FILES = {
    "templates/common/.env.example.tmpl": """APP_NAME=${project_name}
ENV=dev
API_PREFIX=${api_prefix}
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/${project_name}
DB_ECHO=false
""",
    
    "templates/common/.gitignore.tmpl": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
""",

    "templates/common/requirements.bootstrap.txt.tmpl": """fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
asyncpg
alembic
structlog
pytest
pytest-asyncio
pytest-cov
httpx
ruff
mypy
pre-commit
""",

    "templates/common/pytest.ini.tmpl": """[tool:pytest]
testpaths = tests
asyncio_mode = auto
addopts = 
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
    -v
""",

    "templates/common/pyproject.toml.tmpl": """[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "PT", "SIM", "RUF"]
ignore = ["E501", "B008"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = true
""",
}


def create_structure():
    """Cria toda a estrutura de diretórios"""
    print("🏗️  Criando estrutura de diretórios...")
    
    for dir_path in STRUCTURE.keys():
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {dir_path}")
    
    print(f"\n✅ {len(STRUCTURE)} diretórios criados!\n")


def create_init_files():
    """Cria arquivos __init__.py vazios"""
    print("📄 Criando arquivos __init__.py...")
    
    for file_path in INIT_FILES:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Auto-generated __init__.py\n")
        print(f"   ✓ {file_path}")
    
    print(f"\n✅ {len(INIT_FILES)} arquivos __init__.py criados!\n")


def create_placeholder_files():
    """Cria arquivos placeholder com conteúdo básico"""
    print("📝 Criando arquivos placeholder...")
    
    for file_path, content in PLACEHOLDER_FILES.items():
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(f"   ✓ {file_path}")
    
    print(f"\n✅ {len(PLACEHOLDER_FILES)} arquivos placeholder criados!\n")


def create_readme():
    """Cria um README.md de instruções"""
    readme_content = """# Scaffolder-DDD - Setup

## ✅ Estrutura criada com sucesso!

Agora você precisa:

### 1. Adicionar o foundry.py na raiz

Copie o script principal `foundry.py` para a raiz deste diretório.

### 2. Preencher os templates

Os diretórios foram criados com arquivos __init__.py básicos.
Agora você precisa preencher com os templates corretos:

#### Templates essenciais para criar:

**Hybrid Architecture:**
- `templates/hybrid/Conventions.md.tmpl`
- `templates/hybrid/docker-compose.yml.tmpl`
- `templates/hybrid/Dockerfile.tmpl`
- `templates/hybrid/src/app/main.py.tmpl`
- `templates/hybrid/src/app/bootstrap.py.tmpl`
- `templates/hybrid/src/app/core/config.py.tmpl`
- `templates/hybrid/src/app/core/db.py.tmpl`
- `templates/hybrid/src/app/core/errors.py.tmpl`
- `templates/hybrid/src/app/domain/${context}/entities.py.tmpl`
- `templates/hybrid/src/app/domain/${context}/repositories.py.tmpl`
- `templates/hybrid/src/app/domain/ports/uow.py.tmpl`
- `templates/hybrid/src/app/application/${context}/use_cases.py.tmpl`
- `templates/hybrid/src/app/adapters/${context}/models.py.tmpl`
- `templates/hybrid/src/app/adapters/${context}/mappers.py.tmpl`
- `templates/hybrid/src/app/adapters/${context}/repository_impl.py.tmpl`
- `templates/hybrid/src/app/adapters/uow/sqlalchemy.py.tmpl`
- `templates/hybrid/src/app/api/router.py.tmpl`
- `templates/hybrid/src/app/api/routers/health.py.tmpl`
- `templates/hybrid/src/app/api/routers/${context}.py.tmpl`
- `templates/hybrid/src/app/api/schemas/${context}.py.tmpl`
- `templates/hybrid/src/app/api/deps/uow.py.tmpl`

**Common (Docs):**
- `templates/common/docs/DEVELOPER_GUIDE.md.tmpl`
- `templates/common/docs/TESTING_GUIDE.md.tmpl`
- `templates/common/docs/LINTING_GUIDE.md.tmpl`

**Common (Scripts):**
- `templates/common/scripts/dev.sh.tmpl`
- `templates/common/scripts/test.sh.tmpl`
- `templates/common/scripts/lint.sh.tmpl`
- `templates/common/scripts/migrate.sh.tmpl`

### 3. Testar o scaffolder

```bash
python foundry.py test-project --context customer --venv
cd test-project
./scripts/dev.sh
```

## 📁 Estrutura criada:

```
.
├── templates/
│   ├── common/          # Templates compartilhados
│   ├── hybrid/          # Arquitetura Híbrida
│   ├── ddd/             # DDD Puro
│   ├── hexagonal/       # Hexagonal Puro
│   ├── mvc/             # MVC
│   └── orm/             # Templates de ORM
│       ├── sqlalchemy/
│       └── peewee/
```

## 🎯 Próximos passos

1. Adicionar foundry.py
2. Preencher templates essenciais
3. Testar geração de projeto
4. Iterar e melhorar

Boa sorte! 🚀
"""
    
    Path("README_SETUP.md").write_text(readme_content)
    print("📖 README_SETUP.md criado com instruções!")


def print_summary():
    """Imprime resumo do que foi criado"""
    print("\n" + "="*70)
    print("✨ SETUP COMPLETO!")
    print("="*70)
    print("\n📁 Estrutura criada:")
    print(f"   • {len(STRUCTURE)} diretórios")
    print(f"   • {len(INIT_FILES)} arquivos __init__.py")
    print(f"   • {len(PLACEHOLDER_FILES)} arquivos placeholder")
    print(f"   • README_SETUP.md com instruções")
    
    print("\n📋 Próximos passos:")
    print("   1. Leia README_SETUP.md")
    print("   2. Adicione foundry.py na raiz")
    print("   3. Preencha os templates essenciais")
    print("   4. Teste: python foundry.py test --context product\n")
    
    print("💡 Dica: Use seu código existente como base para os templates!")
    print("="*70 + "\n")


def main():
    """Função principal"""
    print("\n🚀 Configurando Scaffolder-DDD...\n")
    
    try:
        create_structure()
        create_init_files()
        create_placeholder_files()
        create_readme()
        print_summary()
        
        print("✅ Setup concluído com sucesso!\n")
        return 0
        
    except Exception as e:
        print(f"\n❌ Erro durante setup: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
