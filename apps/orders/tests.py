from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import MEIProfile
from apps.auctions.models import Bid, MEICategorySubscription
from apps.orders.models import ServiceOrder
from apps.services.models import ServiceCategory, ServiceRequest

User = get_user_model()


def make_user(email, user_type, password='senha123'):
    return User.objects.create_user(
        email=email,
        full_name='Teste',
        user_type=user_type,
        password=password,
    )


class BaseOrderTestCase(TestCase):
    """
    Fixture: cidadão, dois MEIs verificados, categoria, ServiceRequest OPEN
    e dois lances ativos.
    """

    def setUp(self):
        # Cidadão (perfil via signal)
        self.citizen = make_user('citizen@orders.test', 'CIDADAO')
        self.citizen_profile = self.citizen.citizen_profile

        # MEI 1
        self.mei1 = make_user('mei1@orders.test', 'MEI')
        self.mei_profile1 = MEIProfile.objects.create(
            user=self.mei1,
            cnpj='11.111.111/0001-11',
            razao_social='MEI 1',
            nome_fantasia='MEI 1',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
        )

        # MEI 2
        self.mei2 = make_user('mei2@orders.test', 'MEI')
        self.mei_profile2 = MEIProfile.objects.create(
            user=self.mei2,
            cnpj='22.222.222/0002-22',
            razao_social='MEI 2',
            nome_fantasia='MEI 2',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
        )

        self.category = ServiceCategory.objects.create(
            name='Elétrica', slug='eletrica', is_active=True,
        )

        self.service_request = ServiceRequest.objects.create(
            citizen=self.citizen_profile,
            title='Troca de disjuntor',
            description='Quadro elétrico com problema.',
            category=self.category,
            urgency='ALTA',
            budget_max=Decimal('800.00'),
            desired_deadline=date.today() + timedelta(days=10),
        )

        for mei_profile in (self.mei_profile1, self.mei_profile2):
            MEICategorySubscription.objects.create(
                mei_profile=mei_profile, category=self.category, is_active=True,
            )

        self.bid1 = Bid.objects.create(
            service_request=self.service_request,
            mei_profile=self.mei_profile1,
            amount=Decimal('600.00'),
            estimated_hours=Decimal('3'),
            proposed_deadline=date.today() + timedelta(days=7),
        )
        self.bid2 = Bid.objects.create(
            service_request=self.service_request,
            mei_profile=self.mei_profile2,
            amount=Decimal('700.00'),
            estimated_hours=Decimal('4'),
            proposed_deadline=date.today() + timedelta(days=8),
        )

        self.citizen_client = Client()
        self.citizen_client.login(email='citizen@orders.test', password='senha123')

        self.mei1_client = Client()
        self.mei1_client.login(email='mei1@orders.test', password='senha123')

        self.mei2_client = Client()
        self.mei2_client.login(email='mei2@orders.test', password='senha123')

    def _award_url(self, bid=None):
        bid = bid or self.bid1
        return reverse('services:award_bid', kwargs={'bid_pk': bid.pk})

    def _do_award(self, bid=None):
        return self.citizen_client.post(self._award_url(bid))

    def _get_order(self):
        return ServiceOrder.objects.select_related('winning_bid').first()


class AwardActionTest(BaseOrderTestCase):

    def test_award_redireciona_apos_sucesso(self):
        r = self._do_award()
        self.assertEqual(r.status_code, 302)

    def test_award_cria_exatamente_uma_service_order(self):
        self._do_award()
        self.assertEqual(ServiceOrder.objects.count(), 1)

    def test_award_associa_winning_bid_correto(self):
        self._do_award()
        order = self._get_order()
        self.assertEqual(order.winning_bid_id, self.bid1.id)

    def test_award_copia_amount_e_deadline_do_bid(self):
        self._do_award()
        order = self._get_order()
        self.assertEqual(order.agreed_amount, self.bid1.amount)
        self.assertEqual(order.agreed_deadline, self.bid1.proposed_deadline)

    def test_award_order_inicia_com_status_pending_start(self):
        self._do_award()
        order = self._get_order()
        self.assertEqual(order.status, ServiceOrder.Status.PENDING_START)

    def test_award_muda_service_request_para_awarded(self):
        self._do_award()
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.AWARDED)

    def test_award_registra_awarded_at(self):
        self._do_award()
        self.service_request.refresh_from_db()
        self.assertIsNotNone(self.service_request.awarded_at)

    def test_award_marca_lance_vencedor_como_winner(self):
        self._do_award()
        self.bid1.refresh_from_db()
        self.assertEqual(self.bid1.status, Bid.Status.WINNER)

    def test_award_rejeita_outros_lances_ativos(self):
        self._do_award()
        self.bid2.refresh_from_db()
        self.assertEqual(self.bid2.status, Bid.Status.REJECTED)

    def test_award_com_bid_inexistente_retorna_404(self):
        import uuid
        url = reverse('services:award_bid', kwargs={'bid_pk': uuid.uuid4()})
        r = self.citizen_client.post(url)
        self.assertEqual(r.status_code, 404)

    def test_award_request_ja_awarded_nao_cria_segunda_order(self):
        self._do_award()
        # Recria um Bid ACTIVE para tentar aceitar de novo
        new_bid = Bid.objects.create(
            service_request=self.service_request,
            mei_profile=self.mei_profile2,
            amount=Decimal('500.00'),
            estimated_hours=Decimal('2'),
            proposed_deadline=date.today() + timedelta(days=5),
        )
        self.citizen_client.post(self._award_url(new_bid))
        self.assertEqual(ServiceOrder.objects.count(), 1)


class ServiceOrderTransitionTest(BaseOrderTestCase):
    """Testa as transições de status da ServiceOrder via FBVs Django."""

    def setUp(self):
        super().setUp()
        self._do_award()
        self.order = self._get_order()

    def _start_url(self):
        return reverse('orders:order_start', kwargs={'pk': self.order.pk})

    def _complete_url(self):
        return reverse('orders:order_complete', kwargs={'pk': self.order.pk})

    def _confirm_url(self):
        return reverse('orders:order_confirm', kwargs={'pk': self.order.pk})

    # ── start ────────────────────────────────────────────────

    def test_start_muda_status_para_in_progress(self):
        self.mei1_client.post(self._start_url())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ServiceOrder.Status.IN_PROGRESS)

    def test_start_registra_started_at(self):
        self.mei1_client.post(self._start_url())
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.started_at)

    def test_start_em_order_ja_in_progress_nao_muda_segundo_started_at(self):
        self.mei1_client.post(self._start_url())
        self.order.refresh_from_db()
        first_start = self.order.started_at
        self.mei1_client.post(self._start_url())
        self.order.refresh_from_db()
        self.assertEqual(self.order.started_at, first_start)

    def test_start_por_outro_mei_nao_muda_status(self):
        self.mei2_client.post(self._start_url())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ServiceOrder.Status.PENDING_START)

    # ── complete ─────────────────────────────────────────────

    def test_complete_em_pending_start_nao_muda_status(self):
        self.mei1_client.post(self._complete_url())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ServiceOrder.Status.PENDING_START)

    def test_complete_apos_start_muda_para_completed(self):
        self.mei1_client.post(self._start_url())
        self.mei1_client.post(self._complete_url())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, ServiceOrder.Status.COMPLETED)

    def test_complete_registra_completed_at(self):
        self.mei1_client.post(self._start_url())
        self.mei1_client.post(self._complete_url())
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.completed_at)

    # ── confirm ──────────────────────────────────────────────

    def test_confirm_sem_estar_completed_nao_marca_timestamp(self):
        self.citizen_client.post(self._confirm_url())
        self.order.refresh_from_db()
        self.assertIsNone(self.order.citizen_confirmed_at)

    def test_confirm_em_in_progress_nao_marca_timestamp(self):
        self.mei1_client.post(self._start_url())
        self.citizen_client.post(self._confirm_url())
        self.order.refresh_from_db()
        self.assertIsNone(self.order.citizen_confirmed_at)

    def test_confirm_apos_completed_registra_citizen_confirmed_at(self):
        self.mei1_client.post(self._start_url())
        self.mei1_client.post(self._complete_url())
        self.citizen_client.post(self._confirm_url())
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.citizen_confirmed_at)
