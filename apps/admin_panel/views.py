from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q

from apps.accounts.decorators import admin_required
from apps.accounts.models import User, MEIProfile, CitizenProfile
from apps.services.models import ServiceRequest
from apps.orders.models import ServiceOrder


@admin_required
def dashboard(request):
    context = {
        'total_citizens': CitizenProfile.objects.count(),
        'total_meis': MEIProfile.objects.count(),
        'meis_pending': MEIProfile.objects.filter(verification_status='PENDING').count(),
        'total_requests': ServiceRequest.objects.count(),
        'open_requests': ServiceRequest.objects.filter(status=ServiceRequest.Status.OPEN).count(),
        'total_orders': ServiceOrder.objects.count(),
        'orders_in_progress': ServiceOrder.objects.filter(status=ServiceOrder.Status.IN_PROGRESS).count(),
        'orders_completed': ServiceOrder.objects.filter(status=ServiceOrder.Status.COMPLETED).count(),
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def mei_verification_list(request):
    status_filter = request.GET.get('status', 'PENDING')
    meis = MEIProfile.objects.filter(verification_status=status_filter).select_related('user')
    context = {
        'meis': meis,
        'current_status': status_filter,
    }
    return render(request, 'admin_panel/mei_verification_list.html', context)


@admin_required
def mei_verification_detail(request, pk):
    mei = get_object_or_404(MEIProfile, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            mei.verification_status = MEIProfile.VerificationStatus.VERIFIED
            mei.save(update_fields=['verification_status'])
            messages.success(request, f'MEI {mei.nome_fantasia} aprovado.')
        elif action == 'reject':
            mei.verification_status = MEIProfile.VerificationStatus.REJECTED
            mei.save(update_fields=['verification_status'])
            messages.warning(request, f'MEI {mei.nome_fantasia} rejeitado.')
        return redirect('admin_panel:mei_verification_list')

    context = {'mei': mei}
    return render(request, 'admin_panel/mei_verification_detail.html', context)


@admin_required
def user_list(request):
    user_type = request.GET.get('type', '')
    users = User.objects.all().order_by('-created_at')
    if user_type:
        users = users.filter(user_type=user_type)
    context = {
        'users': users,
        'current_type': user_type,
    }
    return render(request, 'admin_panel/user_list.html', context)


@admin_required
def order_list(request):
    status_filter = request.GET.get('status', '')
    orders = ServiceOrder.objects.all().select_related(
        'citizen__user', 'mei_profile__user', 'service_request'
    ).order_by('-created_at')
    if status_filter:
        orders = orders.filter(status=status_filter)
    context = {
        'orders': orders,
        'current_status': status_filter,
    }
    return render(request, 'admin_panel/order_list.html', context)
