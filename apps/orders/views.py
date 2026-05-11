from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import OrderCancelForm
from .models import ServiceOrder


def _get_order_for_user(pk, user):
    """Busca a ordem garantindo que o usuário é cidadão ou MEI dela."""
    order = get_object_or_404(
        ServiceOrder.objects.select_related(
            'service_request',
            'winning_bid',
            'citizen__user',
            'mei_profile__user',
        ),
        pk=pk,
    )
    if order.citizen.user_id != user.id and order.mei_profile.user_id != user.id:
        return None
    return order


@login_required
def order_list(request):
    """Lista as ordens do usuário (cidadão ou MEI)."""
    user = request.user
    qs = ServiceOrder.objects.select_related(
        'service_request', 'citizen__user', 'mei_profile__user',
    ).order_by('-created_at')
    if user.user_type == 'CIDADAO':
        qs = qs.filter(citizen__user=user)
    elif user.user_type == 'MEI':
        qs = qs.filter(mei_profile__user=user)
    else:
        qs = qs.none()
    return render(request, 'orders/lista.html', {'orders': qs})


# Alias
my_orders = order_list


@login_required
def order_detail(request, pk):
    order = _get_order_for_user(pk, request.user)
    if order is None:
        messages.error(request, 'Você não tem acesso a este pedido.')
        return redirect('home')

    # Quem é a contraparte (do ponto de vista do request.user)
    is_citizen = order.citizen.user_id == request.user.id
    is_mei = order.mei_profile.user_id == request.user.id
    counterpart_name = (
        order.mei_profile.user.full_name if is_citizen
        else order.citizen.user.full_name if is_mei
        else ''
    )

    # Já avaliou esta order?
    from apps.reviews.models import Review
    user_already_reviewed = Review.objects.filter(
        service_order=order, reviewer=request.user,
    ).exists()

    can_review = (
        order.status == order.Status.COMPLETED
        and (is_citizen or is_mei)
        and not user_already_reviewed
    )

    return render(request, 'orders/acompanhamento_pedido.html', {
        'order': order,
        'pk': order.pk,
        'is_citizen': is_citizen,
        'is_mei': is_mei,
        'counterpart_name': counterpart_name,
        'can_review': can_review,
        'user_already_reviewed': user_already_reviewed,
    })


@login_required
@require_POST
def order_start(request, pk):
    """MEI inicia o trabalho: PENDING_START → IN_PROGRESS."""
    order = _get_order_for_user(pk, request.user)
    if order is None:
        messages.error(request, 'Você não tem acesso a este pedido.')
        return redirect('home')

    if order.mei_profile.user_id != request.user.id:
        messages.error(request, 'Apenas o MEI responsável pode iniciar o serviço.')
        return redirect('acompanhamento_pedido', pk=pk)

    if order.status != ServiceOrder.Status.PENDING_START:
        messages.error(request, 'Status inválido para iniciar o serviço.')
        return redirect('acompanhamento_pedido', pk=pk)

    order.status = ServiceOrder.Status.IN_PROGRESS
    order.started_at = timezone.now()
    order.save(update_fields=['status', 'started_at'])
    messages.success(request, 'Serviço iniciado!')
    return redirect('acompanhamento_pedido', pk=pk)


@login_required
@require_POST
def order_complete(request, pk):
    """MEI marca como concluído: IN_PROGRESS → COMPLETED."""
    order = _get_order_for_user(pk, request.user)
    if order is None:
        messages.error(request, 'Você não tem acesso a este pedido.')
        return redirect('home')

    if order.mei_profile.user_id != request.user.id:
        messages.error(request, 'Apenas o MEI responsável pode concluir o serviço.')
        return redirect('acompanhamento_pedido', pk=pk)

    if order.status != ServiceOrder.Status.IN_PROGRESS:
        messages.error(request, 'Status inválido para concluir o serviço.')
        return redirect('acompanhamento_pedido', pk=pk)

    order.status = ServiceOrder.Status.COMPLETED
    order.completed_at = timezone.now()
    order.save(update_fields=['status', 'completed_at'])
    messages.success(request, 'Serviço concluído! Aguardando confirmação do cidadão.')
    return redirect('acompanhamento_pedido', pk=pk)


@login_required
@require_POST
def order_confirm(request, pk):
    """Cidadão confirma recebimento (status segue COMPLETED, marca timestamp)."""
    order = _get_order_for_user(pk, request.user)
    if order is None:
        messages.error(request, 'Você não tem acesso a este pedido.')
        return redirect('home')

    if order.citizen.user_id != request.user.id:
        messages.error(request, 'Apenas o cidadão pode confirmar o serviço.')
        return redirect('acompanhamento_pedido', pk=pk)

    if order.status != ServiceOrder.Status.COMPLETED:
        messages.error(request, 'Só é possível confirmar serviços concluídos.')
        return redirect('acompanhamento_pedido', pk=pk)

    order.citizen_confirmed_at = timezone.now()
    order.save(update_fields=['citizen_confirmed_at'])
    messages.success(request, 'Recebimento confirmado. Você pode avaliar o profissional!')
    return redirect('acompanhamento_pedido', pk=pk)


@login_required
@require_POST
def order_cancel(request, pk):
    """Cancela a ordem (cidadão ou MEI), exceto se já COMPLETED/CANCELLED."""
    order = _get_order_for_user(pk, request.user)
    if order is None:
        messages.error(request, 'Você não tem acesso a este pedido.')
        return redirect('home')

    if order.status in (ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED):
        messages.error(request, 'Não é possível cancelar este pedido.')
        return redirect('acompanhamento_pedido', pk=pk)

    form = OrderCancelForm(request.POST)
    motivo = form.cleaned_data.get('motivo') if form.is_valid() else ''

    order.status = ServiceOrder.Status.CANCELLED
    order.save(update_fields=['status'])
    if motivo:
        messages.info(request, f'Pedido cancelado. Motivo: {motivo}')
    else:
        messages.info(request, 'Pedido cancelado.')
    return redirect('acompanhamento_pedido', pk=pk)
