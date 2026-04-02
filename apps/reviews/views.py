from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Review
from .forms import ReviewForm
from apps.orders.models import ServiceOrder


@login_required
def review_create(request, order_pk):
    order = get_object_or_404(ServiceOrder, pk=order_pk)
    user = request.user

    # Determinar tipo de avaliação
    is_citizen = hasattr(user, 'citizen_profile') and order.citizen == user.citizen_profile
    is_mei = hasattr(user, 'mei_profile') and order.mei_profile == user.mei_profile

    if not is_citizen and not is_mei:
        messages.error(request, 'Você não tem permissão para avaliar esta ordem.')
        return redirect('/')

    if order.status != ServiceOrder.Status.COMPLETED:
        messages.error(request, 'Só é possível avaliar ordens concluídas.')
        return redirect('order_detail', pk=order.pk)

    # Cidadão só pode avaliar após confirmar conclusão
    if is_citizen and not order.citizen_confirmed_at:
        messages.error(request, 'Confirme a conclusão do serviço antes de avaliar.')
        return redirect('order_detail', pk=order.pk)

    review_type = Review.ReviewType.CITIZEN_TO_MEI if is_citizen else Review.ReviewType.MEI_TO_CITIZEN

    # Verificar se já avaliou
    if Review.objects.filter(service_order=order, reviewer=user).exists():
        messages.info(request, 'Você já avaliou esta ordem.')
        return redirect('order_detail', pk=order.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.service_order = order
            review.reviewer = user
            review.review_type = review_type
            review.save()
            messages.success(request, 'Avaliação enviada com sucesso!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = ReviewForm()

    context = {
        'form': form,
        'order': order,
        'review_type': review_type,
    }
    return render(request, 'reviews/review_form.html', context)


@login_required
def my_reviews(request):
    reviews_given = Review.objects.filter(
        reviewer=request.user
    ).select_related('service_order').order_by('-created_at')

    reviews_received = Review.objects.filter(
        service_order__in=ServiceOrder.objects.filter(
            models.Q(citizen__user=request.user) | models.Q(mei_profile__user=request.user)
        )
    ).exclude(reviewer=request.user).select_related('service_order').order_by('-created_at')

    context = {
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
    }
    return render(request, 'reviews/my_reviews.html', context)
