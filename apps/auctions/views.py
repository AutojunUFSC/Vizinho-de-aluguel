from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.decorators import mei_required
from apps.services.models import ServiceCategory, ServiceRequest

from .forms import BidForm
from .models import Bid, MEICategorySubscription


# ─── Inscrições do MEI em categorias ─────────────────────────────────────────

@mei_required
def subscription_list(request):
    subscriptions = MEICategorySubscription.objects.filter(
        mei_profile=request.user.mei_profile,
    ).select_related('category')
    available = ServiceCategory.objects.filter(is_active=True).order_by('order')
    return render(request, 'auctions/subscriptions.html', {
        'subscriptions': subscriptions,
        'available': available,
    })


@mei_required
@require_POST
def subscription_create(request):
    """Inscreve o MEI em uma ou mais categorias (campo POST 'category_ids')."""
    category_ids = request.POST.getlist('category_ids')
    mei = request.user.mei_profile
    created = 0
    for cat_id in category_ids:
        _, was_created = MEICategorySubscription.objects.get_or_create(
            mei_profile=mei,
            category_id=cat_id,
            defaults={'is_active': True},
        )
        if was_created:
            created += 1
    if created:
        messages.success(request, f'{created} categoria(s) inscrita(s).')
    else:
        messages.info(request, 'Nenhuma nova inscrição criada.')
    return redirect('auctions:subscription_list')


@mei_required
@require_POST
def subscription_delete(request, category_id):
    sub = get_object_or_404(
        MEICategorySubscription,
        mei_profile=request.user.mei_profile,
        category_id=category_id,
    )
    sub.delete()
    messages.success(request, 'Inscrição removida.')
    return redirect('auctions:subscription_list')


# ─── Lances ─────────────────────────────────────────────────────────────────

@mei_required
def my_bids(request):
    bids = Bid.objects.filter(
        mei_profile=request.user.mei_profile,
    ).select_related('service_request', 'service_request__category').order_by('-created_at')
    return render(request, 'auctions/meus_lances.html', {'bids': bids})


@mei_required
@require_http_methods(['GET', 'POST'])
def bid_create(request, request_pk):
    """Envia um lance para uma ServiceRequest específica."""
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related('citizen__user', 'category'),
        pk=request_pk,
    )
    form = BidForm(
        request.POST or None,
        service_request=service_request,
        mei_profile=request.user.mei_profile,
    )
    if request.method == 'POST':
        if form.is_valid():
            bid = form.save()
            messages.success(request, f'Lance enviado: R$ {bid.amount}.')
            return redirect('auctions:my_bids')
        messages.error(request, 'Verifique os erros no formulário.')

    return render(request, 'auctions/fazer_proposta.html', {
        'form': form,
        'service_request': service_request,
        'pk': request_pk,
    })


@mei_required
@require_http_methods(['GET', 'POST'])
def bid_update(request, pk):
    bid = get_object_or_404(
        Bid,
        pk=pk,
        mei_profile=request.user.mei_profile,
        status=Bid.Status.ACTIVE,
    )
    form = BidForm(
        request.POST or None,
        instance=bid,
        service_request=bid.service_request,
        mei_profile=request.user.mei_profile,
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Lance atualizado.')
            return redirect('auctions:my_bids')
        messages.error(request, 'Verifique os erros no formulário.')

    return render(request, 'auctions/lance_form.html', {
        'form': form,
        'bid': bid,
    })


@mei_required
@require_POST
def bid_withdraw(request, pk):
    bid = get_object_or_404(Bid, pk=pk, mei_profile=request.user.mei_profile)
    if bid.status != Bid.Status.ACTIVE:
        messages.error(request, 'Só é possível retirar lances ativos.')
    else:
        bid.status = Bid.Status.WITHDRAWN
        bid.save(update_fields=['status'])
        messages.success(request, 'Lance retirado.')
    return redirect('auctions:my_bids')


@mei_required
@require_POST
def bid_delete(request, pk):
    bid = get_object_or_404(
        Bid,
        pk=pk,
        mei_profile=request.user.mei_profile,
        status=Bid.Status.ACTIVE,
    )
    bid.delete()
    messages.success(request, 'Lance excluído.')
    return redirect('auctions:my_bids')
