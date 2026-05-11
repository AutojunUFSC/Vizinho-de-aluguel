# ui/views.py

from django.db.models import Count, Q
from django.shortcuts import render, redirect

from apps.accounts.decorators import citizen_required, mei_required
from apps.orders.models import ServiceOrder
from apps.reviews.models import Review
from apps.services.models import ServiceCategory, ServiceRequest


def home(request):
    return render(request, "ui/home.html")


@citizen_required
def home_usuario(request):
    return redirect('accounts:profile')


@mei_required
def home_profissional(request):
    return redirect('accounts:profile')


def servicos(request):
    return render(request, "ui/servicos.html")


def institucional(request):
    return render(request, "ui/institucional.html")


def contato(request):
    return render(request, "ui/contato.html")


def sitemap(request):
    return render(request, "ui/sitemap.html")
