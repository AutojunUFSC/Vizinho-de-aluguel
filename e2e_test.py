#!/usr/bin/env python3
"""
Teste E2E — Vizinho de Aluguel
Pré-requisitos:
  python manage.py migrate
  python manage.py seed_categories
  pip install requests

Execute do diretório raiz do projeto com o servidor rodando:
  python e2e_test.py

Observações sobre limitações da API atual:
  - Passo 7 (award): endpoint não implementado → feito via ORM
  - Pré-6a (verificação MEI): verification_status é read-only na API → feito via ORM
"""

import os
import sys
import uuid
import django
import requests
from datetime import date, datetime, timedelta

# Configura Django no mesmo processo para passos sem endpoint na API
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.utils import timezone
from apps.accounts.models import MEIProfile
from apps.auctions.models import Bid
from apps.orders.models import ServiceOrder
from apps.services.models import ServiceRequest

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"
RUN = uuid.uuid4().hex[:8]  # sufixo único por execução

_log: list[tuple] = []


def _print_step(tag: str, n, label: str, status_code: int | str = ""):
    suffix = f" (HTTP {status_code})" if status_code else ""
    print(f"  [{tag}] Passo {n}: {label}{suffix}")


def check(n, label: str, res: requests.Response, expect: int) -> bool:
    ok = res.status_code == expect
    _print_step("OK  " if ok else "ERRO", n, label, res.status_code)
    if not ok:
        try:
            print(f"          Detalhe: {res.json()}")
        except Exception:
            print(f"          Detalhe: {res.text[:300]}")
    _log.append((n, label, ok))
    return ok


def orm_step(n, label: str, fn) -> object:
    try:
        result = fn()
        _print_step("OK  ", n, f"{label}  [ORM — sem endpoint na API]")
        _log.append((n, label, True))
        return result
    except Exception as exc:
        _print_step("ERRO", n, f"{label}  [ORM]")
        print(f"          Detalhe: {exc}")
        _log.append((n, label, False))
        return None


def summary() -> None:
    passed = sum(1 for *_, v in _log if v)
    print()
    print("═" * 54)
    print("  RESUMO")
    print("═" * 54)
    for n, label, v in _log:
        _print_step("OK  " if v else "ERRO", n, label)
    print(f"\n  Resultado: {passed}/{len(_log)} passos OK")


# ──────────────────────────────────────────────────────────
print("═" * 54)
print(f"  VIZINHO DE ALUGUEL — TESTE E2E  (run={RUN})")
print("═" * 54)
print()

# MEIProfile.cnpj tem unique=True mas o signal o cria com cnpj="".
# Limpamos entradas órfãs de execuções anteriores para evitar IntegrityError.
MEIProfile.objects.filter(cnpj="").delete()

# ─── 1. Registrar cidadão ─────────────────────────
r = requests.post(f"{API}/auth/auth/register/", json={
    "email":            f"cidadao_{RUN}@e2e.test",
    "full_name":        "João Cidadão E2E",
    "user_type":        "CIDADAO",
    "password":         "Teste@1234",
    "password_confirm": "Teste@1234",
})
if not check(1, "Registrar cidadão", r, 201):
    summary(); sys.exit(1)

# ─── 2. Registrar MEI ────────────────────────────
r = requests.post(f"{API}/auth/auth/register/", json={
    "email":            f"mei_{RUN}@e2e.test",
    "full_name":        "Maria MEI E2E",
    "user_type":        "MEI",
    "password":         "Teste@1234",
    "password_confirm": "Teste@1234",
})
if not check(2, "Registrar MEI", r, 201):
    summary(); sys.exit(1)

# ─── 3. Login de ambos e salvar tokens ───────────
r = requests.post(f"{API}/auth/auth/login/", json={
    "email": f"cidadao_{RUN}@e2e.test",
    "password": "Teste@1234",
})
if not check("3a", "Login cidadão", r, 200):
    summary(); sys.exit(1)
C_HDR = {"Authorization": f"Bearer {r.json()['access']}"}

r = requests.post(f"{API}/auth/auth/login/", json={
    "email": f"mei_{RUN}@e2e.test",
    "password": "Teste@1234",
})
if not check("3b", "Login MEI", r, 200):
    summary(); sys.exit(1)
M_HDR = {"Authorization": f"Bearer {r.json()['access']}"}

citizen_profile_id = requests.get(
    f"{API}/auth/citizen-profiles/me/", headers=C_HDR
).json()["id"]
mei_profile_id = requests.get(
    f"{API}/auth/mei-profiles/me/", headers=M_HDR
).json()["id"]

# Define CNPJ único no perfil MEI (signal cria com cnpj=""; CNPJ deve ser único)
requests.patch(f"{API}/auth/mei-profiles/me/", headers=M_HDR, json={
    "cnpj":          f"12.345.{RUN[:3]}/{RUN[3:7]}-00",
    "razao_social":  f"MEI E2E {RUN} LTDA",
    "nome_fantasia": f"Serviços E2E {RUN}",
})

# ─── 4. Criar endereço para o cidadão ────────────
r = requests.post(f"{API}/auth/addresses/", headers=C_HDR, json={
    "label":        "Casa",
    "cep":          "88010-970",
    "street":       "Rua Bocaiuva",
    "number":       "100",
    "neighborhood": "Centro",
    "city":         "Florianópolis",
    "state":        "SC",
    "is_primary":   True,
})
if not check(4, "Criar endereço para cidadão", r, 201):
    summary(); sys.exit(1)
address_id = r.json()["id"]

# Busca primeira categoria ativa
cats = requests.get(f"{API}/categories/").json()
if not cats:
    print("\n  [ABORT] Sem categorias. Rode: python manage.py seed_categories")
    sys.exit(1)
cat_id = cats[0]["id"]
print(f"\n  [INFO] Categoria selecionada: {cats[0]['name']}\n")

# ─── 5. Criar solicitação de serviço ─────────────
r = requests.post(f"{API}/service-requests/", headers=C_HDR, json={
    "title":            "Conserto de encanamento urgente",
    "description":      "Cano com vazamento embaixo da pia da cozinha.",
    "category":         cat_id,
    "address":          address_id,
    "urgency":          "ALTA",
    "budget_max":       "500.00",
    "auction_end_at":   (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "desired_deadline": (date.today() + timedelta(days=14)).isoformat(),
})
if not check(5, "Criar solicitação de serviço", r, 201):
    summary(); sys.exit(1)
service_request_id = r.json()["id"]

# ─── 6. MEI cria lance ───────────────────────────
# Pré-6a: verification_status é read-only na API → ORM
orm_step(
    "Pré-6a", "Verificar MEI (verification_status read-only na API)",
    lambda: MEIProfile.objects.filter(id=mei_profile_id).update(
        verification_status="VERIFIED"
    ),
)

# Pré-6b: MEI se inscreve na categoria
r = requests.post(
    f"{API}/category-subscriptions/", headers=M_HDR,
    json={"category_ids": [cat_id]},
)
check("Pré-6b", "MEI inscrever-se na categoria", r, 201)

r = requests.post(f"{API}/bids/", headers=M_HDR, json={
    "service_request":   service_request_id,
    "amount":            "350.00",
    "estimated_hours":   4,
    "proposed_deadline": (date.today() + timedelta(days=10)).isoformat(),
    "notes":             "5 anos de experiência em encanamento residencial.",
})
if not check(6, "MEI criar lance", r, 201):
    summary(); sys.exit(1)
bid_id       = r.json()["id"]
bid_amount   = r.json()["amount"]
bid_deadline = r.json()["proposed_deadline"]

# ─── 7. Cidadão faz award do lance ───────────────
# Endpoint /bids/<pk>/award/ não existe na API atual.
# ORM: bid → WINNER, ServiceRequest → AWARDED, cria ServiceOrder.
def _do_award():
    bid = Bid.objects.get(id=bid_id)
    bid.status = "WINNER"
    bid.save()

    sr = ServiceRequest.objects.get(id=service_request_id)
    sr.status     = "AWARDED"
    sr.awarded_at = timezone.now()
    sr.save()

    order = ServiceOrder.objects.create(
        service_request = sr,
        winning_bid     = bid,
        citizen_id      = citizen_profile_id,
        mei_profile_id  = mei_profile_id,
        agreed_amount   = bid_amount,
        agreed_deadline = bid_deadline,
    )
    return str(order.id)

order_id = orm_step(7, "Cidadão awarda lance (endpoint não implementado)", _do_award)
if not order_id:
    summary(); sys.exit(1)

# ─── 8. MEI inicia o serviço ─────────────────────
r = requests.post(f"{API}/service-orders/{order_id}/start/", headers=M_HDR)
if not check(8, "MEI iniciar serviço (start)", r, 200):
    summary(); sys.exit(1)

# ─── 9. MEI conclui o serviço ────────────────────
r = requests.post(f"{API}/service-orders/{order_id}/complete/", headers=M_HDR)
if not check(9, "MEI concluir serviço (complete)", r, 200):
    summary(); sys.exit(1)

# ─── 10. Cidadão confirma ────────────────────────
r = requests.post(f"{API}/service-orders/{order_id}/confirm/", headers=C_HDR)
if not check(10, "Cidadão confirmar serviço (confirm)", r, 200):
    summary(); sys.exit(1)

summary()
