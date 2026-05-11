from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import cadastro_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Página unificada de login + cadastro (Cidadão / MEI)
    path('cadastro/', cadastro_view, name='cadastro'),

    # Auth, perfil, endereços, diretório de MEIs (Django Templates)
    path('', include('apps.accounts.urls', namespace='accounts')),

    # Avaliações (Django Templates)
    path('avaliacoes/', include('apps.reviews.urls', namespace='reviews')),

    # Auctions (lances, inscrições) — Django Templates
    # ⚠ Deve vir ANTES de services para que 'categorias/inscricoes/' não seja
    #   capturada pelo catch-all 'categorias/<slug>/' de services.
    path('', include('apps.auctions.urls', namespace='auctions')),

    # Services (solicitações, categorias, mídias, adjudicação) — Django Templates
    path('', include('apps.services.urls', namespace='services')),

    # Orders (ordens de serviço, transições) — Django Templates
    path('', include('apps.orders.urls', namespace='orders')),

    # UI principal (home, dashboards, telas de fluxo)
    path('', include('apps.ui.urls')),

    # Painel administrativo
    path('painel/', include('apps.admin_panel.urls', namespace='admin_panel')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
