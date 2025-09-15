# Scaffolder Fastapi + DDD

<img src="./architecture.png" alt="Logo Spectro">

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

## 🚀 Introdução

**Scaffolder Fastapi + DDD** é uma ferramenta de scaffolding que gera automaticamente um projeto FastAPI estruturado em **DDD (Domain-Driven Design)** e **Arquitetura Hexagonal**.  
Ele cria toda a base do projeto (domain, application, infrastructure, API, testes, scripts, Docker, Alembic, etc.) a partir de templates prontos, permitindo subir rapidamente novos bounded contexts em repositórios separados.

## ✨ Funcionalidades

- Geração automática de estrutura **DDD/Hexagonal**
- Suporte a múltiplos **bounded contexts**
- Configuração pronta para **FastAPI + SQLAlchemy 2.x + Alembic**
- Criação opcional de **venv + instalação de libs mais recentes**
- Scripts utilitários para desenvolvimento (`dev.sh`, `migrate.sh`, `wait-for-db.sh`)
- Suporte a **Docker/Docker Compose**
- Inclui ferramentas de qualidade: **pytest, ruff, mypy, pre-commit**

## 📦 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python** 3.11+  
- **Git**  
- **Docker** e **Docker Compose** (opcional, para rodar via containers)  

## ⚙️ Instalação

Clone o repositório e rode o scaffolder:

```bash
git clone https://github.com/IMNascimento/scaffolder-DDD.git
cd scaffolder-DDD
```

Para criar um novo projeto:

```bash
python foundry.py meu-servico --context customer
```

Com ambiente virtual automático e dependências instaladas:

```bash
python foundry.py meu-servico --context customer --venv
```

## ▶️ Uso

Entre no diretório do serviço gerado e inicialize:

```bash
cd meu-servico
cp .env.example .env
./scripts/dev.sh
```

A API estará disponível em:  
👉 http://localhost:8000/docs

### Exemplos de geração

Criar projeto `orium-customer` com bounded context **customer**:
```bash
python foundry.py orium-customer --context customer
```

Criar projeto `orium-order` com bounded context **order**:
```bash
python foundry.py orium-order --context order
```

Gerar projeto já com virtualenv e dependências:
```bash
python foundry.py payments-service --context payment --venv
```

## 🤝 Contribuindo

Contribuições são bem-vindas!  
Abra uma **issue** ou envie um **pull request** seguindo as boas práticas do repositório.

## 📜 Licença

Distribuído sob a licença MIT.  
Consulte o arquivo [LICENSE](LICENSE) para mais informações.

## 👤 Autor

- **Igor Nascimento** – Desenvolvedor Principal – [GitHub](https://github.com/IMNascimento)

## 🙏 Agradecimentos

- [FastAPI](https://fastapi.tiangolo.com/)  
- [SQLAlchemy](https://www.sqlalchemy.org/)  
- [Alembic](https://alembic.sqlalchemy.org/)  
- Comunidade DDD & Python por inspiração
