# Vizinho de Aluguel — Backend

Plataforma de marketplace de serviços locais que conecta cidadãos a prestadores MEI via leilão reverso.

## Stack

- **Python** 3.12 + **Django** 6.0.2 + **Django REST Framework**
- **Autenticação**: `rest_framework.authtoken` (TokenAuthentication) nas configurações globais; endpoints de login/registro emitem **JWT** via `rest_framework_simplejwt`
- **Banco**: SQLite (dev, padrão via `python-decouple`) / PostgreSQL (produção, `psycopg2-binary`)
- **Modelo de usuário customizado**: `accounts.User` (UUID PK, `email` como `USERNAME_FIELD`)
- **Branch atual**: `sprint-7`

## Estrutura do projeto

```
vizinho_de_aluguel/
├── core/               # settings.py, urls.py, wsgi.py
├── apps/
│   ├── accounts/       # User, CitizenProfile, MEIProfile, Address
│   ├── services/       # ServiceCategory, ServiceRequest, ServiceRequestMedia
│   ├── auctions/       # MEICategorySubscription, Bid
│   ├── orders/         # ServiceOrder
│   ├── reviews/        # stub (sem models/serializers ainda)
│   └── admin_panel/    # stub (sem views/models ainda)
├── ui/                 # front-end Django (templates)
├── templates/
└── manage.py
```

## Models

### `accounts`

| Model | Campos relevantes |
|---|---|
| `User` | `id` (UUID), `email` (unique), `full_name`, `user_type` (CIDADAO / MEI / ADMIN), `phone`, `cpf`, `avatar`, `is_active`, `is_staff` |
| `CitizenProfile` | 1-para-1 com `User`, `default_address` (FK Address), `rating_avg`, `total_services_requested` |
| `MEIProfile` | 1-para-1 com `User`, `cnpj`, `razao_social`, `nome_fantasia`, `verification_status` (PENDING / VERIFIED / REJECTED), `bio`, `service_radius_km`, `city`, `rating_avg`, `is_available`, `cnpj_file`, `whatsapp_link` |
| `Address` | FK `User`, `label`, `cep`, `street`, `number`, `neighborhood`, `city`, `state`, `latitude`, `longitude`, `is_primary` |

### `services`

| Model | Campos relevantes |
|---|---|
| `ServiceCategory` | `id` (UUID), `name`, `slug` (unique), `icon`, `is_active`, `order` |
| `ServiceRequest` | `id` (UUID), FK `CitizenProfile`, FK `ServiceCategory`, FK `Address`, `title`, `description`, `urgency` (BAIXA / MEDIA / ALTA / EMERGENCIA), `status` (OPEN → IN_AUCTION → AWARDED → IN_PROGRESS → COMPLETED / CANCELLED), `budget_max`, `auction_end_at`, `desired_deadline` |
| `ServiceRequestMedia` | FK `ServiceRequest`, `file`, `media_type` (IMAGE / VIDEO), `order` — máx. 5 por solicitação |

### `auctions`

| Model | Campos relevantes |
|---|---|
| `MEICategorySubscription` | FK `MEIProfile`, FK `ServiceCategory`, `is_active`, `subscribed_at` — unique_together |
| `Bid` | `id` (UUID), FK `ServiceRequest`, FK `MEIProfile`, `amount`, `estimated_hours`, `proposed_deadline`, `notes`, `status` (ACTIVE / WITHDRAWN / WINNER / REJECTED) |

Regras de negócio em `BidSerializer.validate`: MEI precisa estar VERIFIED, inscrito na categoria e sem lance ACTIVE duplicado; `amount` não pode exceder `budget_max`.

### `orders`

| Model | Campos relevantes |
|---|---|
| `ServiceOrder` | `id` (UUID), FK `ServiceRequest`, FK `Bid` (winning_bid), FK `CitizenProfile`, FK `MEIProfile`, `agreed_amount`, `agreed_deadline`, `status` (PENDING_START → IN_PROGRESS → COMPLETED / CANCELLED), `started_at`, `completed_at`, `citizen_confirmed_at` |

`ServiceOrderSerializer` expõe todos os campos como `read_only` — alterações só via actions.

### `reviews` / `admin_panel`

Sem models ou serializers. Apenas stubs de views/urls para não travar o servidor.

---

## Rotas da API

> Prefixo base: `/api/v1/`
> Accounts é incluído em `/api/v1/auth/` no `core/urls.py`, mas seus paths internos já repetem o prefixo `auth/` — atenção ao double-prefix em register/login/refresh.

### `accounts` — prefixo `api/v1/auth/`

| Método | Rota | View | Auth |
|---|---|---|---|
| POST | `auth/register/` | `RegisterView` | AllowAny |
| POST | `auth/login/` | `TokenObtainPairView` (JWT) | AllowAny |
| POST | `auth/refresh/` | `TokenRefreshView` (JWT) | AllowAny |
| GET/PUT/PATCH | `users/me/` | `UserMeView` | IsAuthenticated |
| GET/PUT/PATCH | `citizen-profiles/me/` | `CitizenProfileMeView` | IsAuthenticated |
| GET/PUT/PATCH | `mei-profiles/me/` | `MEIProfileMeView` | IsAuthenticated |
| GET | `mei-profiles/` | `MEIProfileListView` | AllowAny — query: `city`, `is_available` |
| GET | `mei-profiles/<uuid:pk>/` | `MEIProfileDetailView` | AllowAny |
| GET/POST | `addresses/` | `AddressViewSet` | IsAuthenticated |

### `services` — prefixo `api/v1/`

| Método | Rota | View | Auth |
|---|---|---|---|
| GET | `categories/` | `ServiceCategoryListView` | AllowAny |
| GET | `categories/<slug>/` | `ServiceCategoryDetailView` | AllowAny |
| GET/POST | `service-requests/` | `ServiceRequestViewSet` | IsAuthenticated |
| GET/PUT/PATCH/DELETE | `service-requests/<pk>/` | `ServiceRequestViewSet` | IsAuthenticated |
| GET | `service-requests/mine/` | action `mine` — filtra por `status` | IsAuthenticated |
| GET | `service-requests/feed/` | action `feed` — pedidos OPEN/IN_AUCTION, query: `category`, `city`, `urgency` | IsAuthenticated |
| POST | `service-requests/<pk>/cancel/` | action `cancel` | IsAuthenticated |
| GET/POST | `service-requests/<uuid:request_pk>/media/` | `ServiceRequestMediaView` | IsAuthenticated |

### `auctions` — prefixo `api/v1/`

| Método | Rota | View | Auth |
|---|---|---|---|
| GET | `category-subscriptions/` | `MEICategorySubscriptionViewSet.list` | IsAuthenticated |
| POST | `category-subscriptions/` | `MEICategorySubscriptionViewSet.create` — body: `{ category_ids: [] }` | IsAuthenticated |
| DELETE | `category-subscriptions/<pk>/` | `MEICategorySubscriptionViewSet.destroy` | IsAuthenticated |
| GET/POST | `bids/` | `BidViewSet` | IsAuthenticated |
| GET/PUT/PATCH/DELETE | `bids/<pk>/` | `BidViewSet` | IsAuthenticated |
| GET | `bids/mine/` | action `mine` | IsAuthenticated |
| POST | `bids/<pk>/withdraw/` | action `withdraw` — só lances ACTIVE | IsAuthenticated |

### `orders` — prefixo `api/v1/`

| Método | Rota | View | Auth |
|---|---|---|---|
| GET/POST | `service-orders/` | `ServiceOrderViewSet` | IsAuthenticated |
| GET/PUT/PATCH/DELETE | `service-orders/<pk>/` | `ServiceOrderViewSet` | IsAuthenticated |
| GET | `service-orders/mine/` | action `mine` — filtra por CIDADAO ou MEI | IsAuthenticated |
| POST | `service-orders/<pk>/start/` | action `start` — PENDING_START → IN_PROGRESS | IsAuthenticated |
| POST | `service-orders/<pk>/complete/` | action `complete` — IN_PROGRESS → COMPLETED | IsAuthenticated |
| POST | `service-orders/<pk>/confirm/` | action `confirm` — registra `citizen_confirmed_at` | IsAuthenticated |
| POST | `service-orders/<pk>/cancel/` | action `cancel` | IsAuthenticated |

### `reviews` — prefixo `api/v1/`

| Método | Rota | Obs |
|---|---|---|
| GET | `reviews/` | Stub — retorna `[]` |

### `admin_panel` — prefixo `api/v1/admin/`

Sem rotas registradas (placeholder).

---

## Comandos frequentes

```bash
# Servidor de desenvolvimento
python manage.py runserver

# Migrações
python manage.py makemigrations
python manage.py migrate

# Testes
python manage.py test

# Listar todas as URLs registradas (requer django-extensions)
python manage.py show_urls

# Popular categorias de serviço iniciais
python manage.py seed_categories
```

## Variáveis de ambiente (`.env`)

```env
# Banco (omitir = SQLite em dev)
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=vizinho_db
DATABASE_USER=postgres
DATABASE_PASSWORD=secret
DATABASE_HOST=localhost
DATABASE_PORT=5432

SECRET_KEY=sua-chave-secreta
```
