"""
Testes unitários da integração Gov.BR (PKCE, montagem de URLs, validação de
id_token RS256, troca de tokens e regra de vínculo/criação de usuário).

Não dependem de credenciais reais: o JWK/assinatura é gerado localmente e as
chamadas HTTP ao Gov.BR são mockadas.
"""

import base64
import hashlib
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from django.test import TestCase, override_settings
from django.urls import reverse

from . import govbr
from .models import CitizenProfile, User
from .views import _govbr_user_from_claims, _only_digits

GOVBR_TEST_SETTINGS = dict(
    GOVBR_CLIENT_ID='client-test',
    GOVBR_CLIENT_SECRET='secret-test',
    GOVBR_REDIRECT_URI='https://app.example/accounts/govbr/callback/',
    GOVBR_LOGOUT_REDIRECT_URI='https://app.example/',
    GOVBR_PROVIDER_URL='https://sso.staging.acesso.gov.br',
    GOVBR_SCOPES='openid email profile',
)


def _make_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk['kid'] = 'test-key'
    return pem, jwk


def _sign_id_token(pem, jwk, claims):
    return jwt.encode(claims, pem, algorithm='RS256', headers={'kid': jwk['kid']})


@override_settings(**GOVBR_TEST_SETTINGS)
class PkceTests(TestCase):
    def test_pkce_pair_length_and_challenge(self):
        verifier, challenge = govbr.generate_pkce_pair()
        self.assertGreaterEqual(len(verifier), 43)
        self.assertLessEqual(len(verifier), 128)
        # challenge deve ser BASE64URL(SHA256(verifier)) sem padding.
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('ascii')).digest()
        ).decode('ascii').rstrip('=')
        self.assertEqual(challenge, expected)
        self.assertNotIn('=', challenge)

    def test_random_tokens_are_unique(self):
        self.assertNotEqual(govbr.random_token(), govbr.random_token())


@override_settings(**GOVBR_TEST_SETTINGS)
class AuthorizeUrlTests(TestCase):
    def test_authorize_url_has_required_params(self):
        url = govbr.build_authorize_url('st', 'no', 'chal')
        qs = parse_qs(urlparse(url).query)
        self.assertEqual(qs['response_type'], ['code'])
        self.assertEqual(qs['client_id'], ['client-test'])
        self.assertEqual(qs['redirect_uri'], [GOVBR_TEST_SETTINGS['GOVBR_REDIRECT_URI']])
        self.assertEqual(qs['state'], ['st'])
        self.assertEqual(qs['nonce'], ['no'])
        self.assertEqual(qs['code_challenge'], ['chal'])
        self.assertEqual(qs['code_challenge_method'], ['S256'])
        self.assertTrue(url.startswith('https://sso.staging.acesso.gov.br/authorize?'))


@override_settings(**GOVBR_TEST_SETTINGS)
class ValidateIdTokenTests(TestCase):
    def setUp(self):
        self.pem, self.jwk = _make_rsa_keypair()
        self.jwks = {'keys': [self.jwk]}

    def _claims(self, **overrides):
        base = {
            'sub': '12345678909',
            'aud': 'client-test',
            'iss': GOVBR_TEST_SETTINGS['GOVBR_PROVIDER_URL'],
            'exp': int(time.time()) + 60,
            'nonce': 'nonce-ok',
            'name': 'Maria Souza',
        }
        base.update(overrides)
        return base

    def test_valid_token_passes(self):
        token = _sign_id_token(self.pem, self.jwk, self._claims())
        claims = govbr.validate_id_token(token, 'nonce-ok', jwks=self.jwks)
        self.assertEqual(claims['sub'], '12345678909')

    def test_wrong_audience_rejected(self):
        token = _sign_id_token(self.pem, self.jwk, self._claims(aud='outro'))
        with self.assertRaises(jwt.InvalidTokenError):
            govbr.validate_id_token(token, 'nonce-ok', jwks=self.jwks)

    def test_wrong_nonce_rejected(self):
        token = _sign_id_token(self.pem, self.jwk, self._claims(nonce='nonce-x'))
        with self.assertRaises(jwt.InvalidTokenError):
            govbr.validate_id_token(token, 'nonce-ok', jwks=self.jwks)

    def test_expired_token_rejected(self):
        token = _sign_id_token(self.pem, self.jwk, self._claims(exp=int(time.time()) - 10))
        with self.assertRaises(jwt.InvalidTokenError):
            govbr.validate_id_token(token, 'nonce-ok', jwks=self.jwks)


@override_settings(**GOVBR_TEST_SETTINGS)
class ExchangeTokensTests(TestCase):
    def test_exchange_builds_basic_auth_and_body(self):
        fake = mock.Mock()
        fake.json.return_value = {'access_token': 'a', 'id_token': 'b'}
        fake.raise_for_status.return_value = None
        with mock.patch('apps.accounts.govbr.requests.post', return_value=fake) as post:
            result = govbr.exchange_code_for_tokens('the-code', 'the-verifier')
        self.assertEqual(result['id_token'], 'b')
        _, kwargs = post.call_args
        # Basic base64(client_id:client_secret)
        expected_basic = 'Basic ' + base64.b64encode(b'client-test:secret-test').decode()
        self.assertEqual(kwargs['headers']['Authorization'], expected_basic)
        self.assertEqual(kwargs['data']['grant_type'], 'authorization_code')
        self.assertEqual(kwargs['data']['code'], 'the-code')
        self.assertEqual(kwargs['data']['code_verifier'], 'the-verifier')


@override_settings(**GOVBR_TEST_SETTINGS)
class AccountLinkingTests(TestCase):
    def test_existing_cpf_logs_into_same_user(self):
        existing = User.objects.create_user(
            email='maria@example.com', password='x',
            full_name='Maria', user_type=User.UserType.CIDADAO,
            cpf='123.456.789-09',
        )
        user, created = _govbr_user_from_claims({
            'sub': '12345678909', 'name': 'Maria Souza',
        })
        self.assertFalse(created)
        self.assertEqual(user.pk, existing.pk)
        self.assertTrue(user.govbr_verified)

    def test_new_cpf_creates_citizen_with_profile(self):
        user, created = _govbr_user_from_claims({
            'sub': '98765432100', 'name': 'João Lima',
            'email': 'joao@example.com', 'email_verified': True,
            'reliability_info': {'level': 'gold'},
        })
        self.assertTrue(created)
        self.assertEqual(user.user_type, User.UserType.CIDADAO)
        self.assertEqual(user.govbr_level, 'gold')
        self.assertFalse(user.has_usable_password())
        self.assertTrue(CitizenProfile.objects.filter(user=user).exists())

    def test_verified_email_links_and_fills_cpf(self):
        existing = User.objects.create_user(
            email='ze@example.com', password='x',
            full_name='Zé', user_type=User.UserType.CIDADAO,
        )
        user, created = _govbr_user_from_claims({
            'sub': '11144477735', 'name': 'Zé', 'email': 'ze@example.com',
            'email_verified': True,
        })
        self.assertFalse(created)
        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(_only_digits(user.cpf), '11144477735')


@override_settings(**GOVBR_TEST_SETTINGS)
class CallbackViewTests(TestCase):
    def test_callback_with_mismatched_state_redirects_to_cadastro(self):
        session = self.client.session
        session['govbr_state'] = 'real-state'
        session['govbr_code_verifier'] = 'v'
        session['govbr_nonce'] = 'n'
        session.save()
        resp = self.client.get(
            reverse('accounts:govbr_callback'),
            {'code': 'abc', 'state': 'WRONG'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(urlparse(resp['Location']).path, '/cadastro/')

    def test_login_view_redirects_to_authorize(self):
        resp = self.client.get(reverse('accounts:govbr_login'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp['Location'].startswith(
            'https://sso.staging.acesso.gov.br/authorize?'))
        # PKCE/state/nonce ficam na sessão.
        self.assertIn('govbr_code_verifier', self.client.session)
        self.assertIn('govbr_state', self.client.session)
