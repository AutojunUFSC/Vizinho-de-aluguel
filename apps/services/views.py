from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import ServiceCategory, ServiceRequest, ServiceRequestMedia
from .forms import ServiceRequestForm, ServiceRequestMediaForm
from apps.accounts.decorators import citizen_required, mei_required
from apps.accounts.models import Address
from apps.auctions.models import Bid
from apps.orders.models import ServiceOrder


# --- Categorias ---

def category_list(request):
    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'services/category_list.html', {'categories': categories})


# --- Solicitações (Cidadão) ---

@citizen_required
def service_request_create(request):
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, user=request.user)
        files = request.FILES.getlist('media_files')
        if form.is_valid():
            sr = form.save(commit=False)
            sr.citizen = request.user.citizen_profile
            sr.save()
            for f in files:
                ServiceRequestMedia.objects.create(
                    service_request=sr,
                    file=f,
                    media_type='IMAGE',
                )
            messages.success(request, 'Solicitação criada com sucesso!')
            return redirect('service_request_detail', pk=sr.pk)
    else:
        form = ServiceRequestForm(user=request.user)
    return render(request, 'services/request_form.html', {'form': form})


@citizen_required
def service_request_detail(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk, citizen__user=request.user)
    bids = sr.bids.filter(status=Bid.Status.ACTIVE).select_related('mei_profile__user')
    context = {
        'service_request': sr,
        'bids': bids,
        'media': sr.media.all(),
    }
    return render(request, 'services/request_detail.html', context)


@citizen_required
def service_request_update(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk, citizen__user=request.user, status=ServiceRequest.Status.OPEN)
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, instance=sr, user=request.user)
        files = request.FILES.getlist('media_files')
        if form.is_valid():
            form.save()
            for f in files:
                ServiceRequestMedia.objects.create(
                    service_request=sr,
                    file=f,
                    media_type='IMAGE',
                )
            messages.success(request, 'Solicitação atualizada com sucesso!')
            return redirect('service_request_detail', pk=sr.pk)
    else:
        form = ServiceRequestForm(instance=sr, user=request.user)
    return render(request, 'services/request_form.html', {'form': form, 'service_request': sr})


@citizen_required
def service_request_cancel(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk, citizen__user=request.user)
    if request.method == 'POST':
        if sr.status in [ServiceRequest.Status.COMPLETED, ServiceRequest.Status.CANCELLED]:
            messages.error(request, 'Não é possível cancelar esta solicitação.')
        else:
            sr.status = ServiceRequest.Status.CANCELLED
            sr.save()
            messages.success(request, 'Solicitação cancelada.')
    return redirect('dashboard_citizen')


@citizen_required
def award_bid(request, pk, bid_id):
    sr = get_object_or_404(ServiceRequest, pk=pk, citizen__user=request.user)
    bid = get_object_or_404(Bid, pk=bid_id, service_request=sr, status=Bid.Status.ACTIVE)

    if request.method == 'POST':
        with transaction.atomic():
            bid.status = Bid.Status.WINNER
            bid.save()

            sr.bids.filter(status=Bid.Status.ACTIVE).exclude(pk=bid.pk).update(status=Bid.Status.REJECTED)

            sr.status = ServiceRequest.Status.AWARDED
            sr.awarded_at = timezone.now()
            sr.save()

            order = ServiceOrder.objects.create(
                service_request=sr,
                winning_bid=bid,
                citizen=sr.citizen,
                mei_profile=bid.mei_profile,
                agreed_amount=bid.amount,
                agreed_deadline=bid.proposed_deadline,
            )
            messages.success(request, 'Lance aceito! Ordem de serviço criada.')
            return redirect('order_detail', pk=order.pk)

    return redirect('service_request_detail', pk=sr.pk)


@citizen_required
def media_delete(request, pk, media_id):
    sr = get_object_or_404(ServiceRequest, pk=pk, citizen__user=request.user, status=ServiceRequest.Status.OPEN)
    media = get_object_or_404(ServiceRequestMedia, pk=media_id, service_request=sr)
    if request.method == 'POST':
        media.file.delete()
        media.delete()
        messages.success(request, 'Mídia removida.')
    return redirect('service_request_update', pk=sr.pk)


# --- Feed (MEI) ---

@mei_required
def feed(request):
    queryset = ServiceRequest.objects.filter(
        status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.IN_AUCTION]
    ).select_related('category', 'address', 'citizen__user')

    category_slug = request.GET.get('categoria')
    urgency = request.GET.get('urgencia')

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    if urgency:
        queryset = queryset.filter(urgency=urgency)

    categories = ServiceCategory.objects.filter(is_active=True)

    context = {
        'service_requests': queryset,
        'categories': categories,
        'selected_category': category_slug,
        'selected_urgency': urgency,
    }
    return render(request, 'services/feed.html', context)


@mei_required
def feed_detail(request, pk):
    sr = get_object_or_404(ServiceRequest, pk=pk, status__in=[ServiceRequest.Status.OPEN, ServiceRequest.Status.IN_AUCTION])
    existing_bid = Bid.objects.filter(
        service_request=sr,
        mei_profile=request.user.mei_profile,
        status=Bid.Status.ACTIVE,
    ).first()

    context = {
        'service_request': sr,
        'media': sr.media.all(),
        'existing_bid': existing_bid,
    }
    return render(request, 'services/feed_detail.html', context)
