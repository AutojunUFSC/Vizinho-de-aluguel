from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.auctions.models import Bid, MEICategorySubscription
from apps.orders.models import ServiceOrder
from apps.services.models import ServiceCategory, ServiceRequest


def make_user(email, user_type, password='senha123'):
    return User.objects.create_user(
        email=email,
        full_name='Teste',
        user_type=user_type,
        password=password,
    )


class BaseOrderTestCase(TestCase):
    """
    Fixture compartilhado: cidadão, dois MEIs verificados, categoria,
    service_request OPEN e dois lances ativos.
    """

    def setUp(self):
        # Cidadão
        self.citizen = make_user('citizen@orders.test', 'CIDADAO')
        self.citizen_profile = self.citizen.citizen_profile

        # MEI 1 — cnpj definido antes de criar MEI 2 para evitar conflito de unique=""
        self.mei1 = make_user('mei1@orders.test', 'MEI')
        self.mei_profile1 = self.mei1.mei_profile
        self.mei_profile1.cnpj = '11.111.111/0001-11'
        self.mei_profile1.verification_status = 'VERIFIED'
        self.mei_profile1.save()

        # MEI 2
        self.mei2 = make_user('mei2@orders.test', 'MEI')
        self.mei_profile2 = self.mei2.mei_profile
        self.mei_profile2.cnpj = '22.222.222/0002-22'
        self.mei_profile2.verification_status = 'VERIFIED'
        self.mei_profile2.save()

        self.category = ServiceCategory.objects.create(
            name='Elétrica', slug='eletrica', is_active=True,
        )

        self.service_request = ServiceRequest.objects.create(
            citizen=self.citizen_profile,
            title='Troca de disjuntor',
            description='Quadro elétrico com problema.',
            category=self.category,
            urgency='ALTA',
            budget_max='800.00',
            desired_deadline=date.today() + timedelta(days=10),
        )

        for mei_profile in (self.mei_profile1, self.mei_profile2):
            MEICategorySubscription.objects.create(
                mei_profile=mei_profile, category=self.category, is_active=True,
            )

        self.bid1 = Bid.objects.create(
            service_request=self.service_request,
            mei_profile=self.mei_profile1,
            amount='600.00',
            estimated_hours=3,
            proposed_deadline=date.today() + timedelta(days=7),
        )
        self.bid2 = Bid.objects.create(
            service_request=self.service_request,
            mei_profile=self.mei_profile2,
            amount='700.00',
            estimated_hours=4,
            proposed_deadline=date.today() + timedelta(days=8),
        )

        self.citizen_client = APIClient()
        self.citizen_client.force_authenticate(user=self.citizen)

        self.mei1_client = APIClient()
        self.mei1_client.force_authenticate(user=self.mei1)

        self.mei2_client = APIClient()
        self.mei2_client.force_authenticate(user=self.mei2)

    def _award_url(self, sr_id=None):
        sr_id = sr_id or self.service_request.id
        return f'/api/v1/service-requests/{sr_id}/award/'

    def _do_award(self, bid=None):
        bid = bid or self.bid1
        return self.citizen_client.post(
            self._award_url(), {'bid_id': str(bid.id)}, format='json'
        )

    def _get_order(self):
        return ServiceOrder.objects.select_related('winning_bid').first()


class AwardActionTest(BaseOrderTestCase):

    def test_award_retorna_201(self):
        r = self._do_award()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_award_cria_exatamente_uma_service_order(self):
        self._do_award()
        self.assertEqual(ServiceOrder.objects.count(), 1)

    def test_award_associa_winning_bid_correto(self):
        self._do_award()
        order = self._get_order()
        self.assertEqual(str(order.winning_bid.id), str(self.bid1.id))

    def test_award_copia_amount_e_deadline_do_bid(self):
        self._do_award()
        order = self._get_order()
        self.assertEqual(order.agreed_amount, Decimal(self.bid1.amount))
        self.assertEqual(order.agreed_deadline, self.bid1.proposed_deadline)

    def test_award_order_inicia_com_status_pending_start(self):
        self._do_award()
        order = self._get_order()
        self.assertEqual(order.status, 'PENDING_START')

    def test_award_muda_service_request_para_awarded(self):
        self._do_award()
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, 'AWARDED')

    def test_award_registra_awarded_at(self):
        self._do_award()
        self.service_request.refresh_from_db()
        self.assertIsNotNone(self.service_request.awarded_at)

    def test_award_marca_lance_vencedor_como_winner(self):
        self._do_award()
        self.bid1.refresh_from_db()
        self.assertEqual(self.bid1.status, 'WINNER')

    def test_award_rejeita_outros_lances_ativos(self):
        self._do_award()
        self.bid2.refresh_from_db()
        self.assertEqual(self.bid2.status, 'REJECTED')

    def test_award_com_bid_invalido_retorna_404(self):
        import uuid
        r = self.citizen_client.post(
            self._award_url(), {'bid_id': str(uuid.uuid4())}, format='json'
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_award_sem_bid_id_retorna_400(self):
        r = self.citizen_client.post(self._award_url(), {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_award_request_ja_awarded_retorna_400(self):
        self._do_award()
        r = self._do_award()
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


class ServiceOrderTransitionTest(BaseOrderTestCase):
    """Testa as transições de status da ServiceOrder."""

    def setUp(self):
        super().setUp()
        self._do_award()
        self.order = self._get_order()

    # ── start ────────────────────────────────────────────────

    def test_start_muda_status_para_in_progress(self):
        r = self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'IN_PROGRESS')

    def test_start_registra_started_at(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.started_at)

    def test_start_em_order_ja_in_progress_retorna_400(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        r = self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── complete ─────────────────────────────────────────────

    def test_complete_sem_estar_in_progress_retorna_400(self):
        # order está em PENDING_START
        r = self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/complete/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_em_pending_start_nao_muda_status(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/complete/')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'PENDING_START')

    def test_complete_muda_status_para_completed(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        r = self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/complete/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'COMPLETED')

    def test_complete_registra_completed_at(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/complete/')
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.completed_at)

    # ── confirm ──────────────────────────────────────────────

    def test_confirm_sem_estar_completed_retorna_400(self):
        # order em PENDING_START
        r = self.citizen_client.post(f'/api/v1/service-orders/{self.order.id}/confirm/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_em_in_progress_retorna_400(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        r = self.citizen_client.post(f'/api/v1/service-orders/{self.order.id}/confirm/')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_registra_citizen_confirmed_at(self):
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/start/')
        self.mei1_client.post(f'/api/v1/service-orders/{self.order.id}/complete/')
        r = self.citizen_client.post(f'/api/v1/service-orders/{self.order.id}/confirm/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.citizen_confirmed_at)
