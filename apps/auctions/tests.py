from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import MEIProfile
from apps.auctions.models import Bid, MEICategorySubscription
from apps.services.models import ServiceCategory, ServiceRequest

User = get_user_model()


def make_user(email, user_type, password='senha123'):
    return User.objects.create_user(
        email=email,
        full_name='Teste',
        user_type=user_type,
        password=password,
    )


class BidFormValidationTest(TestCase):
    """
    Testa todas as regras de negócio do BidForm.clean() (espelham as antigas
    validações de BidSerializer.validate, agora servidas via view Django).
    """

    def setUp(self):
        self.client = Client()

        # Cidadão (perfil criado automaticamente pelo signal)
        self.citizen = make_user('citizen@bid.test', 'CIDADAO')
        self.citizen_profile = self.citizen.citizen_profile

        # MEI — signal de accounts não cria MEIProfile, então criamos aqui.
        self.mei_user = make_user('mei@bid.test', 'MEI')
        self.mei_profile = MEIProfile.objects.create(
            user=self.mei_user,
            cnpj='12.345.678/0001-90',
            razao_social='MEI Teste',
            nome_fantasia='MEI Teste',
        )

        self.category = ServiceCategory.objects.create(
            name='Encanamento', slug='encanamento', is_active=True,
        )

        self.service_request = ServiceRequest.objects.create(
            citizen=self.citizen_profile,
            title='Conserto de cano',
            description='Cano com vazamento.',
            category=self.category,
            urgency='ALTA',
            budget_max=Decimal('500.00'),
            desired_deadline=date.today() + timedelta(days=14),
        )

        self.bid_url = reverse(
            'auctions:bid_create',
            kwargs={'request_pk': self.service_request.pk},
        )

    def _login_mei(self):
        self.client.login(email='mei@bid.test', password='senha123')

    def _payload(self, **overrides):
        data = {
            'amount': '300.00',
            'estimated_hours': '4',
            'proposed_deadline': (date.today() + timedelta(days=10)).isoformat(),
            'notes': 'Disponível imediatamente.',
        }
        data.update(overrides)
        return data

    def _verify_mei(self):
        self.mei_profile.verification_status = MEIProfile.VerificationStatus.VERIFIED
        self.mei_profile.save()

    def _subscribe_mei(self):
        MEICategorySubscription.objects.create(
            mei_profile=self.mei_profile, category=self.category, is_active=True,
        )

    # ── Falhas esperadas ──────────────────────────────────────

    def test_mei_nao_verificado_nao_cria_lance(self):
        self._login_mei()
        self.client.post(self.bid_url, self._payload())
        self.assertEqual(Bid.objects.count(), 0)

    def test_mei_nao_verificado_form_inclui_erro_de_verificacao(self):
        self._login_mei()
        response = self.client.post(self.bid_url, self._payload())
        self.assertContains(response, 'verificad', status_code=200)

    def test_mei_sem_inscricao_nao_cria_lance(self):
        self._verify_mei()
        self._login_mei()
        self.client.post(self.bid_url, self._payload())
        self.assertEqual(Bid.objects.count(), 0)

    def test_mei_sem_inscricao_form_inclui_erro_de_inscricao(self):
        self._verify_mei()
        self._login_mei()
        response = self.client.post(self.bid_url, self._payload())
        self.assertContains(response, 'inscrit', status_code=200)

    def test_segundo_lance_ativo_no_mesmo_request_nao_cria(self):
        self._verify_mei()
        self._subscribe_mei()
        self._login_mei()
        self.client.post(self.bid_url, self._payload())
        self.client.post(self.bid_url, self._payload())
        self.assertEqual(Bid.objects.count(), 1)

    def test_lance_acima_do_budget_max_nao_cria(self):
        self._verify_mei()
        self._subscribe_mei()
        self._login_mei()
        self.client.post(self.bid_url, self._payload(amount='999.99'))
        self.assertEqual(Bid.objects.count(), 0)

    def test_request_fora_de_open_ou_in_auction_nao_cria_lance(self):
        self.service_request.status = ServiceRequest.Status.AWARDED
        self.service_request.save(update_fields=['status'])
        self._verify_mei()
        self._subscribe_mei()
        self._login_mei()
        self.client.post(self.bid_url, self._payload())
        self.assertEqual(Bid.objects.count(), 0)

    # ── Sucesso ───────────────────────────────────────────────

    def test_lance_valido_cria_bid_com_status_active(self):
        self._verify_mei()
        self._subscribe_mei()
        self._login_mei()
        response = self.client.post(self.bid_url, self._payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Bid.objects.count(), 1)
        self.assertEqual(Bid.objects.first().status, Bid.Status.ACTIVE)

    def test_lance_retirado_permite_novo_lance_no_mesmo_request(self):
        """WITHDRAWN não bloqueia: o segundo lance deve ser aceito."""
        self._verify_mei()
        self._subscribe_mei()
        self._login_mei()
        self.client.post(self.bid_url, self._payload())
        bid = Bid.objects.first()
        bid.status = Bid.Status.WITHDRAWN
        bid.save(update_fields=['status'])
        response = self.client.post(self.bid_url, self._payload())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Bid.objects.count(), 2)


class BidWithdrawTest(TestCase):

    def setUp(self):
        self.client = Client()
        make_user('cit@w.test', 'CIDADAO')
        self.mei_user = make_user('mei@w.test', 'MEI')
        self.mei_profile = MEIProfile.objects.create(
            user=self.mei_user,
            cnpj='99.999.999/0001-99',
            razao_social='MEI W',
            nome_fantasia='MEI W',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
        )
        category = ServiceCategory.objects.create(name='C', slug='c')
        request = ServiceRequest.objects.create(
            citizen=User.objects.get(email='cit@w.test').citizen_profile,
            title='X', description='Y', category=category,
        )
        self.bid = Bid.objects.create(
            service_request=request,
            mei_profile=self.mei_profile,
            amount=Decimal('100'),
            estimated_hours=Decimal('1'),
            proposed_deadline=date.today() + timedelta(days=2),
        )
        self.client.login(email='mei@w.test', password='senha123')

    def test_withdraw_marca_lance_como_withdrawn(self):
        url = reverse('auctions:bid_withdraw', kwargs={'pk': self.bid.pk})
        self.client.post(url)
        self.bid.refresh_from_db()
        self.assertEqual(self.bid.status, Bid.Status.WITHDRAWN)
