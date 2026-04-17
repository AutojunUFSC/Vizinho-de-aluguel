from datetime import date, timedelta

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.auctions.models import Bid, MEICategorySubscription
from apps.services.models import ServiceCategory, ServiceRequest

BIDS_URL = '/api/v1/bids/'


def make_user(email, user_type, password='senha123'):
    return User.objects.create_user(
        email=email,
        full_name='Teste',
        user_type=user_type,
        password=password,
    )


class BidSerializerValidationTest(TestCase):
    """Testa todas as regras de negócio do BidSerializer.validate()."""

    def setUp(self):
        # Cidadão e seu perfil (criado via signal)
        self.citizen = make_user('citizen@bid.test', 'CIDADAO')
        self.citizen_profile = self.citizen.citizen_profile

        # MEI — signal cria MEIProfile com cnpj="".
        # Definimos cnpj logo após para evitar conflito de unique em outros testes.
        self.mei_user = make_user('mei@bid.test', 'MEI')
        self.mei_profile = self.mei_user.mei_profile
        self.mei_profile.cnpj = '12.345.678/0001-00'
        self.mei_profile.save()

        self.category = ServiceCategory.objects.create(
            name='Encanamento', slug='encanamento', is_active=True,
        )

        self.service_request = ServiceRequest.objects.create(
            citizen=self.citizen_profile,
            title='Conserto de cano',
            description='Cano com vazamento.',
            category=self.category,
            urgency='ALTA',
            budget_max='500.00',
            desired_deadline=date.today() + timedelta(days=14),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.mei_user)

    def _payload(self, **overrides):
        data = {
            'service_request': str(self.service_request.id),
            'amount': '300.00',
            'estimated_hours': 4,
            'proposed_deadline': (date.today() + timedelta(days=10)).isoformat(),
            'notes': 'Disponível imediatamente.',
        }
        data.update(overrides)
        return data

    def _verify_mei(self):
        self.mei_profile.verification_status = 'VERIFIED'
        self.mei_profile.save()

    def _subscribe_mei(self):
        MEICategorySubscription.objects.create(
            mei_profile=self.mei_profile,
            category=self.category,
            is_active=True,
        )

    # ── Falhas esperadas ──────────────────────────────────────

    def test_mei_nao_verificado_recebe_400(self):
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mei_nao_verificado_mensagem_contem_verificado(self):
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertIn('verificado', str(r.data).lower())

    def test_mei_sem_inscricao_na_categoria_recebe_400(self):
        self._verify_mei()
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mei_sem_inscricao_mensagem_contem_inscrito(self):
        self._verify_mei()
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertIn('inscrito', str(r.data).lower())

    def test_segundo_lance_ativo_no_mesmo_request_recebe_400(self):
        self._verify_mei()
        self._subscribe_mei()
        self.client.post(BIDS_URL, self._payload(), format='json')  # primeiro lance OK
        r = self.client.post(BIDS_URL, self._payload(), format='json')  # segundo deve falhar
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_segundo_lance_mensagem_contem_ativo(self):
        self._verify_mei()
        self._subscribe_mei()
        self.client.post(BIDS_URL, self._payload(), format='json')
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertIn('ativo', str(r.data).lower())

    def test_lance_acima_do_budget_max_recebe_400(self):
        self._verify_mei()
        self._subscribe_mei()
        r = self.client.post(BIDS_URL, self._payload(amount='999.99'), format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_request_fora_de_open_ou_in_auction_recebe_400(self):
        self.service_request.status = 'AWARDED'
        self.service_request.save()
        self._verify_mei()
        self._subscribe_mei()
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Sucesso ───────────────────────────────────────────────

    def test_lance_valido_cria_bid_com_status_active(self):
        self._verify_mei()
        self._subscribe_mei()
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bid.objects.count(), 1)
        self.assertEqual(Bid.objects.first().status, 'ACTIVE')

    def test_lance_retirado_permite_novo_lance_no_mesmo_request(self):
        """WITHDRAWN não é ACTIVE; um novo lance deve ser aceito."""
        self._verify_mei()
        self._subscribe_mei()
        self.client.post(BIDS_URL, self._payload(), format='json')
        bid = Bid.objects.first()
        bid.status = 'WITHDRAWN'
        bid.save()
        r = self.client.post(BIDS_URL, self._payload(), format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
