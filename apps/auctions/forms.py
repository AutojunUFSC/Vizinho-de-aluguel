from django import forms
from .models import Bid


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ('amount', 'estimated_hours', 'proposed_deadline', 'notes')
        widgets = {
            'proposed_deadline': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
