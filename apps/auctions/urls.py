from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MEICategorySubscriptionViewSet, BidViewSet

router = DefaultRouter()
router.register('category-subscriptions', MEICategorySubscriptionViewSet, basename='category-subscription')
router.register('bids', BidViewSet, basename='bid')

urlpatterns = [
    path('', include(router.urls)),
]