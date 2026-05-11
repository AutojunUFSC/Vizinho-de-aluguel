from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import CitizenProfile, MEIProfile
from apps.auctions.models import Bid
from apps.orders.models import ServiceOrder
from apps.services.models import ServiceCategory, ServiceRequest

from .models import Review

User = get_user_model()


class RatingAvgSignalTests(TestCase):
    """
    Garante que ao criar uma Review o sinal post_save recalcula o rating_avg
    do MEIProfile (CITIZEN_TO_MEI) e do CitizenProfile (MEI_TO_CITIZEN).
    """

    def setUp(self):
        # Signal create_user_profile cria CitizenProfile automaticamente
        # quando user_type=CIDADAO. Para MEI, é criado manualmente abaixo.
        self.citizen_user = User.objects.create_user(
            email='cidadao@teste.com',
            password='senha-forte-123',
            full_name='Cidadão Teste',
            user_type=User.UserType.CIDADAO,
        )
        self.citizen = CitizenProfile.objects.get(user=self.citizen_user)

        self.mei_user = User.objects.create_user(
            email='mei@teste.com',
            password='senha-forte-123',
            full_name='MEI Teste',
            user_type=User.UserType.MEI,
        )
        self.mei = MEIProfile.objects.create(
            user=self.mei_user,
            cnpj='12.345.678/0001-90',
            razao_social='MEI Teste LTDA',
            nome_fantasia='MEI Teste',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
        )

        self.category = ServiceCategory.objects.create(
            name='Encanamento',
            slug='encanamento',
        )

    def _make_order(self):
        request = ServiceRequest.objects.create(
            citizen=self.citizen,
            title='Vazamento na pia',
            description='Pia da cozinha vazando.',
            category=self.category,
        )
        bid = Bid.objects.create(
            service_request=request,
            mei_profile=self.mei,
            amount=Decimal('150.00'),
            estimated_hours=Decimal('2.00'),
            proposed_deadline=date.today() + timedelta(days=3),
        )
        return ServiceOrder.objects.create(
            service_request=request,
            winning_bid=bid,
            citizen=self.citizen,
            mei_profile=self.mei,
            agreed_amount=Decimal('150.00'),
            agreed_deadline=date.today() + timedelta(days=3),
            status=ServiceOrder.Status.COMPLETED,
        )

    def test_citizen_to_mei_review_updates_mei_rating_avg(self):
        order_a = self._make_order()
        order_b = self._make_order()

        Review.objects.create(
            service_order=order_a,
            reviewer=self.citizen_user,
            review_type=Review.ReviewType.CITIZEN_TO_MEI,
            rating=4,
        )
        self.mei.refresh_from_db()
        self.assertEqual(self.mei.rating_avg, Decimal('4.00'))

        Review.objects.create(
            service_order=order_b,
            reviewer=self.citizen_user,
            review_type=Review.ReviewType.CITIZEN_TO_MEI,
            rating=2,
        )
        self.mei.refresh_from_db()
        self.assertEqual(self.mei.rating_avg, Decimal('3.00'))

    def test_mei_to_citizen_review_updates_citizen_rating_avg(self):
        order = self._make_order()

        Review.objects.create(
            service_order=order,
            reviewer=self.mei_user,
            review_type=Review.ReviewType.MEI_TO_CITIZEN,
            rating=5,
        )
        self.citizen.refresh_from_db()
        self.assertEqual(self.citizen.rating_avg, Decimal('5.00'))

    def test_signal_is_registered(self):
        """A configuração de apps.py deve ter conectado o signal."""
        from django.db.models.signals import post_save

        self.assertTrue(
            post_save.has_listeners(sender=Review),
            'Nenhum listener de post_save conectado a Review — '
            'verifique apps/reviews/apps.py:ready().',
        )
