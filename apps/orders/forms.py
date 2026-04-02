from django import forms


class OrderCancelForm(forms.Form):
    motivo = forms.CharField(
        label='Motivo do cancelamento',
        widget=forms.Textarea(attrs={'rows': 3}),
    )
