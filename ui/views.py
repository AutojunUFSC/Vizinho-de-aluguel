from django.shortcuts import render

def home(request):
    return render(request, "ui/home.html")

def cadastro(request):
    return render(request, "ui/cadastro.html")