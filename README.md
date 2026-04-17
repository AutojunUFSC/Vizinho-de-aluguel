# Vizinho de Aluguel — Backend

Plataforma de marketplace de serviços locais que conecta cidadãos a prestadores MEI por meio de um sistema de **leilão reverso**: o cidadão abre uma solicitação, MEIs enviam lances e o cidadão escolhe o vencedor.

Projeto desenvolvido pela equipe **AutoJun/UFSC**.

---

## Visão Geral

O fluxo principal da plataforma é:

1. **Cidadão** cria uma solicitação de serviço com orçamento máximo e prazo.
2. **MEIs** inscritos na categoria recebem a solicitação no feed e enviam lances.
3. O cidadão **adjudica** um lance (`award`), criando automaticamente uma ordem de serviço.
4. O MEI **inicia** e **conclui** o serviço; o cidadão **confirma** a entrega.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Framework web | Django 6.0.2 |
| API REST | Django REST Framework 3.16 |
| Autenticação | JWT via `djangorestframework-simplejwt` |
| Banco de dados (dev) | SQLite (padrão) |
| Banco de dados (prod) | PostgreSQL (`psycopg2-binary`) |
| Upload de arquivos | Pillow (imagens) |
| Variáveis de ambiente | `python-decouple` |

---

## Pré-requisitos

- Python 3.12+
- pip
- (Opcional, produção) PostgreSQL 14+

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/AutojunUFSC/Vizinho-de-alugel
cd vizinho_de_aluguel

# 2. Crie e ative um ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

---

## Configuração do .env

Crie um arquivo `.env` na raiz do projeto. Em desenvolvimento as configurações de banco podem ser omitidas (SQLite será usado por padrão).

```env
# Chave secreta do Django (obrigatória em produção)
SECRET_KEY=sua-chave-secreta-aqui

# Banco de dados — omitir para usar SQLite em desenvolvimento
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=vizinho_db
DATABASE_USER=postgres
DATABASE_PASSWORD=secret
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

> **Atenção:** nunca commite o arquivo `.env`. Adicione-o ao `.gitignore`.

---

## Como Rodar

```bash
# 1. Aplique as migrações
python manage.py migrate

# 2. (Opcional) Popule as categorias de serviço iniciais
python manage.py seed_categories

# 3. (Opcional) Crie um superusuário para o painel admin
python manage.py createsuperuser

# 4. Suba o servidor de desenvolvimento
python manage.py runserver
```

A API estará disponível em `http://localhost:8000/api/v1/`.
O painel admin Django estará em `http://localhost:8000/admin/`.

---

## Como Testar

```bash
# Roda toda a suíte de testes unitários
python manage.py test

# Com saída detalhada (nome de cada teste)
python manage.py test --verbosity=2

# Roda testes de um app específico
python manage.py test apps.accounts
python manage.py test apps.auctions
python manage.py test apps.orders
```

A suíte atual conta com **42 testes** distribuídos entre os apps `accounts`, `auctions` e `orders`.

Para o teste de ponta a ponta (requer servidor rodando e `pip install requests`):

```bash
# Janela 1 — servidor
python manage.py runserver

# Janela 2 — teste E2E
python e2e_test.py
```

---

## Estrutura de Apps

```
vizinho_de_aluguel/
├── core/               # Configurações globais (settings.py, urls.py, wsgi.py)
├── apps/
│   ├── accounts/       # Usuários, perfis (Cidadão e MEI) e endereços
│   ├── services/       # Categorias e solicitações de serviço
│   ├── auctions/       # Inscrições de MEI em categorias e lances (bids)
│   ├── orders/         # Ordens de serviço e ciclo de vida do trabalho
│   ├── reviews/        # Avaliações (stub — não implementado)
│   └── admin_panel/    # Painel administrativo customizado (stub)
├── ui/                 # Front-end Django (templates)
├── templates/
├── e2e_test.py         # Teste de ponta a ponta com requests
├── requirements.txt
└── manage.py
```

### Modelos principais

| App | Modelos |
|---|---|
| `accounts` | `User`, `CitizenProfile`, `MEIProfile`, `Address` |
| `services` | `ServiceCategory`, `ServiceRequest`, `ServiceRequestMedia` |
| `auctions` | `MEICategorySubscription`, `Bid` |
| `orders` | `ServiceOrder` |

---

## Rotas Principais

> Prefixo base: `/api/v1/`

### Autenticação e Perfis — `/api/v1/auth/`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| POST | `auth/register/` | Cadastra novo usuário, retorna JWT | Pública |
| POST | `auth/login/` | Login, retorna par de tokens JWT | Pública |
| POST | `auth/refresh/` | Renova o access token | Pública |
| GET/PATCH | `users/me/` | Dados do usuário autenticado | Sim |
| GET/PATCH | `citizen-profiles/me/` | Perfil do cidadão autenticado | Sim |
| GET/PATCH | `mei-profiles/me/` | Perfil do MEI autenticado | Sim |
| GET | `mei-profiles/` | Lista pública de MEIs (`?city=`, `?is_available=`) | Pública |
| GET | `mei-profiles/<uuid>/` | Perfil público de um MEI | Pública |
| GET/POST | `addresses/` | Endereços do usuário autenticado | Sim |

### Serviços — `/api/v1/`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `categories/` | Lista categorias ativas | Pública |
| GET | `categories/<slug>/` | Detalhe de uma categoria | Pública |
| GET/POST | `service-requests/` | Lista e cria solicitações | Sim |
| GET/PATCH/DELETE | `service-requests/<pk>/` | Detalhe de uma solicitação | Sim |
| GET | `service-requests/mine/` | Solicitações do cidadão (`?status=`) | Sim |
| GET | `service-requests/feed/` | Feed para MEIs (`?category=`, `?city=`, `?urgency=`) | Sim |
| POST | `service-requests/<pk>/cancel/` | Cancela uma solicitação | Sim |
| POST | `service-requests/<pk>/award/` | Adjudica lance vencedor, cria ordem | Sim |
| GET/POST | `service-requests/<uuid>/media/` | Mídias de uma solicitação | Sim |

### Leilões — `/api/v1/`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET/POST | `category-subscriptions/` | Inscrições do MEI em categorias | Sim |
| DELETE | `category-subscriptions/<pk>/` | Remove inscrição | Sim |
| GET/POST | `bids/` | Lista e cria lances | Sim |
| GET/PATCH/DELETE | `bids/<pk>/` | Detalhe de um lance | Sim |
| GET | `bids/mine/` | Lances do MEI autenticado | Sim |
| POST | `bids/<pk>/withdraw/` | Retira um lance ACTIVE | Sim |

### Ordens — `/api/v1/`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| GET | `service-orders/` | Lista todas as ordens | Sim |
| GET | `service-orders/<pk>/` | Detalhe de uma ordem | Sim |
| GET | `service-orders/mine/` | Ordens do usuário autenticado | Sim |
| POST | `service-orders/<pk>/start/` | Inicia o serviço (PENDING_START → IN_PROGRESS) | Sim |
| POST | `service-orders/<pk>/complete/` | Conclui o serviço (IN_PROGRESS → COMPLETED) | Sim |
| POST | `service-orders/<pk>/confirm/` | Cidadão confirma a entrega | Sim |
| POST | `service-orders/<pk>/cancel/` | Cancela a ordem | Sim |

---

## Equipe

- Artur Tomaz
- Bernardo Nunes
- Gabriel Madeira
- Gustavo Borget
- Pedro Petrelli
- Rafael Mussi
