from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("ui.urls")), # Mantém o front-end aqui
    
    # Rotas de Autenticação e Perfis
    path('api/v1/auth/', include('apps.accounts.urls')),
   # path('api/v1/', include('apps.accounts.urls_profiles')),
    
    # Restante dos Apps
    path('api/v1/', include('apps.services.urls')),
    path('api/v1/', include('apps.auctions.urls')),
    path('api/v1/', include('apps.orders.urls')),
    path('api/v1/', include('apps.reviews.urls')),
    path('api/v1/admin/', include('apps.admin_panel.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)