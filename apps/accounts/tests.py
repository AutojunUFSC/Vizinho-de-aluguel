from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.backends import EmailBackend
from apps.accounts.models import CitizenProfile, MEIProfile

User = get_user_model()


# ─── Modelo User ─────────────────────────────────────────────────────────────

class UserModelTest(TestCase):

    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')

    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email='cidadao@test.com',
            full_name='Cidadão Teste',
            user_type='CIDADAO',
            password='senha-forte-123',
        )
        self.assertEqual(user.email, 'cidadao@test.com')
        self.assertTrue(user.check_password('senha-forte-123'))

    def test_email_must_be_unique(self):
        User.objects.create_user(
            email='dup@test.com', full_name='X',
            user_type='CIDADAO', password='senha-forte-123',
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='dup@test.com', full_name='Y',
                user_type='CIDADAO', password='senha-forte-123',
            )


# ─── Signal create_user_profile ──────────────────────────────────────────────

class CitizenSignalTest(TestCase):
    """O signal cria CitizenProfile automaticamente para user_type=CIDADAO."""

    def test_signal_creates_citizen_profile_for_cidadao(self):
        user = User.objects.create_user(
            email='cidadao@signal.test', full_name='Cidadão Signal',
            user_type='CIDADAO', password='senha-forte-123',
        )
        self.assertTrue(CitizenProfile.objects.filter(user=user).exists())

    def test_signal_does_not_create_mei_profile_for_cidadao(self):
        user = User.objects.create_user(
            email='cidadao2@signal.test', full_name='Cidadão Signal',
            user_type='CIDADAO', password='senha-forte-123',
        )
        self.assertFalse(MEIProfile.objects.filter(user=user).exists())

    def test_signal_does_not_create_profile_on_update(self):
        user = User.objects.create_user(
            email='update@signal.test', full_name='Cidadão Update',
            user_type='CIDADAO', password='senha-forte-123',
        )
        user.full_name = 'Novo Nome'
        user.save()
        self.assertEqual(CitizenProfile.objects.filter(user=user).count(), 1)

    def test_citizen_profile_default_rating_is_zero(self):
        user = User.objects.create_user(
            email='rating@signal.test', full_name='X',
            user_type='CIDADAO', password='senha-forte-123',
        )
        self.assertEqual(user.citizen_profile.rating_avg, 0)


# ─── Custom EmailBackend ─────────────────────────────────────────────────────

class EmailBackendTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='login@test.com', full_name='Login User',
            user_type='CIDADAO', password='senha-forte-123',
        )
        self.backend = EmailBackend()

    def test_authenticate_with_correct_email_and_password(self):
        result = self.backend.authenticate(
            request=None, email='login@test.com', password='senha-forte-123',
        )
        self.assertEqual(result, self.user)

    def test_authenticate_is_case_insensitive_for_email(self):
        result = self.backend.authenticate(
            request=None, email='LOGIN@TEST.COM', password='senha-forte-123',
        )
        self.assertEqual(result, self.user)

    def test_authenticate_returns_none_for_wrong_password(self):
        result = self.backend.authenticate(
            request=None, email='login@test.com', password='senha-errada',
        )
        self.assertIsNone(result)

    def test_authenticate_returns_none_for_unknown_email(self):
        result = self.backend.authenticate(
            request=None, email='ninguem@test.com', password='senha-forte-123',
        )
        self.assertIsNone(result)


# ─── Fluxo cadastro_view (Cliente Django, não APIClient) ─────────────────────

class CadastroViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('cadastro')

    def test_get_renders_form(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Acessar conta')

    def test_post_register_cidadao_cria_user_e_loga(self):
        r = self.client.post(self.url, {
            'action': 'register',
            'user_type': 'CIDADAO',
            'full_name': 'Novo Cidadão',
            'email': 'novo@test.com',
            'password': 'senha-forte-123',
            'password_confirm': 'senha-forte-123',
        })
        # Redireciona para /usuario/ após cadastro
        self.assertEqual(r.status_code, 302)
        user = User.objects.get(email='novo@test.com')
        self.assertEqual(user.user_type, 'CIDADAO')
        self.assertTrue(CitizenProfile.objects.filter(user=user).exists())

    def test_post_register_passwords_dont_match_returns_form_with_error(self):
        r = self.client.post(self.url, {
            'action': 'register',
            'user_type': 'CIDADAO',
            'full_name': 'X',
            'email': 'mismatch@test.com',
            'password': 'senha-forte-123',
            'password_confirm': 'outra-senha',
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email='mismatch@test.com').exists())

    def test_post_login_redireciona_para_usuario_quando_cidadao(self):
        User.objects.create_user(
            email='loginok@test.com', full_name='X',
            user_type='CIDADAO', password='senha-forte-123',
        )
        r = self.client.post(self.url, {
            'action': 'login',
            'username': 'loginok@test.com',
            'password': 'senha-forte-123',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/usuario/perfil/')

    def test_post_login_invalido_re_renderiza_form(self):
        User.objects.create_user(
            email='loginbad@test.com', full_name='X',
            user_type='CIDADAO', password='senha-forte-123',
        )
        r = self.client.post(self.url, {
            'action': 'login',
            'username': 'loginbad@test.com',
            'password': 'senha-errada',
        })
        self.assertEqual(r.status_code, 200)

    def test_get_when_logged_in_redirects(self):
        User.objects.create_user(
            email='already@test.com', full_name='X',
            user_type='CIDADAO', password='senha-forte-123',
        )
        self.client.login(email='already@test.com', password='senha-forte-123')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)


# ─── logout_view ─────────────────────────────────────────────────────────────

class LogoutViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            email='logout@test.com', full_name='X',
            user_type='CIDADAO', password='senha-forte-123',
        )
        self.client.login(email='logout@test.com', password='senha-forte-123')

    def test_logout_redirects_to_home(self):
        r = self.client.post(reverse('accounts:logout'))
        self.assertEqual(r.status_code, 302)

    def test_logout_actually_logs_out(self):
        self.client.post(reverse('accounts:logout'))
        # /usuario/ requer @citizen_required, deve redirecionar para /cadastro/
        r = self.client.get('/usuario/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/cadastro/', r.url)


# ─── Proteção de rotas (decorators) ──────────────────────────────────────────

class RouteProtectionTest(TestCase):

    def setUp(self):
        self.client = Client()
        from apps.accounts.models import MEIProfile
        # Cria CIDADAO + MEI verificados
        User.objects.create_user(
            email='cit@test.com', full_name='C',
            user_type='CIDADAO', password='senha-forte-123',
        )
        mei_user = User.objects.create_user(
            email='mei@test.com', full_name='M',
            user_type='MEI', password='senha-forte-123',
        )
        MEIProfile.objects.create(
            user=mei_user, cnpj='99.999.999/0001-99',
            razao_social='X', nome_fantasia='X',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
        )

    def test_anon_acessando_usuario_redireciona_para_cadastro(self):
        r = self.client.get('/usuario/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/cadastro/', r.url)

    def test_cidadao_acessando_profissional_recebe_403(self):
        self.client.login(email='cit@test.com', password='senha-forte-123')
        r = self.client.get('/profissional/')
        self.assertEqual(r.status_code, 403)

    def test_mei_acessando_usuario_recebe_403(self):
        self.client.login(email='mei@test.com', password='senha-forte-123')
        r = self.client.get('/usuario/')
        self.assertEqual(r.status_code, 403)


# ─── toggle_availability ─────────────────────────────────────────────────────

class ToggleAvailabilityTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:toggle_availability')

        self.mei_user = User.objects.create_user(
            email='mei@toggle.test', full_name='MEI',
            user_type='MEI', password='senha-forte-123',
        )
        self.mei_profile = MEIProfile.objects.create(
            user=self.mei_user, cnpj='88.888.888/0001-88',
            razao_social='X', nome_fantasia='X',
            verification_status=MEIProfile.VerificationStatus.VERIFIED,
            is_available=True,
        )
        User.objects.create_user(
            email='cit@toggle.test', full_name='C',
            user_type='CIDADAO', password='senha-forte-123',
        )

    def test_toggle_inverte_is_available_e_redireciona(self):
        self.client.login(email='mei@toggle.test', password='senha-forte-123')
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)
        self.mei_profile.refresh_from_db()
        self.assertFalse(self.mei_profile.is_available)

    def test_toggle_duas_vezes_volta_ao_estado_original(self):
        self.client.login(email='mei@toggle.test', password='senha-forte-123')
        self.client.post(self.url)
        self.client.post(self.url)
        self.mei_profile.refresh_from_db()
        self.assertTrue(self.mei_profile.is_available)

    def test_toggle_anonimo_redireciona_para_login(self):
        # @mei_required encadeia @login_required → 302 para LOGIN_URL
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/cadastro/', r.url)
        self.mei_profile.refresh_from_db()
        self.assertTrue(self.mei_profile.is_available)  # estado intacto

    def test_toggle_por_cidadao_recebe_403(self):
        self.client.login(email='cit@toggle.test', password='senha-forte-123')
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)
        self.mei_profile.refresh_from_db()
        self.assertTrue(self.mei_profile.is_available)  # estado intacto

    def test_toggle_via_get_recebe_405(self):
        self.client.login(email='mei@toggle.test', password='senha-forte-123')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
