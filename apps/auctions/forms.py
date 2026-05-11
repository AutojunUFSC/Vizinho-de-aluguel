from django import forms
from django.utils import timezone

from apps.accounts.models import MEIProfile

from .models import Bid


class BidForm(forms.ModelForm):
    """
    Formulário de envio/edição de lance.

    Espera receber:
      - service_request: instância de ServiceRequest sobre a qual o lance é feito.
      - mei_profile: MEIProfile do usuário autenticado.

    Replica as regras de BidSerializer.validate.
    """

    class Meta:
        model = Bid
        fields = ('amount', 'estimated_hours', 'proposed_deadline', 'notes')
        widgets = {
            'proposed_deadline': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.service_request = kwargs.pop('service_request', None)
        self.mei_profile = kwargs.pop('mei_profile', None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('O valor do lance deve ser maior que zero.')
        if (
            amount is not None
            and self.service_request is not None
            and self.service_request.budget_max
            and amount > self.service_request.budget_max
        ):
            raise forms.ValidationError(
                'O valor do lance não pode exceder o orçamento máximo da solicitação.'
            )
        return amount

    def clean_estimated_hours(self):
        hours = self.cleaned_data.get('estimated_hours')
        if hours is not None and hours <= 0:
            raise forms.ValidationError('As horas estimadas devem ser maiores que zero.')
        return hours

    def clean_proposed_deadline(self):
        deadline = self.cleaned_data.get('proposed_deadline')
        if deadline and deadline < timezone.localdate():
            raise forms.ValidationError('O prazo proposto não pode estar no passado.')
        return deadline

    def clean(self):
        cleaned = super().clean()

        if self.mei_profile is None:
            raise forms.ValidationError(
                'Não foi possível identificar o perfil MEI do usuário.'
            )

        if self.mei_profile.verification_status != MEIProfile.VerificationStatus.VERIFIED:
            raise forms.ValidationError(
                'Apenas MEIs verificados podem enviar lances.'
            )

        if self.service_request is None:
            raise forms.ValidationError(
                'Solicitação de serviço não informada para o lance.'
            )

        if self.service_request.status not in (
            'OPEN',
            'IN_AUCTION',
        ):
            raise forms.ValidationError(
                'Esta solicitação não está mais aceitando lances.'
            )

        if not self.mei_profile.category_subscriptions.filter(
            category=self.service_request.category,
            is_active=True,
        ).exists():
            raise forms.ValidationError(
                'MEI não está inscrito na categoria desta solicitação.'
            )

        duplicate_qs = Bid.objects.filter(
            service_request=self.service_request,
            mei_profile=self.mei_profile,
            status=Bid.Status.ACTIVE,
        )
        if self.instance and self.instance.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
        if duplicate_qs.exists():
            raise forms.ValidationError(
                'Você já possui um lance ativo nesta solicitação.'
            )

        return cleaned

    def save(self, commit=True):
        bid = super().save(commit=False)
        if self.service_request is not None:
            bid.service_request = self.service_request
        if self.mei_profile is not None:
            bid.mei_profile = self.mei_profile
        if commit:
            bid.save()
        return bid
