from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.decorators import citizen_required, mei_required
from apps.accounts.models import Address

from .forms import ServiceRequestForm, ServiceRequestMediaForm
from .models import ServiceCategory, ServiceRequest, ServiceRequestMedia


# ─── Catálogo público ────────────────────────────────────────────────────────

def category_list(request):
    categories = ServiceCategory.objects.filter(is_active=True).order_by('order')
    return render(request, 'services/categoria_lista.html', {'categories': categories})


def category_detail(request, slug):
    category = get_object_or_404(ServiceCategory, slug=slug, is_active=True)
    return render(request, 'services/categoria_detalhe.html', {'category': category})


# ─── Cidadão: criar e gerenciar solicitações ─────────────────────────────────

@citizen_required
def service_request_list(request):
    #expira solicitações pendentes há mais de de 7 dias
    ServiceRequest.objects.filter(
        citizen__user=request.user,
        status='OPEN',
        auction_end_at__lt=timezone.now(),
    ).update(status=ServiceRequest.Status.CANCELLED)

    base_qs = (
        ServiceRequest.objects
        .filter(citizen__user=request.user)
        .select_related('category', 'address')
        .annotate(bid_count=Count('bids', filter=Q(bids__status='ACTIVE')))
    )

    status_filter = request.GET.get('status') or ''
    category_filter = request.GET.get('category') or ''

    qs = base_qs.order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category__slug=category_filter)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Contagens por status (do total, ignorando filtros) — para os tabs/resumo
    counts = {status.value: 0 for status in ServiceRequest.Status}
    for row in base_qs.values('status').annotate(n=Count('id')):
        counts[row['status']] = row['n']
    counts['TODAS'] = base_qs.count()

    qs_extra_parts = []
    if status_filter:
        qs_extra_parts.append(f'status={status_filter}')
    if category_filter:
        qs_extra_parts.append(f'category={category_filter}')

    return render(request, 'services/minhas_solicitacoes.html', {
        'page_obj': page_obj,
        'requests': page_obj.object_list,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'counts': counts,
        'qs_extra': '&'.join(qs_extra_parts),
        'categories': ServiceCategory.objects.filter(is_active=True).order_by('order'),
    })


# Alias semântico usado em outras telas
my_requests = service_request_list


@citizen_required
@require_http_methods(['GET', 'POST'])
def service_request_create(request):
    """
    Aceita endereço de duas formas (UX atual do template):
      - address_id de um Address salvo do usuário, OU
      - campos inline: cep, street, neighborhood (number opcional)
    Cria Address inline quando necessário antes de instanciar o form.
    """
    post_data = request.POST.copy() if request.method == 'POST' else None

    inline_address = None
    if post_data is not None and not post_data.get('address'):
        cep = (post_data.get('cep') or '').strip()
        street = (post_data.get('street') or '').strip()
        neighborhood = (post_data.get('neighborhood') or '').strip()
        if cep and street and neighborhood:
            inline_address = Address.objects.create(
                user=request.user,
                label='Solicitação',
                cep=cep,
                street=street,
                number=(post_data.get('number') or 'S/N').strip() or 'S/N',
                neighborhood=neighborhood,
                city=(post_data.get('city') or 'Florianópolis').strip(),
                state=(post_data.get('state') or 'SC').strip().upper()[:2],
            )
            post_data['address'] = str(inline_address.pk)

    form = ServiceRequestForm(post_data, user=request.user)
    media_form = ServiceRequestMediaForm(post_data, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid() and media_form.is_valid():
            with transaction.atomic():
                service_request = form.save(commit=False)
                service_request.citizen = request.user.citizen_profile
                service_request.save()
                media_form.service_request = service_request
                media_form.save()
            messages.success(request, 'Solicitação publicada!')
            return redirect('services:service_request_detail', pk=service_request.pk)
        messages.error(request, 'Verifique os erros no formulário.')

    # Se criamos um Address inline mas o form falhou, removemos para não deixar lixo.
    if inline_address is not None and request.method == 'POST' and not form.is_valid():
        inline_address.delete()

    return render(request, 'services/nova_solicitacao.html', {
        'form': form,
        'media_form': media_form,
        'categories': ServiceCategory.objects.filter(is_active=True).order_by('order'),
        'addresses': Address.objects.filter(user=request.user),
    })


@login_required
def service_request_detail(request, pk):
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related('citizen__user', 'category', 'address'),
        pk=pk,
    )
    # Apenas o dono ou MEIs podem ver detalhes públicos
    if request.user.user_type == 'CIDADAO' and service_request.citizen.user != request.user:
        messages.error(request, 'Você não pode ver esta solicitação.')
        return redirect('home_usuario')

    bids = service_request.bids.filter(status='ACTIVE').select_related('mei_profile__user').order_by('amount')
    return render(request, 'services/propostas_solicitacao.html', {
        'service_request': service_request,
        'bids': bids,
        'pk': pk,
    })


@citizen_required
@require_http_methods(['GET', 'POST'])
def service_request_update(request, pk):
    service_request = get_object_or_404(
        ServiceRequest, pk=pk, citizen__user=request.user,
    )
    if service_request.status not in ('OPEN', 'IN_AUCTION'):
        messages.error(request, 'Solicitação não pode mais ser editada.')
        return redirect('services:service_request_detail', pk=pk)

    form = ServiceRequestForm(
        request.POST or None,
        instance=service_request,
        user=request.user,
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Solicitação atualizada.')
            return redirect('services:service_request_detail', pk=pk)
        messages.error(request, 'Verifique os erros no formulário.')
    return render(request, 'services/solicitacao_form.html', {'form': form})


@citizen_required
@require_http_methods(['GET', 'POST'])
def service_request_cancel(request, pk):
    service_request = get_object_or_404(
        ServiceRequest, pk=pk, citizen__user=request.user,
    )

    if service_request.status in ('COMPLETED', 'CANCELLED'):
        messages.error(request, 'Não é possível cancelar esta solicitação.')
        return redirect('services:my_requests')

    if request.method == 'POST':
        service_request.status = ServiceRequest.Status.CANCELLED
        service_request.save(update_fields=['status'])
        messages.success(request, 'Solicitação cancelada.')
        return redirect('services:my_requests')

    return render(request, 'services/service_request_confirm_delete.html', {
        'service_request': service_request,
    })


# ─── MEI: feed de solicitações abertas ───────────────────────────────────────

@mei_required
def request_feed(request):
    qs = ServiceRequest.objects.filter(
        status__in=('OPEN', 'IN_AUCTION'),
        auction_end_at__gt=timezone.now(),
    ).select_related('citizen__user', 'category', 'address').order_by('-created_at')

    category = request.GET.get('category')
    city = request.GET.get('city')
    urgency = request.GET.get('urgency')
    if category:
        qs = qs.filter(category__slug=category)
    if city:
        qs = qs.filter(address__city__icontains=city)
    if urgency:
        qs = qs.filter(urgency=urgency)

    return render(request, 'services/feed_mei.html', {
        'requests': qs,
        'category_filter': category,
        'city_filter': city,
        'urgency_filter': urgency,
        'categories': ServiceCategory.objects.filter(is_active=True).order_by('order'),
    })


# ─── Adjudicação (Award): cidadão escolhe vencedor ───────────────────────────

@citizen_required
@require_POST
@transaction.atomic
def award_bid(request, bid_pk):
    """
    Cidadão escolhe um lance vencedor:
      - valida que a solicitação está OPEN/IN_AUCTION
      - marca o lance vencedor como WINNER e os demais ACTIVE como REJECTED
      - muda status da solicitação para AWARDED
      - cria a ServiceOrder
    """
    from apps.auctions.models import Bid
    from apps.orders.models import ServiceOrder

    winning_bid = get_object_or_404(
        Bid.objects.select_related('service_request', 'mei_profile'),
        pk=bid_pk,
        status=Bid.Status.ACTIVE,
    )
    service_request = winning_bid.service_request

    if service_request.citizen.user != request.user:
        messages.error(request, 'Você não pode adjudicar esta solicitação.')
        return redirect('services:my_requests')

    if service_request.status not in (ServiceRequest.Status.OPEN, ServiceRequest.Status.IN_AUCTION):
        messages.error(request, 'Esta solicitação não pode ser adjudicada no estado atual.')
        return redirect('services:service_request_detail', pk=service_request.pk)

    # Rejeita os demais lances ativos
    Bid.objects.filter(
        service_request=service_request,
        status=Bid.Status.ACTIVE,
    ).exclude(pk=winning_bid.pk).update(status=Bid.Status.REJECTED)

    winning_bid.status = Bid.Status.WINNER
    winning_bid.save(update_fields=['status'])

    service_request.status = ServiceRequest.Status.AWARDED
    service_request.awarded_at = timezone.now()
    service_request.save(update_fields=['status', 'awarded_at'])

    order = ServiceOrder.objects.create(
        service_request=service_request,
        winning_bid=winning_bid,
        citizen=service_request.citizen,
        mei_profile=winning_bid.mei_profile,
        agreed_amount=winning_bid.amount,
        agreed_deadline=winning_bid.proposed_deadline,
    )
    messages.success(request, 'Proposta aceita! O profissional foi notificado.')
    return redirect('acompanhamento_pedido', pk=order.pk)


# ─── Mídia: listar/adicionar fotos a uma solicitação existente ───────────────

@citizen_required
@require_http_methods(['GET', 'POST'])
def request_media(request, request_pk):
    service_request = get_object_or_404(
        ServiceRequest, pk=request_pk, citizen__user=request.user,
    )
    media_form = ServiceRequestMediaForm(
        request.POST or None,
        request.FILES or None,
        service_request=service_request,
    )
    if request.method == 'POST' and media_form.is_valid():
        media_form.save()
        messages.success(request, 'Mídia(s) adicionada(s).')
        return redirect('services:request_media', request_pk=request_pk)

    media = ServiceRequestMedia.objects.filter(service_request=service_request).order_by('order')
    return render(request, 'services/midias.html', {
        'service_request': service_request,
        'media': media,
        'media_form': media_form,
    })
