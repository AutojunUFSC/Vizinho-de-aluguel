from django import forms

from apps.accounts.models import Address

from .models import ServiceRequest, ServiceRequestMedia


MAX_MEDIA_PER_REQUEST = 5
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Aceita uma lista de arquivos vinda de <input type="file" multiple>."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)] if data else []


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = (
            'title', 'description', 'category', 'address',
            'urgency', 'budget_max',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields['address'].queryset = Address.objects.filter(user=self.user)
        # category e address são null=True no model, mas no fluxo de criação
        # o cidadão precisa obrigatoriamente informar ambos.
        self.fields['category'].required = True
        self.fields['address'].required = True
        self.fields['title'].required = True
        self.fields['description'].required = True

    def clean_title(self):
        value = (self.cleaned_data.get('title') or '').strip()
        if not value:
            raise forms.ValidationError('Informe um título para o serviço.')
        return value

    def clean_description(self):
        value = (self.cleaned_data.get('description') or '').strip()
        if not value:
            raise forms.ValidationError('Descreva o serviço.')
        if len(value) < 20:
            raise forms.ValidationError('A descrição deve ter pelo menos 20 caracteres.')
        return value

    def clean_budget_max(self):
        value = self.cleaned_data.get('budget_max')
        if value is not None and value <= 0:
            raise forms.ValidationError('O orçamento máximo deve ser maior que zero.')
        return value

    def clean_address(self):
        address = self.cleaned_data.get('address')
        if address and self.user is not None and address.user_id != self.user.id:
            raise forms.ValidationError('Este endereço não pertence ao usuário.')
        return address


class ServiceRequestMediaForm(forms.Form):
    """Upload de até 5 arquivos (imagem ou vídeo) para uma ServiceRequest."""

    files = MultipleFileField(
        required=False,
        label='Fotos ou vídeos (até 5)',
    )

    def __init__(self, *args, **kwargs):
        self.service_request = kwargs.pop('service_request', None)
        super().__init__(*args, **kwargs)

    def clean_files(self):
        files = self.cleaned_data.get('files') or []

        if self.service_request is not None:
            existing = ServiceRequestMedia.objects.filter(
                service_request=self.service_request
            ).count()
        else:
            existing = 0

        if existing + len(files) > MAX_MEDIA_PER_REQUEST:
            raise forms.ValidationError(
                f'Máximo de {MAX_MEDIA_PER_REQUEST} mídias por solicitação '
                f'(já há {existing} salvas).'
            )

        for f in files:
            if f.size > MAX_FILE_SIZE:
                raise forms.ValidationError(
                    f'"{f.name}" excede o tamanho máximo de 20 MB.'
                )
            content_type = getattr(f, 'content_type', '') or ''
            if content_type not in ALLOWED_IMAGE_TYPES and content_type not in ALLOWED_VIDEO_TYPES:
                raise forms.ValidationError(
                    f'"{f.name}" tem tipo não suportado ({content_type or "desconhecido"}).'
                )

        return files

    def save(self):
        if self.service_request is None:
            raise ValueError('service_request é obrigatório para salvar mídias.')

        created = []
        start_order = ServiceRequestMedia.objects.filter(
            service_request=self.service_request
        ).count()

        for index, f in enumerate(self.cleaned_data.get('files') or []):
            content_type = getattr(f, 'content_type', '') or ''
            media_type = (
                ServiceRequestMedia.MediaType.VIDEO
                if content_type in ALLOWED_VIDEO_TYPES
                else ServiceRequestMedia.MediaType.IMAGE
            )
            created.append(
                ServiceRequestMedia.objects.create(
                    service_request=self.service_request,
                    file=f,
                    media_type=media_type,
                    order=start_order + index,
                )
            )
        return created
