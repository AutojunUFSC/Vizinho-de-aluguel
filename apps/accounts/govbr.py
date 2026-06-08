"""
Utilitários para a integração com o Login Único Gov.BR.

OpenID Connect sobre OAuth2 (Authorization Code Flow + PKCE obrigatório).
Implementação manual com `requests` + `PyJWT` para ter controle total sobre
as particularidades do Gov.BR (ver Integra_gov_br.md).

Este módulo NÃO contém lógica de view — apenas funções puras/utilitárias.
Toda configuração vem de `settings` (variáveis GOVBR_*), nunca chumbada aqui.
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings

# Tempo máximo (s) de espera nas chamadas HTTP ao provedor Gov.BR.
_HTTP_TIMEOUT = 15


def _endpoints():
    """Monta as URLs do provedor a partir de settings.GOVBR_PROVIDER_URL."""
    base = settings.GOVBR_PROVIDER_URL.rstrip('/')
    return {
        'authorize': f'{base}/authorize',
        'token': f'{base}/token',
        'jwk': f'{base}/jwk',
        'userinfo': f'{base}/userinfo/',
        'logout': f'{base}/logout',
    }


def random_token(n_bytes=32):
    """Gera um token aleatório URL-safe (para state e nonce)."""
    return secrets.token_urlsafe(n_bytes)


def generate_pkce_pair():
    """
    Gera (code_verifier, code_challenge) para PKCE com método S256.

    - code_verifier: string URL-safe entre 43 e 128 caracteres (exigência Gov.BR).
    - code_challenge: BASE64URL(SHA256(code_verifier)) sem padding '='.
    """
    # token_urlsafe(64) -> ~86 chars, dentro da faixa 43–128.
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return code_verifier, code_challenge


def build_authorize_url(state, nonce, code_challenge):
    """Monta a URL de /authorize (GET) com todos os parâmetros obrigatórios."""
    params = {
        'response_type': 'code',
        'client_id': settings.GOVBR_CLIENT_ID,
        'scope': settings.GOVBR_SCOPES,
        'redirect_uri': settings.GOVBR_REDIRECT_URI,
        'nonce': nonce,
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    # quote_via padrão troca espaços por '+', que é o separador esperado nos scopes.
    return f"{_endpoints()['authorize']}?{urlencode(params)}"


def _basic_auth_header():
    """Header Authorization: Basic base64(client_id:client_secret)."""
    raw = f'{settings.GOVBR_CLIENT_ID}:{settings.GOVBR_CLIENT_SECRET}'.encode('utf-8')
    return 'Basic ' + base64.b64encode(raw).decode('ascii')


def exchange_code_for_tokens(code, code_verifier):
    """
    Troca o authorization code por tokens (POST /token).

    Retorna o dict de resposta (access_token, id_token, token_type, ...).
    Levanta requests.HTTPError em caso de erro HTTP.
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': _basic_auth_header(),
    }
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.GOVBR_REDIRECT_URI,
        'code_verifier': code_verifier,
    }
    resp = requests.post(
        _endpoints()['token'], headers=headers, data=data, timeout=_HTTP_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def get_jwks():
    """Baixa o conjunto de chaves públicas (JWKS) do provedor (/jwk)."""
    resp = requests.get(_endpoints()['jwk'], timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def validate_id_token(id_token, nonce, jwks=None):
    """
    Valida a assinatura RS256 do id_token contra o JWK e confere os claims.

    Confere: assinatura, aud == client_id, exp (com folga), e nonce == nonce salvo
    na sessão. Retorna os claims validados (dict).

    Levanta jwt.InvalidTokenError (ou subclasses) se algo for inválido.
    """
    if jwks is None:
        jwks = get_jwks()

    # Seleciona a chave pelo 'kid' do header do token (com fallback p/ a 1ª chave).
    header = jwt.get_unverified_header(id_token)
    kid = header.get('kid')
    keys = jwks.get('keys', jwks if isinstance(jwks, list) else [])
    signing_key = None
    for key in keys:
        if kid is None or key.get('kid') == kid:
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            break
    if signing_key is None:
        raise jwt.InvalidTokenError('Nenhuma chave JWK compatível com o id_token.')

    claims = jwt.decode(
        id_token,
        key=signing_key,
        algorithms=['RS256'],
        audience=settings.GOVBR_CLIENT_ID,
        options={'require': ['exp', 'aud']},
    )

    if nonce is not None and claims.get('nonce') != nonce:
        raise jwt.InvalidTokenError('nonce do id_token não confere com o da sessão.')

    return claims


def get_userinfo(access_token):
    """
    Consulta o endpoint /userinfo com o access_token (fallback do id_token).

    O id_token NUNCA é usado aqui — só o access_token vai no header Bearer.
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        _endpoints()['userinfo'], headers=headers, timeout=_HTTP_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def build_logout_url():
    """Monta a URL de /logout do Gov.BR com post_logout_redirect_uri."""
    params = {'post_logout_redirect_uri': settings.GOVBR_LOGOUT_REDIRECT_URI}
    return f"{_endpoints()['logout']}?{urlencode(params)}"
