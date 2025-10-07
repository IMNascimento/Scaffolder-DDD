# Scaffolder FastAPI + DDD/Hexagonal — Foundry v3.4

<img src="./architecture.png" alt="Arquitetura" width="640"/>

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/foundry-v3.4-blue)

## 🚀 O que é

**Foundry** é um gerador de projetos FastAPI com suporte a **DDD / Hexagonal / MVC / Hybrid**.  
Ele cria um projeto com **layout `src/`** (pacote real Python), múltiplos *bounded contexts*, ORM/DB, Docker, testes e tooling (Ruff, MyPy, Pytest, pre-commit).

> Desde a v3.4:
> - pacote = **nome do projeto normalizado** (ou `--module`)
> - toda a arquitetura cai em **`src/<package>/...`**
> - arquivos de topo (**README, LICENSE, pyproject.toml, .env, .gitignore, docker-compose.yml, Dockerfile, tests/, scripts/**) ficam **na raiz**
> - templates `.tmpl` com imports `from app.` são reescritos para `from <package>.`
> - se o destino não tiver extensão e o conteúdo parecer Python, força **`.py`**
> - cria `__init__.py` automaticamente nos diretórios de pacote

---

## 📦 Pré-requisitos

- **Python 3.12+**
- **Git**
- (Opcional) **Docker** e **Docker Compose**

---

## ⚙️ Instalação (do scaffolder)

```bash
git clone https://github.com/IMNascimento/scaffolder-DDD.git
cd scaffolder-DDD
# (opcional) crie um venv para o scaffolder em si
python -m venv .venv && source .venv/bin/activate
pip install -U pip
# nenhuma dependência extra é necessária para rodar o foundry
```

---

## 🧪 Dry run (opcional)

Quer só ver os comandos e logs? Rode o `foundry.py` com um nome de teste (ele cria a pasta).  
Apague depois se não quiser manter.

```bash
python foundry.py demo-service --context payment
rm -rf demo-service  # para limpar
```

---

## ▶️ Como gerar um novo projeto

### Exemplo simples
```bash
python foundry.py sua_aplicação --context payment
```

### Com múltiplos contexts
```bash
python foundry.py teste-api --contexts payment,sales,billing
```

### Escolhendo arquitetura/ORM/DB
```bash
python foundry.py loja-api \
  --arch hybrid \            # ddd | hexagonal | mvc | hybrid
  --orm sqlalchemy \         # sqlalchemy | peewee
  --db postgresql \          # postgresql | mysql
  --contexts customer,order
```

### Criando venv e instalando deps automaticamente
```bash
python foundry.py payments-svc --context payment --venv
```

### Sem Docker
```bash
python foundry.py minimal-api --context customer --no-docker
```

### Definindo o nome do pacote (opcional)
```bash
python foundry.py minha-api --context customer --module acme_api
# Resultado: src/acme_api/...
```

---

## 📁 Estrutura gerada

```
<project-name>/
├─ src/
│  └─ <package>/
│     ├─ api/
│     ├─ application/
│     ├─ core/
│     ├─ domain/
│     ├─ infrastructure/         # conforme arquitetura
│     └─ __init__.py
├─ scripts/                       # dev.sh, migrate.sh, lint.sh, etc.
├─ tests/
├─ .env.example
├─ Dockerfile
├─ docker-compose.yml
├─ pyproject.toml
└─ README.md                      # do projeto gerado
```

- `<package>` = `normalize(name)` ou `--module` (minúsculas, não começa com dígito).
- **Tudo de arquitetura** vai para `src/<package>/...`.
- **Arquivos de topo** ficam na raiz (ver lista no código).

---

## 🧭 Convenções de template

Nos seus `.tmpl`, use placeholders:

- `${module_name}` → nome do pacote final (ex.: `paguecerto`)
- `${context}` / `${ContextCap}` → nome do contexto atual
- `${project_name}`, `${api_prefix}`, `${db}`, `${db_url}`, `${year}`, `${date}`

Exemplo de import **correto** dentro do `.tmpl`:
```python
from ${module_name}.core.errors import NotFoundError
from ${module_name}.domain.${context}.entities import Payment
```

> O foundry ainda aplica um *fallback* para `from app.` → `from ${module_name}.`, mas prefira os placeholders.

---

## 🏃 Após gerar o projeto

Dentro da pasta do novo projeto:

```bash
# 1) venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# 2) deps + editable install (recomendado)
pip install -U pip
pip install -r requirements.txt
pip install -e .

# 3) env
cp .env.example .env

# 4) (opcional) docker
docker compose up -d --build

# 5) migrações (se SQLAlchemy + Alembic)
./scripts/migrate.sh
# ou: alembic upgrade head

# 6) dev server
uvicorn <package>.api.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger: `http://localhost:8000/api/docs` (ou `${api_prefix}/docs`)
- Redoc: `http://localhost:8000/api/redoc`

---

## 🧪 Testes e qualidade

```bash
pytest -v --cov=<package> --cov-report=term-missing
ruff check . --fix && ruff format .
mypy src/<package> tests
pre-commit install && pre-commit run -a
```

---

## 🔧 Opções da CLI

```
usage: foundry.py name [--module MODULE] [--api-prefix /api] 
                      [--context C | --contexts C1,C2] 
                      [--arch ddd|hexagonal|mvc|hybrid] 
                      [--orm sqlalchemy|peewee] 
                      [--db postgresql|mysql] 
                      [--venv] [--no-docker]
```

- `name` — nome do diretório do projeto (e base para o pacote)
- `--module` — nome do pacote (opcional)
- `--context` / `--contexts` — um ou vários bounded contexts
- `--arch` — arquitetura
- `--orm` — ORM
- `--db` — banco de dados
- `--venv` — cria `.venv` e instala dependências
- `--no-docker` — não gera Dockerfile/docker-compose.yml

---

## 🩹 Troubleshooting

- **ImportError do pacote**: esqueceu do `pip install -e .`?  
  Alternativa provisória: `export PYTHONPATH=./src` (não recomendado a longo prazo).
- **Arquivos `.py` faltando extensão**: v3.4 tenta corrigir automaticamente se o conteúdo parecer Python. Prefira nomear `.py.tmpl` nos templates.
- **`from app.` nos templates**: será reescrito, mas **padronize** para `${module_name}`.
- **Alembic não acha modelos**: confirme que o `env.py` gerado contém os imports por contexto e `target_metadata = Base.metadata`.

---

## 🤝 Contribuindo

1. Faça um fork e crie uma branch: `feat/minha-melhoria`
2. Rode `pre-commit install` e `pre-commit run -a`
3. Abra um PR com a descrição do que mudou

---

## 📜 Licença

MIT — veja [LICENSE](LICENSE).

---

## 👤 Autor

- **Igor Nascimento** – Desenvolvedor Principal – [@IMNascimento](https://github.com/IMNascimento)


## 🙏 Agradecimentos

- [FastAPI](https://fastapi.tiangolo.com/)  
- [SQLAlchemy](https://www.sqlalchemy.org/)  
- [Alembic](https://alembic.sqlalchemy.org/)  
- Comunidade DDD & Python por inspiração
- SophiaLabs (https://www.sophialabs.com.br) pelo apoio ao projeto e sempre apoiar iniciativas open source!
