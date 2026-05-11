from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Address, MEIProfile
from apps.auctions.models import Bid, MEICategorySubscription
from apps.orders.models import ServiceOrder

from .forms import ServiceRequestForm, ServiceRequestMediaForm
from .models import ServiceCategory, ServiceRequest, ServiceRequestMedia

User = get_user_model()


def make_user(email, user_type, password='senha123'):
    return User.objects.create_user(
        email=email,
        full_name='Teste',
        user_type=user_type,
        password=password,
    )


class ServiceRequestFormTest(TestCase):
    """Testes das validações do ServiceRequestForm."""

    def setUp(self):
        self.citizen = make_user('cit@form.test', 'CIDADAO')
        self.other_user = make_user('other@form.test', 'CIDADAO')
        self.category = ServiceCategory.objects.create(
            name='Pintura', slug='pintura', is_active=True,
        )
        self.address = Address.objects.create(
            user=self.citizen, label='Casa', cep='88000-000',
            street='Rua A', number='1', neighborhood='Centro',
            city='Florianópolis', state='SC',
        )
        self.other_address = Address.objects.create(
            user=self.other_user, label='Outro', cep='88000-111',
            street='Rua B', number='2', neighborhood='Trindade',
            city='Florianópolis', state='SC',
        )

    def _data(self, **overrides):
        data = {
            'title': 'Pintar sala',
            'description': 'Preciso pintar a sala de 20m².',
            'category': self.category.pk,
            'address': self.address.pk,
            'urgency': 'MEDIA',
            'budget_max': '1000.00',
            'desired_deadline': (date.today() + timedelta(days=14)).isoformat(),
        }
        data.update(overrides)
        return data

    def test_form_valido_com_dados_corretos(self):
        form = ServiceRequestForm(self._data(), user=self.citizen)
        self.assertTrue(form.is_valid(), form.errors)

    def test_budget_max_negativo_invalido(self):
        form = ServiceRequestForm(self._data(budget_max='-50'), user=self.citizen)
        self.assertFalse(form.is_valid())
        self.assertIn('budget_max', form.errors)

    def test_budget_max_zero_invalido(self):
        form = ServiceRequestForm(self._data(budget_max='0'), user=self.citizen)
        self.assertFalse(form.is_valid())
        self.assertIn('budget_max', form.errors)

    def test_deadline_no_passado_invalido(self):
        form = ServiceRequestForm(
            self._data(desired_deadline=(date.today() - timedelta(days=1)).isoformat()),
            user=self.citizen,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('desired_deadline', form.errors)

    def test_endereco_de_outro_usuario_invalido(self):
        form = ServiceRequestForm(
            self._data(address=self.other_address.pk),
            user=self.citizen,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('address', form.errors)


class ServiceRequestMediaFormTest(TestCase):
    """Testes das validações do ServiceRequestMediaForm."""

    def _make_image(self, name='foto.jpg', size=1024):
        f = SimpleUploadedFile(name, b'\x00' * size, content_type='image/jpeg')
        return f

    def test_tipo_nao_permitido_invalido(self):
        bad_file = SimpleUploadedFile('doc.pdf', b'%PDF', content_type='application/pdf')
        form = ServiceRequestMediaForm(
            {}, {'files': [bad_file]},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('files', form.errors)

    def test_upload_ate_5_permitido(self):
        files = [self._make_image(f'img{i}.jpg') for i in range(5)]
        form = ServiceRequestMediaForm({}, {'files': files})
        self.assertTrue(form.is_valid(), form.errors)

    def test_upload_excedendo_5_midias_invalido(self):
        files = [self._make_image(f'img{i}.jpg') for i in range(6)]
        form = ServiceRequestMediaForm({}, {'files': files})
        self.assertFalse(form.is_valid())
        self.assertIn('files', form.errors)


# ─── View Tests ──────────────────────────────────────────────────────────────


class ServiceViewBaseTestCase(TestCase):
    """Fixture base: cidadão, MEI verificado, categoria, address, service request."""

    def setUp(self):
        self.citizen = make_user('citizen@view.test', 'CIDADAO')
        self.citizen_profile = self.citizen.citizen_profile

        self.mei_user = make_user('mei@view.test', 'MEI')
        self.mei_profile = MEIProfile.objects.create(
            user=self.mei_user,
            cnpj='11.111.111/0001-11',
            razao_social='MEI Teste',
            nome_fantasia='MEI Teste',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
        )

        self.category = ServiceCategory.objects.create(
            name='Encanamento', slug='encanamento', is_active=True,
        )

        self.address = Address.objects.create(
            user=self.citizen, label='Casa', cep='88000-000',
            street='Rua Teste', number='100', neighborhood='Centro',
            city='Florianópolis', state='SC',
        )

        self.service_request = ServiceRequest.objects.create(
            citizen=self.citizen_profile,
            title='Conserto de cano',
            description='Torneira vazando.',
            category=self.category,
            address=self.address,
            urgency='ALTA',
            budget_max=Decimal('500.00'),
            desired_deadline=date.today() + timedelta(days=14),
        )

        MEICategorySubscription.objects.create(
            mei_profile=self.mei_profile, category=self.category, is_active=True,
        )

        self.citizen_client = Client()
        self.citizen_client.login(email='citizen@view.test', password='senha123')

        self.mei_client = Client()
        self.mei_client.login(email='mei@view.test', password='senha123')


class ServiceRequestCreateViewTest(ServiceViewBaseTestCase):

    def test_get_renderiza_formulario(self):
        r = self.citizen_client.get(reverse('services:service_request_create'))
        self.assertEqual(r.status_code, 200)

    def test_post_valido_cria_solicitacao(self):
        r = self.citizen_client.post(reverse('services:service_request_create'), {
            'title': 'Nova solicitação',
            'description': 'Descrição do serviço.',
            'category': self.category.pk,
            'address': self.address.pk,
            'urgency': 'MEDIA',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(ServiceRequest.objects.filter(title='Nova solicitação').exists())

    def test_mei_nao_acessa_criar_solicitacao(self):
        r = self.mei_client.get(reverse('services:service_request_create'))
        self.assertEqual(r.status_code, 403)


class ServiceRequestDetailViewTest(ServiceViewBaseTestCase):

    def test_dono_acessa_detalhe(self):
        r = self.citizen_client.get(
            reverse('services:service_request_detail', kwargs={'pk': self.service_request.pk})
        )
        self.assertEqual(r.status_code, 200)

    def test_mei_acessa_detalhe(self):
        r = self.mei_client.get(
            reverse('services:service_request_detail', kwargs={'pk': self.service_request.pk})
        )
        self.assertEqual(r.status_code, 200)

    def test_outro_cidadao_nao_acessa_detalhe(self):
        other = make_user('other@view.test', 'CIDADAO')
        c = Client()
        c.login(email='other@view.test', password='senha123')
        r = c.get(
            reverse('services:service_request_detail', kwargs={'pk': self.service_request.pk})
        )
        self.assertEqual(r.status_code, 302)


class RequestFeedViewTest(ServiceViewBaseTestCase):

    def test_mei_acessa_feed(self):
        r = self.mei_client.get(reverse('services:request_feed'))
        self.assertEqual(r.status_code, 200)

    def test_cidadao_nao_acessa_feed(self):
        r = self.citizen_client.get(reverse('services:request_feed'))
        self.assertEqual(r.status_code, 403)


class ServiceRequestCancelViewTest(ServiceViewBaseTestCase):

    def test_cidadao_cancela_solicitacao(self):
        r = self.citizen_client.post(
            reverse('services:service_request_cancel', kwargs={'pk': self.service_request.pk})
        )
        self.assertEqual(r.status_code, 302)
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.CANCELLED)


class AwardBidViewTest(ServiceViewBaseTestCase):

    def setUp(self):
        super().setUp()
        self.bid = Bid.objects.create(
            service_request=self.service_request,
            mei_profile=self.mei_profile,
            amount=Decimal('300.00'),
            estimated_hours=Decimal('3'),
            proposed_deadline=date.today() + timedelta(days=7),
        )

    def test_award_cria_order(self):
        r = self.citizen_client.post(
            reverse('services:award_bid', kwargs={'bid_pk': self.bid.pk})
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ServiceOrder.objects.count(), 1)
        order = ServiceOrder.objects.first()
        self.assertEqual(order.winning_bid_id, self.bid.pk)
        self.assertEqual(order.agreed_amount, self.bid.amount)

    def test_award_muda_status_da_solicitacao(self):
        self.citizen_client.post(
            reverse('services:award_bid', kwargs={'bid_pk': self.bid.pk})
        )
        self.service_request.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.Status.AWARDED)
