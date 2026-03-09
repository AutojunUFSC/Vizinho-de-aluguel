from django.db import models
from django.conf import settings
from usuarios.models import PerfilProfissional


class CategoriaServico(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    icone = models.CharField(max_length=50, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoria de Serviço'
        verbose_name_plural = 'Categorias de Serviço'

    def __str__(self):
        return self.nome


class AnuncioServico(models.Model):
    STATUS_CHOICES = [
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    profissional = models.ForeignKey(PerfilProfissional, on_delete=models.CASCADE, related_name='anuncios')
    categoria = models.ForeignKey(CategoriaServico, on_delete=models.SET_NULL, null=True)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    disponivel = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Anúncio de Serviço'
        verbose_name_plural = 'Anúncios de Serviço'

    def __str__(self):
        return self.titulo


class Contrato(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceito', 'Aceito'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contratos_cliente')
    anuncio = models.ForeignKey(AnuncioServico, on_delete=models.CASCADE, related_name='contratos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    valor_acordado = models.DecimalField(max_digits=8, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'

    def __str__(self):
        return f"Contrato #{self.id} - {self.cliente} x {self.anuncio}"


class Avaliacao(models.Model):
    contrato = models.OneToOneField(Contrato, on_delete=models.CASCADE, related_name='avaliacao')
    avaliador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avaliacoes_feitas')
    nota = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comentario = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'

    def __str__(self):
        return f"Avaliação {self.nota}★ - {self.avaliador}"