from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MEICategorySubscriptionViewSet, BidViewSet

router = DefaultRouter()
router.register(r'category-subscriptions', MEICategorySubscriptionViewSet, basename='category-subscriptions')
router.register(r'bids', BidViewSet, basename='bids')

urlpatterns = router.urls
