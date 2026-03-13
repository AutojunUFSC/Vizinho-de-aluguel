from django.core.management.base import BaseCommand
from apps.services.models import ServiceCategory


class Command(BaseCommand):
    help = 'Popula as categorias iniciais de serviço'

    def handle(self, *args, **kwargs):
        categories = [
            {'name': 'Hidráulica', 'slug': 'hidraulica', 'icon': '🔧', 'order': 1},
            {'name': 'Elétrica', 'slug': 'eletrica', 'icon': '⚡', 'order': 2},
            {'name': 'Pintura', 'slug': 'pintura', 'icon': '🖌️', 'order': 3},
            {'name': 'Alvenaria', 'slug': 'alvenaria', 'icon': '🧱', 'order': 4},
            {'name': 'Marcenaria', 'slug': 'marcenaria', 'icon': '🪵', 'order': 5},
            {'name': 'Limpeza', 'slug': 'limpeza', 'icon': '🧹', 'order': 6},
            {'name': 'Jardinagem', 'slug': 'jardinagem', 'icon': '🌿', 'order': 7},
            {'name': 'Ar-Condicionado', 'slug': 'ar-condicionado', 'icon': '❄️', 'order': 8},
            {'name': 'Serralheria', 'slug': 'serralheria', 'icon': '🔩', 'order': 9},
            {'name': 'Outros', 'slug': 'outros', 'icon': '🛠️', 'order': 10},
        ]

        for cat in categories:
            obj, created = ServiceCategory.objects.get_or_create(
                slug=cat['slug'],
                defaults={
                    'name': cat['name'],
                    'icon': cat['icon'],
                    'order': cat['order'],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Criada: {cat["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Já existe: {cat["name"]}'))

        self.stdout.write(self.style.SUCCESS('🎉 Categorias populadas com sucesso!'))