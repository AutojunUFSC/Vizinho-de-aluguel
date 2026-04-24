from django.shortcuts import render

def home(request):
    return render(request, "ui/home.html")

def cadastro(request):
    return render(request, "ui/cadastro.html")

def home_usuario(request):
    return render(request, "ui/home_usuario.html")

def nova_solicitacao(request):
    return render(request, "ui/nova_solicitacao.html")

def minhas_solicitacoes(request):
    return render(request, "ui/minhas_solicitacoes.html")
