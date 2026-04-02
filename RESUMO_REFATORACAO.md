# Resumo da Refatoração Backend - Alinhamento com Arquitetura Especificada

## Contexto

O projeto "Vizinho de Aluguel" foi construído inicialmente com Django REST Framework (DRF), seguindo um padrão de API REST com serializers e autenticação JWT. Porém, os documentos de arquitetura definidos para o projeto especificam uma aplicação Django Templates pura, com autenticação por sessão e renderização de HTML no servidor. Este resumo detalha as mudanças realizadas para alinhar o backend com a arquitetura definida.

## Mudanças Principais

### 1. Configuração do Django (core/settings.py)

A configuração foi completamente reescrita para suportar a arquitetura de Django Templates puro. Alterações incluem: migração de SQLite para PostgreSQL 16+, substituição de python-dotenv por python-decouple para gerenciar variáveis de ambiente de forma mais simples, adição de suporte a MEDIA_ROOT e MEDIA_URL para uploads de usuários, configuração de locale para português-Brasil (pt-br) e timezone Brasil, e registro de todos os 6 apps do projeto. Também foram adicionadas as configurações de redirecionamento de login (LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL) e definição do AUTH_USER_MODEL como 'accounts.User'.

### 2. Remoção do Django REST Framework

O Django REST Framework foi completamente removido do projeto. Isso inclui a exclusão de todos os serializers (DRF) dos apps accounts, services e auctions, e a remoção do permissions.py (que era exclusivo de DRF). O motivo é que DRF foi projetado para servir APIs REST a clientes externos (apps mobile, frontends SPA). No novo arquitetura, o backend renderiza HTML no servidor e o entrega direto ao browser — não há necessidade de serializar dados para JSON. Manter DRF adicionaria complexidade e dependências desnecessárias. A responsabilidade de validação e transformação de dados agora é das Django Forms nativas.

### 3. App Accounts - Refatoração Completa

O app accounts foi refatorado para remover completamente o padrão DRF. Foram criados decorators customizados (@citizen_required, @mei_required, @admin_required) que encapsulam a lógica de controle de acesso usando @login_required + verificação do user_type, substituindo completamente o sistema de permissões do DRF. Foram criadas Django Forms para todos os fluxos: LoginForm, CitizenRegisterForm, MEIRegisterForm, UserProfileForm, CitizenProfileForm, MEIProfileForm e AddressForm. Cada form contém a lógica de validação e salvamento específica do seu contexto. As views foram reescritas para renderizar templates HTML em vez de retornar JSON: CustomLoginView (com redirecionamento por user_type), CustomLogoutView, register_citizen e register_mei (com tratamento de profile creation via signals), dashboards para cidadão e MEI, perfis públicos e CRUD completo de endereços. As URLs foram reorganizadas para refletir a navegação do usuário no site (login, cadastro, dashboard, perfil, endereços).

### 4. App Services - Refatoração

O app services foi refatorado removendo os serializers DRF. Foi criado admin.py com ServiceCategoryAdmin (com auto-population de slug) e ServiceRequestAdmin (com inline de mídias). Foram criadas ServiceRequestForm e ServiceRequestMediaForm para validação e salvamento de dados do lado do servidor. As views foram reescritas para renderizar HTML: category_list exibe todas as categorias, service_request CRUD manipula criação, edição e exclusão de solicitações, award_bid adjudica uma solicitação a um lance vencedor (dentro de transaction.atomic para integridade), media_delete remove mídias, feed lista solicitações abertas com filtros, feed_detail exibe detalhes de uma solicitação. As URLs foram reorganizadas para routes de navegação (categorias, solicitações, feed). Foram criados arquivos faltantes: __init__.py do app, migrations/__init__.py e tests.py.

### 5. App Auctions - Refatoração

Removidos os serializers DRF. Foi criado BidForm para validação de lances com regras de negócio. As views foram reescritas: mei_categories gerencia a inscrição/desincrição em categorias de serviço (com lógica de checkbox), bid_create cria um lance com 6 validações (MEI verificado, inscrito na categoria, lance não duplicado, solicitação aberta, valor dentro do orçamento, prazo respeitável), my_bids lista lances do MEI, bid_update edita lances (apenas em status específicos), bid_withdraw retira lances. As URLs foram reorganizadas para navegação de perfil e feed.

### 6. App Orders - Refatoração (novo backend)

O app orders existia apenas com models. Foram criados forms (OrderCancelForm com campo motivo), views (order_detail exibe detalhes, order_start marca como em andamento, order_complete marca como concluído, order_confirm cidadão confirma conclusão, order_cancel cancela com motivo e lógica de reembolso) e urls (5 rotas para manipulação de ordens).

### 7. App Reviews - Novo App Criado

Foi criado um app reviews completo do zero com a seguinte estrutura: Model Review com campos para vincular a uma ServiceOrder, reviewer (User), review_type (CITIZEN_TO_MEI ou MEI_TO_CITIZEN), rating (1-5), comment e timestamps. Forms (ReviewForm para input de rating e comentário). Views (review_create com validação de permissão, confirmação de conclusão da ordem, e prevenção de avaliações duplicadas; my_reviews lista avaliações dadas e recebidas). Signals que recalculam rating_avg em MEIProfile e CitizenProfile a cada nova avaliação, mantendo os ratings atualizados. URLs para criar avaliação e listar minhas avaliações. Admin com ReviewAdmin registrado. O app carrega signals no ready() do AppConfig.

### 8. App Admin Panel - Novo App Criado

Foi criado um app admin_panel (painel administrativo customizado) com views para: dashboard exibindo estatísticas gerais (total de cidadãos, MEIs, verificações pendentes, solicitações abertas, ordens em andamento), mei_verification_list listando MEIs por status de verificação, mei_verification_detail permitindo aprovar/rejeitar MEIs, user_list com filtro por tipo de usuário, order_list com filtro por status. URLs sob prefixo painel/ (painel/, painel/verificacoes/, painel/usuarios/, painel/ordens/). Toda a lógica é protegida pelo decorator @admin_required.

### 9. Dependencies e Infrastructure

O arquivo requirements.txt foi reescrito corrigindo um problema de UTF-16 encoding que tornava o arquivo ilegível. Agora contém as dependências corretas: django==6.0.2, psycopg2-binary (para PostgreSQL), python-decouple (para config), pillow (para ImageField), e dependências de suporte. Foi criado arquivo .env com template de configuração para desenvolvimento local (credenciais PostgreSQL, SECRET_KEY, DEBUG flag, etc).

## Motivos da Refatoração

A refatoração foi necessária para alinhar o projeto com a arquitetura especificada nos documentos de base. O mismatch original entre implementação (API REST com DRF) e especificação (Django Templates puro) causava: (1) uso de tecnologia desnecessária (DRF sem um frontend externo para servir), (2) separação artificial entre dados e apresentação, (3) código duplicado de validação (serializers + forms), (4) maior complexidade do que o necessário para um site tradicional. A refatoração simplifica o stack, reduz dependências, e permite que o backend renderize diretamente o HTML que o usuário vê no browser, seguindo o padrão tradicional de desenvolvimento Django que alinha melhor com a proposta do projeto.

## Próximos Passos

1. Instalar Pillow (já está em requirements.txt): `pip install Pillow`
2. Configurar PostgreSQL local ou ajustar credenciais no .env
3. Rodar migrations: `python manage.py makemigrations && python manage.py migrate`
4. Criar superusuário para testar admin: `python manage.py createsuperuser`
5. Testar fluxos: cadastro cidadão, cadastro MEI, criar solicitação, fazer lance, adjudicar, criar ordem, concluir, avaliar
6. Verificar se app ui/ (frontend team) tem rotas básicas configuradas
7. Criar diretório static/ se ainda não existir (responsabilidade inicial do frontend)
