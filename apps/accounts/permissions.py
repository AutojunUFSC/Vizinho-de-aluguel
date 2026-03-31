from rest_framework.permissions import BasePermission


class IsCitizen(BasePermission):
    """Permite acesso apenas a usuários do tipo Cidadão."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == 'CIDADAO'
        )


class IsMEI(BasePermission):
    """Permite acesso apenas a usuários do tipo MEI."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == 'MEI'
        )


class IsAdmin(BasePermission):
    """Permite acesso apenas a usuários do tipo Admin."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == 'ADMIN'
        )


class IsOwner(BasePermission):
    """Permite acesso apenas ao dono do objeto."""

    def has_object_permission(self, request, view, obj):
        # Verifica se o objeto tem um campo 'user' diretamente
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Verifica se o objeto é o próprio usuário
        if hasattr(obj, 'citizen'):
            return obj.citizen.user == request.user

        return False