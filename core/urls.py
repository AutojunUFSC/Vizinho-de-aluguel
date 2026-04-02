from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ui.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.services.urls')),
    path('', include('apps.auctions.urls')),
    path('', include('apps.orders.urls')),
    path('', include('apps.reviews.urls')),
    path('painel/', include('apps.admin_panel.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
