import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import govbr
from .decorators import mei_required
from .forms import (
    AddressForm,
    CitizenProfileForm,
    CitizenRegisterForm,
    LoginForm,
    MEIProfileForm,
    MEIRegisterForm,
    UserProfileForm,
)
from .models import Address, MEIProfile, User


def _redirect_by_user_type(user, fallback='home'):
    if user.user_type == User.UserType.MEI:
        return redirect('accounts:profile')
    if user.user_type == User.UserType.ADMIN:
        return redirect('/admin/')
    return redirect('accounts:profile')


def cadastro_view(request):
    """
    Página unificada de login + cadastro (Cidadão ou MEI).
    Distingue a ação pelo campo POST 'action' (login | register).
    """
    if request.user.is_authenticated:
        return _redirect_by_user_type(request.user)

    login_form = LoginForm(request)
    register_form_citizen = CitizenRegisterForm()
    register_form_mei = MEIRegisterForm()
    active_tab = request.GET.get('tab', 'entrar')
    if active_tab not in ('entrar', 'cadastrar'):
        active_tab = 'entrar'
    register_user_type = request.GET.get('tipo', 'CIDADAO')
    if register_user_type not in ('CIDADAO', 'MEI'):
        register_user_type = 'CIDADAO'

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'login':
            active_tab = 'entrar'
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                django_login(request, user)
                messages.success(request, f'Bem-vindo(a), {user.full_name}!')
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return _redirect_by_user_type(user)

        elif action == 'register':
            active_tab = 'cadastrar'
            register_user_type = request.POST.get('user_type', 'CIDADAO')

            if register_user_type == 'MEI':
                register_form_mei = MEIRegisterForm(request.POST, request.FILES)
                if register_form_mei.is_valid():
                    user = register_form_mei.save()
                    django_login(
                        request,
                        user,
                        backend='apps.accounts.backends.EmailBackend',
                    )
                    messages.success(request, 'Cadastro MEI criado com sucesso!')
                    return _redirect_by_user_type(user)
            else:
                register_form_citizen = CitizenRegisterForm(request.POST)
                if register_form_citizen.is_valid():
                    user = register_form_citizen.save()
                    django_login(
                        request,
                        user,
                        backend='apps.accounts.backends.EmailBackend',
                    )
                    messages.success(request, 'Cadastro realizado com sucesso!')
                    return _redirect_by_user_type(user)

    return render(request, 'accounts/cadastro.html', {
        'login_form': login_form,
        'register_form_citizen': register_form_citizen,
        'register_form_mei': register_form_mei,
        'active_tab': active_tab,
        'register_user_type': register_user_type,
    })


def login_view(request):
    """Endpoint POST-only que reaproveita o formulário de login do cadastro."""
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            django_login(request, user)
            messages.success(request, f'Bem-vindo(a), {user.full_name}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return _redirect_by_user_type(user)
        for error in form.non_field_errors():
            messages.error(request, error)
    return redirect('cadastro')


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Sessão encerrada.')
    django_logout(request)
    return redirect('home')


@login_required
@require_http_methods(['GET', 'POST'])
def profile_view(request):
    """Edita dados do User + perfil específico (Cidadão ou MEI)."""
    user = request.user
    user_form = UserProfileForm(request.POST or None, request.FILES or None, instance=user)

    from apps.services.models import ServiceRequest
    from apps.orders.models import ServiceOrder

    profile_form = None
    extra_context = {}

    if user.user_type == User.UserType.CIDADAO:
        profile = getattr(user, 'citizen_profile', None)
        profile_form = CitizenProfileForm(
            request.POST or None,
            instance=profile,
            user=user,
        )
        orders_qs = ServiceOrder.objects.filter(citizen=profile) if profile else ServiceOrder.objects.none()
        extra_context['completed_count'] = orders_qs.filter(status=ServiceOrder.Status.COMPLETED).count()
        extra_context['pending_review_count'] = orders_qs.filter(status=ServiceOrder.Status.COMPLETED).exclude(reviews__reviewer=user).count()
        extra_context['profile'] = profile
    elif user.user_type == User.UserType.MEI:
        mei_profile = getattr(user, 'mei_profile', None)
        profile_form = MEIProfileForm(
            request.POST or None,
            instance=mei_profile,
        )
        if mei_profile:
            subscriptions = mei_profile.category_subscriptions.filter(is_active=True)
            subscribed_category_ids = list(subscriptions.values_list('category_id', flat=True))
            feed_qs = ServiceRequest.objects.filter(
                status__in=(ServiceRequest.Status.OPEN, ServiceRequest.Status.IN_AUCTION),
            )
            if subscribed_category_ids:
                feed_qs = feed_qs.filter(category_id__in=subscribed_category_ids)
            
            extra_context['feed_count'] = feed_qs.count()
            extra_context['active_orders_count'] = ServiceOrder.objects.filter(
                mei_profile=mei_profile,
                status=ServiceOrder.Status.IN_PROGRESS,
            ).count()
        else:
            extra_context['feed_count'] = 0
            extra_context['active_orders_count'] = 0

    if request.method == 'POST':
        forms_valid = user_form.is_valid() and (profile_form is None or profile_form.is_valid())
        if forms_valid:
            user_form.save()
            if profile_form is not None:
                profile_form.save()
            messages.success(request, 'Perfil atualizado.')
            return redirect('accounts:profile')
        messages.error(request, 'Verifique os erros no formulário.')

    if user.user_type == User.UserType.MEI:
        template_name = 'accounts/perfil_profissional.html'
    else:
        template_name = 'accounts/perfil_cidadao.html'

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    context.update(extra_context)

    return render(request, template_name, context)


def mei_list(request):
    """Lista pública de MEIs ativos. Filtros: ?city= e ?is_available=1."""
    qs = MEIProfile.objects.filter(user__is_active=True).select_related('user')
    city = request.GET.get('city')
    is_available = request.GET.get('is_available')
    if city:
        qs = qs.filter(city__icontains=city)
    if is_available:
        qs = qs.filter(is_available=True)
    return render(request, 'accounts/mei_list.html', {'meis': qs})


def mei_detail(request, pk):
    """Página pública de um MEI."""
    mei = get_object_or_404(MEIProfile, pk=pk, user__is_active=True)
    return render(request, 'accounts/mei_detail.html', {'mei': mei})


@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'accounts/enderecos.html', {'addresses': addresses})


@login_required
@require_http_methods(['GET', 'POST'])
def address_create(request):
    form = AddressForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        address.save()
        messages.success(request, 'Endereço cadastrado.')
        return redirect('accounts:address_list')
    return render(request, 'accounts/endereco_form.html', {'form': form, 'mode': 'create'})


@login_required
@require_http_methods(['GET', 'POST'])
def address_update(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Endereço atualizado.')
        return redirect('accounts:address_list')
    return render(request, 'accounts/endereco_form.html', {'form': form, 'mode': 'update'})


@login_required
@require_POST
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    messages.success(request, 'Endereço removido.')
    return redirect('accounts:address_list')


@mei_required
@require_POST
def toggle_availability(request):
    mei_profile = request.user.mei_profile
    mei_profile.is_available = not mei_profile.is_available
    mei_profile.save(update_fields=['is_available'])
    if mei_profile.is_available:
        messages.success(request, 'Você agora está recebendo novos pedidos.')
    else:
        messages.warning(request, 'Sua disponibilidade foi pausada.')
    return redirect('accounts:profile')


# ──────────────────────────────────────────────────────────────────────────────
# Login Único Gov.BR (OAuth2 + OIDC + PKCE) — ver Integra_gov_br.md
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# Chaves usadas na sessão durante o fluxo OIDC.
_SESS_VERIFIER = 'govbr_code_verifier'
_SESS_STATE = 'govbr_state'
_SESS_NONCE = 'govbr_nonce'


def _only_digits(value):
    return ''.join(c for c in (value or '') if c.isdigit())


def _govbr_user_from_claims(claims):
    """
    Vincula ou cria o usuário local a partir dos claims validados do Gov.BR.

    Estratégia de vínculo (CPF sempre comparado por dígitos):
      1) usuário cujo CPF == CPF do gov.br  → loga nele;
      2) senão, usuário com o e-mail verificado do gov.br → vincula CPF e loga;
      3) senão, cria um novo usuário CIDADAO (sem senha utilizável).
    """
    cpf = _only_digits(claims.get('sub') or claims.get('preferred_username'))
    name = claims.get('social_name') or claims.get('name') or ''
    email = claims.get('email') if claims.get('email_verified') else None
    level = (claims.get('reliability_info') or {}).get('level', '') if isinstance(
        claims.get('reliability_info'), dict
    ) else ''

    user = None
    # 1) match por CPF (normalizado).
    for candidate in User.objects.exclude(cpf__isnull=True).exclude(cpf=''):
        if _only_digits(candidate.cpf) == cpf and cpf:
            user = candidate
            break

    # 2) match por e-mail verificado.
    if user is None and email:
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and not _only_digits(user.cpf) and cpf:
            user.cpf = cpf

    created = False
    if user is None:
        # 3) cria novo CIDADAO. O signal cria o CitizenProfile automaticamente.
        created = True
        user = User(
            user_type=User.UserType.CIDADAO,
            full_name=name or (email.split('@')[0] if email else f'gov.br {cpf}'),
            email=email or f'{cpf}@govbr.local',
            cpf=cpf or None,
        )
        user.set_unusable_password()

    # Atualiza dados de confiabilidade Gov.BR em todos os casos.
    user.govbr_verified = True
    if level:
        user.govbr_level = level
    if name and not user.full_name:
        user.full_name = name
    user.save()
    return user, created


def govbr_login(request):
    """Inicia o fluxo OIDC: gera PKCE/state/nonce, salva na sessão e redireciona."""
    if not settings.GOVBR_CLIENT_ID or not settings.GOVBR_REDIRECT_URI:
        messages.error(request, 'Login Gov.BR ainda não está configurado.')
        return redirect('cadastro')

    code_verifier, code_challenge = govbr.generate_pkce_pair()
    state = govbr.random_token()
    nonce = govbr.random_token()

    request.session[_SESS_VERIFIER] = code_verifier
    request.session[_SESS_STATE] = state
    request.session[_SESS_NONCE] = nonce

    return redirect(govbr.build_authorize_url(state, nonce, code_challenge))


def govbr_callback(request):
    """
    Recebe o authorization code, valida state/token e abre a sessão Django.

    A tela que recebe o `code` NÃO renderiza conteúdo — sempre redireciona.
    """
    error = request.GET.get('error')
    if error:
        logger.warning('Gov.BR retornou erro: %s — %s', error, request.GET.get('error_description'))
        messages.error(request, 'Não foi possível autenticar com o Gov.BR. Tente novamente.')
        return redirect('cadastro')

    code = request.GET.get('code')
    returned_state = request.GET.get('state')
    saved_state = request.session.pop(_SESS_STATE, None)
    code_verifier = request.session.pop(_SESS_VERIFIER, None)
    nonce = request.session.pop(_SESS_NONCE, None)

    if not code or not returned_state or returned_state != saved_state or not code_verifier:
        logger.warning('Gov.BR callback inválido: state divergente ou parâmetros ausentes.')
        messages.error(request, 'Sessão de login Gov.BR inválida ou expirada. Tente novamente.')
        return redirect('cadastro')

    try:
        tokens = govbr.exchange_code_for_tokens(code, code_verifier)
        id_token = tokens.get('id_token')
        claims = govbr.validate_id_token(id_token, nonce)
    except Exception:
        logger.exception('Falha ao trocar/validar tokens do Gov.BR.')
        messages.error(request, 'Falha ao validar a autenticação Gov.BR. Tente novamente.')
        return redirect('cadastro')

    user, created = _govbr_user_from_claims(claims)
    django_login(request, user, backend='apps.accounts.backends.EmailBackend')
    request.session['govbr'] = True  # marca a sessão como originada do Gov.BR

    if created:
        messages.success(request, f'Conta criada via Gov.BR. Bem-vindo(a), {user.first_name}!')
    else:
        messages.success(request, f'Bem-vindo(a), {user.first_name}!')
    return _redirect_by_user_type(user)


@require_POST
def govbr_logout(request):
    """Encerra a sessão Django e redireciona ao /logout do Gov.BR (disparado pelo front)."""
    django_logout(request)
    if settings.GOVBR_LOGOUT_REDIRECT_URI:
        return redirect(govbr.build_logout_url())
    return redirect('home')

