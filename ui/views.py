# ui/views.py

from django.shortcuts import render


def home(request):
    return render(request, "ui/home.html")


def cadastro(request):
    return render(request, "ui/cadastro.html")


def home_usuario(request):
    return render(request, "ui/home_usuario.html")


def home_profissional(request):
    # Autenticação feita via JWT no JS (mesmo padrão do home_usuario)
    # O template chama requireAuth() que redireciona se não houver token
    return render(request, "ui/home_profissional.html")


def nova_solicitacao(request):
    return render(request, "ui/nova_solicitacao.html")


def minhas_solicitacoes(request):
    return render(request, "ui/minhas_solicitacoes.html")


def servicos(request):
    return render(request, "ui/servicos.html")


def institucional(request):
    return render(request, "ui/institucional.html")


def contato(request):
    return render(request, "ui/contato.html")


def propostas_solicitacao(request, pk):
    return render(request, "ui/propostas_solicitacao.html", {"pk": pk})


def fazer_proposta(request, pk):
    return render(request, "ui/fazer_proposta.html", {"pk": pk})


def acompanhamento_pedido(request, pk):
    return render(request, "ui/acompanhamento_pedido.html", {"pk": pk})


def sitemap(request):
    return render(request, "ui/sitemap.html")
