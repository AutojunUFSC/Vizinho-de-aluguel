from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.orders.models import ServiceOrder

from .forms import ReviewForm
from .models import Review


def _resolve_review_type(order: ServiceOrder, user) -> str:
    """Determina se o reviewer é cidadão (CITIZEN_TO_MEI) ou MEI (MEI_TO_CITIZEN)."""
    if order.citizen.user_id == user.id:
        return Review.ReviewType.CITIZEN_TO_MEI
    if order.mei_profile.user_id == user.id:
        return Review.ReviewType.MEI_TO_CITIZEN
    return ''


@login_required
@require_http_methods(['GET', 'POST'])
def review_create(request, order_pk):
    """
    Cria uma Review para uma ServiceOrder.

    Regras (replicadas das exigências do Backlog):
      - Order precisa estar COMPLETED.
      - Reviewer precisa ser o cidadão OU o MEI da order.
      - Reviewer não pode ter avaliado a mesma order duas vezes.
    """
    order = get_object_or_404(
        ServiceOrder.objects.select_related('citizen__user', 'mei_profile__user'),
        pk=order_pk,
    )

    review_type = _resolve_review_type(order, request.user)
    if not review_type:
        messages.error(request, 'Você não participou deste serviço.')
        return redirect('home')

    if order.status != ServiceOrder.Status.COMPLETED:
        messages.error(request, 'Só é possível avaliar serviços concluídos.')
        return redirect('acompanhamento_pedido', pk=order.pk)

    if Review.objects.filter(service_order=order, reviewer=request.user).exists():
        messages.info(request, 'Você já avaliou este serviço.')
        return redirect('acompanhamento_pedido', pk=order.pk)

    form = ReviewForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.service_order = order
        review.reviewer = request.user
        review.review_type = review_type
        review.save()
        # Signal apps.reviews.signals.update_rating_avg recalcula rating_avg.
        messages.success(request, 'Avaliação enviada! Obrigado pelo feedback.')
        return redirect('acompanhamento_pedido', pk=order.pk)

    return render(request, 'reviews/criar.html', {
        'form': form,
        'order': order,
        'review_type': review_type,
    })


@login_required
def my_reviews(request):
    """Lista as avaliações dadas e recebidas pelo usuário autenticado."""
    given = Review.objects.filter(
        reviewer=request.user,
    ).select_related('service_order').order_by('-created_at')

    received = Review.objects.filter(
        service_order__citizen__user=request.user,
        review_type=Review.ReviewType.MEI_TO_CITIZEN,
    ).select_related('service_order', 'reviewer') | Review.objects.filter(
        service_order__mei_profile__user=request.user,
        review_type=Review.ReviewType.CITIZEN_TO_MEI,
    ).select_related('service_order', 'reviewer')
    received = received.order_by('-created_at')

    return render(request, 'reviews/lista.html', {
        'reviews_given': given,
        'reviews_received': received,
    })
