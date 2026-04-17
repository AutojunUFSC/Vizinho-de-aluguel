from django.test import TestCase
from django.db import IntegrityError
from apps.accounts.models import User, CitizenProfile, MEIProfile


class UserCreationTest(TestCase):

    def _make_user(self, email, user_type, **kwargs):
        return User.objects.create_user(
            email=email,
            full_name='Teste Nome',
            user_type=user_type,
            password='senha123',
            **kwargs,
        )

    def test_cidadao_user_can_be_created_with_email(self):
        user = self._make_user('cidadao@test.com', 'CIDADAO')
        self.assertEqual(user.email, 'cidadao@test.com')
        self.assertTrue(user.check_password('senha123'))

    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')

    def test_email_must_be_unique(self):
        self._make_user('dup@test.com', 'CIDADAO')
        with self.assertRaises(IntegrityError):
            self._make_user('dup@test.com', 'CIDADAO')


class SignalProfileCreationTest(TestCase):

    def test_signal_creates_citizen_profile_for_cidadao(self):
        user = User.objects.create_user(
            email='cidadao@signal.test',
            full_name='Cidadão Signal',
            user_type='CIDADAO',
            password='senha123',
        )
        self.assertTrue(CitizenProfile.objects.filter(user=user).exists())
        self.assertFalse(MEIProfile.objects.filter(user=user).exists())

    def test_signal_creates_mei_profile_for_mei(self):
        user = User.objects.create_user(
            email='mei@signal.test',
            full_name='MEI Signal',
            user_type='MEI',
            password='senha123',
        )
        self.assertTrue(MEIProfile.objects.filter(user=user).exists())
        self.assertFalse(CitizenProfile.objects.filter(user=user).exists())

    def test_citizen_profile_has_correct_defaults(self):
        user = User.objects.create_user(
            email='citizen2@signal.test',
            full_name='Cidadão Defaults',
            user_type='CIDADAO',
            password='senha123',
        )
        profile = CitizenProfile.objects.get(user=user)
        self.assertEqual(profile.rating_avg, 0)
        self.assertEqual(profile.total_services_requested, 0)

    def test_mei_profile_default_verification_is_pending(self):
        user = User.objects.create_user(
            email='mei2@signal.test',
            full_name='MEI Pending',
            user_type='MEI',
            password='senha123',
        )
        profile = MEIProfile.objects.get(user=user)
        self.assertEqual(profile.verification_status, 'PENDING')

    def test_signal_does_not_create_profile_on_update(self):
        user = User.objects.create_user(
            email='update@signal.test',
            full_name='Cidadão Update',
            user_type='CIDADAO',
            password='senha123',
        )
        user.full_name = 'Nome Atualizado'
        user.save()
        # Apenas um CitizenProfile deve existir
        self.assertEqual(CitizenProfile.objects.filter(user=user).count(), 1)

    def test_citizen_profile_related_name_accessible(self):
        user = User.objects.create_user(
            email='rel@signal.test',
            full_name='Cidadão Rel',
            user_type='CIDADAO',
            password='senha123',
        )
        self.assertIsNotNone(user.citizen_profile)

    def test_mei_profile_related_name_accessible(self):
        user = User.objects.create_user(
            email='meirel@signal.test',
            full_name='MEI Rel',
            user_type='MEI',
            password='senha123',
        )
        self.assertIsNotNone(user.mei_profile)
