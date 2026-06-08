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
| Framework web | Django 6.0.2 (Templates SSR) |
| Formulários | Django Forms |
| Autenticação | Sessões padrão do Django |
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

A plataforma estará disponível em `http://localhost:8000/`.
O painel administrativo padrão do Django em `http://localhost:8000/admin/`.
O painel de controle gerencial (customizado) em `http://localhost:8000/painel/`.

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

A suíte atual conta com dezenas de testes (mais de 50 testes no total) distribuídos entre os apps `accounts`, `auctions`, `orders`, `reviews` e `services`, com cobertura de ponta a ponta dos fluxos de negócios e segurança.

---

## Estrutura de Apps

```text
vizinho_de_aluguel/
├── core/               # Configurações globais (settings.py, urls.py, wsgi.py)
├── apps/
│   ├── accounts/       # Autenticação, Perfis (Cidadão/MEI) e Endereços
│   ├── services/       # Categorias e Solicitações de Serviço
│   ├── auctions/       # Inscrições em Categorias e Feed de Lances (Bids)
│   ├── orders/         # Acompanhamento de Pedidos e Chat
│   ├── reviews/        # Reputação e Avaliações de Usuários
│   └── admin_panel/    # Painel Gerencial (Backoffice Administrativo)
├── templates/          # Templates SSR modulares (separados por app)
├── static/             # Estilos CSS, assets e bibliotecas front-end
├── media/              # Diretório local para imagens e uploads
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
| `reviews` | `Review` |

---

## Rotas Principais (Navegação UI)

> O sistema não possui uma API REST pública. A renderização é 100% Server-Side (SSR) usando Django Templates nativos.

### Autenticação e Perfis

| Rota | Descrição | Auth |
|---|---|---|
| `/cadastro/` | Cadastro unificado (Cidadão e MEI) | Pública |
| `/login/` | Autenticação unificada por email e senha | Pública |
| `/logout/` | Encerra a sessão atual com segurança | Sim |
| `/usuario/perfil/` | Perfil Unificado e Dashboard Híbrido (Cidadão e MEI) | Sim |
| `/usuario/enderecos/` | Gerenciamento de endereços para cidadãos | Sim |
| `/mei/` | Diretório público de profissionais cadastrados | Pública |
| `/mei/<pk>/` | Perfil público detalhado do profissional MEI | Pública |

### Serviços e Marketplace

| Rota | Descrição | Auth |
|---|---|---|
| `/servicos/` | Catálogo público das categorias ativas | Pública |
| `/solicitacoes/nova/` | Assistente para cidadão criar uma solicitação (Wizard) | Cidadão |
| `/solicitacoes/minhas/`| Listagem das solicitações abertas/em progresso do cidadão | Cidadão |
| `/solicitacoes/<pk>/` | Detalhes da solicitação e comparação de lances/orçamentos | Cidadão |
| `/solicitacoes/<pk>/adjudicar/<bid_pk>/` | Ação: cidadão aceita um lance e gera um Pedido | Cidadão |

### Leilões e Pedidos

| Rota | Descrição | Auth |
|---|---|---|
| `/feed/` | Feed Kanban de oportunidades disponíveis para MEIs na região | MEI |
| `/categorias/inscrever/`| Painel para o MEI gerenciar inscrições nas suas áreas de atuação | MEI |
| `/propostas/nova/<pk>/` | MEI avalia detalhes da solicitação e envia seu orçamento formal | MEI |
| `/propostas/minhas/` | Listagem das propostas enviadas pelo MEI com status atualizado | MEI |
| `/pedidos/` | Listagem completa de todos os serviços (Cidadãos e MEIs) | Sim |
| `/pedidos/<pk>/` | Tela de acompanhamento do pedido ativo com linha do tempo | Sim |
| `/avaliacoes/avaliar/<pk>/`| Ferramenta de feedback para avaliar pedidos já finalizados | Sim |

---

## Login Único Gov.BR (OAuth2 + OIDC + PKCE)

A plataforma suporta "Entrar com gov.br" (coexistindo com o login por e-mail/senha).
Detalhes técnicos em [`Integra_gov_br.md`](Integra_gov_br.md).

### Configuração

1. Instale as dependências: `pip install -r requirements.txt` (adiciona `requests` e `PyJWT[crypto]`).
2. Copie `.env.example` para `.env` e preencha as variáveis `GOVBR_*` com as credenciais
   fornecidas pela Prefeitura/Gov.BR (homologação primeiro). No Railway, cadastre as mesmas
   variáveis no painel **Variables**.
3. O `GOVBR_REDIRECT_URI` (`.../accounts/govbr/callback/`) e o `GOVBR_LOGOUT_REDIRECT_URI`
   precisam ser **idênticos** aos cadastrados na credencial Gov.BR.
4. Rode as migrações: `python manage.py migrate` (campos `govbr_verified` e `govbr_level`).

### Rotas

| Rota | Descrição | Auth |
|---|---|---|
| `/accounts/govbr/login/` | Inicia o fluxo OIDC (gera PKCE/state/nonce, redireciona ao gov.br) | Não |
| `/accounts/govbr/callback/` | Recebe o code, valida tokens e abre a sessão Django | Não |
| `/accounts/govbr/logout/` | Encerra a sessão e redireciona ao logout do gov.br (POST) | Sim |

> Usuário novo via gov.br é criado como **Cidadão** (sem senha utilizável; entra só pelo gov.br).
> O teste ponta-a-ponta exige as credenciais de homologação da Prefeitura.

---

## Equipe

- Artur Tomaz
- Bernardo Nunes
- Gabriel Madeira
- Gustavo Borget
- Pedro Petrelli
- Rafael Mussi
