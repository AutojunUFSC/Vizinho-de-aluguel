from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import MEICategorySubscription, Bid
from .forms import BidForm
from apps.accounts.decorators import mei_required
from apps.services.models import ServiceCategory, ServiceRequest


# --- Inscrição em Categorias ---

@mei_required
def mei_categories(request):
    mei = request.user.mei_profile
    all_categories = ServiceCategory.objects.filter(is_active=True)
    subscribed_ids = set(
        mei.category_subscriptions.filter(is_active=True).values_list('category_id', flat=True)
    )

    if request.method == 'POST':
        selected_ids = set(request.POST.getlist('categories'))
        # Criar novas inscrições
        for cat_id in selected_ids - subscribed_ids:
            MEICategorySubscription.objects.get_or_create(
                mei_profile=mei,
                category_id=cat_id,
                defaults={'is_active': True},
            )
        # Desativar inscrições desmarcadas
        MEICategorySubscription.objects.filter(
            mei_profile=mei,
        ).exclude(
            category_id__in=selected_ids,
        ).update(is_active=False)
        # Reativar inscrições marcadas
        MEICategorySubscription.objects.filter(
            mei_profile=mei,
            category_id__in=selected_ids,
            is_active=False,
        ).update(is_active=True)

        messages.success(request, 'Categorias atualizadas com sucesso!')
        return redirect('my_profile')

    context = {
        'categories': all_categories,
        'subscribed_ids': subscribed_ids,
    }
    return render(request, 'auctions/mei_categories.html', context)


# --- Lances ---

@mei_required
def bid_create(request, request_id):
    sr = get_object_or_404(ServiceRequest, pk=request_id)
    mei = request.user.mei_profile

    if request.method == 'POST':
        form = BidForm(request.POST)

        # Validações de negócio
        errors = []
        if mei.verification_status != 'VERIFIED':
            errors.append('Seu perfil MEI precisa estar verificado para enviar lances.')
        if not mei.category_subscriptions.filter(category=sr.category, is_active=True).exists():
            errors.append('Você não está inscrito na categoria desta solicitação.')
        if sr.status not in [ServiceRequest.Status.OPEN, ServiceRequest.Status.IN_AUCTION]:
            errors.append('Esta solicitação não está aceitando lances.')
        if sr.auction_end_at and sr.auction_end_at <= timezone.now():
            errors.append('O prazo para lances já expirou.')
        if Bid.objects.filter(service_request=sr, mei_profile=mei, status=Bid.Status.ACTIVE).exists():
            errors.append('Você já possui um lance ativo nesta solicitação.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('feed_detail', pk=sr.pk)

        if form.is_valid():
            if sr.budget_max and form.cleaned_data['amount'] > sr.budget_max:
                messages.error(request, 'Seu lance excede o orçamento máximo do cliente.')
                return redirect('feed_detail', pk=sr.pk)

            bid = form.save(commit=False)
            bid.service_request = sr
            bid.mei_profile = mei
            bid.save()

            # Primeiro bid muda status para IN_AUCTION
            if sr.status == ServiceRequest.Status.OPEN:
                sr.status = ServiceRequest.Status.IN_AUCTION
                sr.save()

            messages.success(request, 'Lance enviado com sucesso!')
            return redirect('feed_detail', pk=sr.pk)
    else:
        form = BidForm()

    return redirect('feed_detail', pk=sr.pk)


@mei_required
def my_bids(request):
    bids = Bid.objects.filter(
        mei_profile=request.user.mei_profile
    ).select_related('service_request__category').order_by('-created_at')
    return render(request, 'auctions/my_bids.html', {'bids': bids})


@mei_required
def bid_update(request, bid_id):
    bid = get_object_or_404(
        Bid, pk=bid_id, mei_profile=request.user.mei_profile, status=Bid.Status.ACTIVE
    )
    if request.method == 'POST':
        form = BidForm(request.POST, instance=bid)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lance atualizado com sucesso!')
            return redirect('my_bids')
    else:
        form = BidForm(instance=bid)
    return render(request, 'auctions/bid_form.html', {'form': form, 'bid': bid})


@mei_required
def bid_withdraw(request, bid_id):
    bid = get_object_or_404(
        Bid, pk=bid_id, mei_profile=request.user.mei_profile, status=Bid.Status.ACTIVE
    )
    if request.method == 'POST':
        bid.status = Bid.Status.WITHDRAWN
        bid.save()
        messages.success(request, 'Lance retirado com sucesso.')
    return redirect('my_bids')
