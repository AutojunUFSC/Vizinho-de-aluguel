from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

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

