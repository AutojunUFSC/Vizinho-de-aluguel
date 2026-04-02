from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetConfirmView
from django.contrib import messages
from django.urls import reverse_lazy

from .models import User, CitizenProfile, MEIProfile, Address
from .forms import (
    LoginForm, CitizenRegisterForm, MEIRegisterForm,
    UserProfileForm, CitizenProfileForm, MEIProfileForm, AddressForm,
)
from .decorators import citizen_required, mei_required


# --- Auth ---

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.user_type == User.UserType.MEI:
            return reverse_lazy('dashboard_mei')
        return reverse_lazy('dashboard_citizen')


class CustomLogoutView(LogoutView):
    next_page = '/'


def register_citizen(request):
    if request.method == 'POST':
        form = CitizenRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('dashboard_citizen')
    else:
        form = CitizenRegisterForm()
    return render(request, 'accounts/register_citizen.html', {'form': form})


def register_mei(request):
    if request.method == 'POST':
        form = MEIRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso! Seu CNPJ será verificado em breve.')
            return redirect('dashboard_mei')
    else:
        form = MEIRegisterForm()
    return render(request, 'accounts/register_mei.html', {'form': form})


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    success_url = reverse_lazy('password_reset_done')
    email_template_name = 'accounts/password_reset_email.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('login')


# --- Dashboard ---

@citizen_required
def dashboard_citizen(request):
    citizen = request.user.citizen_profile
    context = {
        'citizen': citizen,
    }
    return render(request, 'accounts/dashboard_citizen.html', context)


@mei_required
def dashboard_mei(request):
    mei = request.user.mei_profile
    context = {
        'mei': mei,
    }
    return render(request, 'accounts/dashboard_mei.html', context)


# --- Perfil ---

@login_required
def my_profile(request):
    user = request.user
    user_form = UserProfileForm(instance=user)
    profile_form = None

    if user.user_type == User.UserType.CIDADAO:
        profile_form = CitizenProfileForm(instance=user.citizen_profile, user=user)
    elif user.user_type == User.UserType.MEI:
        profile_form = MEIProfileForm(instance=user.mei_profile)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        if user.user_type == User.UserType.CIDADAO:
            profile_form = CitizenProfileForm(request.POST, instance=user.citizen_profile, user=user)
        elif user.user_type == User.UserType.MEI:
            profile_form = MEIProfileForm(request.POST, instance=user.mei_profile)

        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('my_profile')

    addresses = Address.objects.filter(user=user)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'addresses': addresses,
    }
    return render(request, 'accounts/my_profile.html', context)


# --- Perfil Público ---

def mei_public_profile(request, pk):
    mei = get_object_or_404(MEIProfile, pk=pk, user__is_active=True)
    context = {'mei': mei}
    return render(request, 'accounts/mei_public_profile.html', context)


@login_required
def citizen_public_profile(request, pk):
    citizen = get_object_or_404(CitizenProfile, pk=pk, user__is_active=True)
    context = {'citizen': citizen}
    return render(request, 'accounts/citizen_public_profile.html', context)


# --- Endereços ---

@login_required
def address_create(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Endereço adicionado com sucesso!')
            return redirect('my_profile')
    else:
        form = AddressForm()
    return render(request, 'accounts/address_form.html', {'form': form})


@login_required
def address_update(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Endereço atualizado com sucesso!')
            return redirect('my_profile')
    else:
        form = AddressForm(instance=address)
    return render(request, 'accounts/address_form.html', {'form': form})


@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Endereço removido com sucesso!')
    return redirect('my_profile')
