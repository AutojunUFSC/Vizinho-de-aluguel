from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import ServiceOrder
from apps.accounts.decorators import mei_required, citizen_required


@login_required
def order_detail(request, pk):
    order = get_object_or_404(ServiceOrder, pk=pk)
    user = request.user

    # Verificar que o user é participante da ordem
    is_citizen = hasattr(user, 'citizen_profile') and order.citizen == user.citizen_profile
    is_mei = hasattr(user, 'mei_profile') and order.mei_profile == user.mei_profile

    if not is_citizen and not is_mei and not user.is_staff:
        messages.error(request, 'Você não tem permissão para ver esta ordem.')
        return redirect('/')

    context = {
        'order': order,
        'is_citizen': is_citizen,
        'is_mei': is_mei,
    }
    return render(request, 'orders/order_detail.html', context)


@mei_required
def order_start(request, pk):
    order = get_object_or_404(ServiceOrder, pk=pk, mei_profile=request.user.mei_profile)
    if request.method == 'POST':
        if order.status != ServiceOrder.Status.PENDING_START:
            messages.error(request, 'Esta ordem não pode ser iniciada.')
        else:
            order.status = ServiceOrder.Status.IN_PROGRESS
            order.started_at = timezone.now()
            order.save()
            messages.success(request, 'Serviço iniciado!')
    return redirect('order_detail', pk=order.pk)


@mei_required
def order_complete(request, pk):
    order = get_object_or_404(ServiceOrder, pk=pk, mei_profile=request.user.mei_profile)
    if request.method == 'POST':
        if order.status != ServiceOrder.Status.IN_PROGRESS:
            messages.error(request, 'Esta ordem não pode ser concluída.')
        else:
            order.status = ServiceOrder.Status.COMPLETED
            order.completed_at = timezone.now()
            order.save()

            # Atualizar status do ServiceRequest
            order.service_request.status = 'COMPLETED'
            order.service_request.save()

            messages.success(request, 'Serviço marcado como concluído!')
    return redirect('order_detail', pk=order.pk)


@citizen_required
def order_confirm(request, pk):
    order = get_object_or_404(ServiceOrder, pk=pk, citizen=request.user.citizen_profile)
    if request.method == 'POST':
        if order.status != ServiceOrder.Status.COMPLETED or order.citizen_confirmed_at:
            messages.error(request, 'Não é possível confirmar esta ordem.')
        else:
            order.citizen_confirmed_at = timezone.now()
            order.save()
            messages.success(request, 'Conclusão confirmada! Agora você pode avaliar o profissional.')
    return redirect('order_detail', pk=order.pk)


@login_required
def order_cancel(request, pk):
    order = get_object_or_404(ServiceOrder, pk=pk)
    user = request.user

    if request.method == 'POST':
        is_citizen = hasattr(user, 'citizen_profile') and order.citizen == user.citizen_profile
        is_mei = hasattr(user, 'mei_profile') and order.mei_profile == user.mei_profile

        if order.status == ServiceOrder.Status.PENDING_START and (is_citizen or is_mei):
            order.status = ServiceOrder.Status.CANCELLED
            order.save()
            messages.success(request, 'Ordem cancelada.')
        elif user.is_staff:
            order.status = ServiceOrder.Status.CANCELLED
            order.save()
            messages.success(request, 'Ordem cancelada pelo admin.')
        else:
            messages.error(request, 'Não é possível cancelar esta ordem.')

    return redirect('order_detail', pk=order.pk)
