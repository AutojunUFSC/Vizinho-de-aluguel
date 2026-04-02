from django import forms
from django.utils import timezone
from .models import ServiceRequest, ServiceRequestMedia
from apps.accounts.models import Address


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ('title', 'description', 'category', 'address', 'urgency', 'budget_max', 'auction_end_at', 'desired_deadline')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'auction_end_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'desired_deadline': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['address'].queryset = Address.objects.filter(user=user)

    def clean_auction_end_at(self):
        value = self.cleaned_data.get('auction_end_at')
        if value and value <= timezone.now():
            raise forms.ValidationError('A data do leilão deve ser no futuro.')
        return value


class ServiceRequestMediaForm(forms.ModelForm):
    class Meta:
        model = ServiceRequestMedia
        fields = ('file', 'media_type')
