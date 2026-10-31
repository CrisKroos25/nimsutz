# payments/test_history.py
from datetime import datetime, timezone as dt_timezone
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Payment, PaymentDetail

PLAN = {"plan_code": "basic", "version_id": 2, "name": "Básico", "capacity_bytes": 1073741824}


def make_payment(owner, *, status="approved", operation="contract", amount="15.00",
                 created=None, reason=None, last4="0001"):
    payment = Payment.objects.create(
        owner=owner, operation_key=uuid4(), request_digest="x" * 64, quote_id=uuid4(),
        status=status, reason_code=reason, operation=operation, amount=amount, currency="GTQ",
        card_last4=last4, plan_snapshot=PLAN, result_snapshot={"secreto": "no debe salir"},
    )
    PaymentDetail.objects.create(payment=payment, code="contract_cycle",
                                 description="Primer ciclo Básico", amount=amount)
    if created:
        Payment.objects.filter(pk=payment.pk).update(created_at=created)
    return payment


class HistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.ana = User.objects.create_user(email="ana@example.test", name="Ana", password="Clave-Segura-123",
                                           email_verified=True, account_status="activa")
        cls.beto = User.objects.create_user(email="beto@example.test", name="Beto", password="Clave-Segura-123",
                                            email_verified=True, account_status="activa")

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.ana)

    def get(self, query=""):
        return self.client.get(f"/api/payments/{query}")

    # --- aislamiento y permisos ---
    def test_lista_solo_los_pagos_propios(self):
        mine = make_payment(self.ana)
        make_payment(self.beto)
        body = self.get().json()
        self.assertEqual(body["count"], 1)
        self.assertEqual([item["id"] for item in body["results"]], [mine.id])

    def test_detalle_de_otra_cuenta_responde_404(self):
        other = make_payment(self.beto)
        response = self.client.get(f"/api/payments/{other.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")

    def test_el_propietario_no_se_puede_pedir_por_parametro(self):
        make_payment(self.beto)
        self.assertEqual(self.get(f"?owner={self.beto.id}&owner_id={self.beto.id}").json()["count"], 0)

    def test_sin_sesion_se_rechaza(self):
        self.assertEqual(APIClient().get("/api/payments/").status_code, 403)

    def test_cuenta_no_cliente_recibe_account_not_eligible(self):
        admin = get_user_model().objects.create_superuser(email="adm@example.test", name="Adm", password="Clave-Segura-123")
        self.client.force_login(admin)
        response = self.get()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "account_not_eligible")

    def test_cuenta_sin_verificar_recibe_account_not_eligible(self):
        pending = get_user_model().objects.create_user(email="pend@example.test", name="P", password="Clave-Segura-123")
        self.client.force_login(pending)
        self.assertIn(self.get().status_code, (403,))

    # --- solo lectura y campos publicos ---
    def test_no_permite_alterar_resultados(self):
        payment = make_payment(self.ana)
        for method in ("post", "put", "patch", "delete"):
            for url in ("/api/payments/", f"/api/payments/{payment.id}/"):
                response = getattr(self.client, method)(url, {"status": "approved"}, format="json")
                self.assertIn(response.status_code, (403, 405), (method, url, response.status_code))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "approved")

    def test_no_expone_datos_internos(self):
        payment = make_payment(self.ana)
        for body in (self.get().json()["results"][0], self.client.get(f"/api/payments/{payment.id}/").json()):
            for forbidden in ("operation_key", "quote_id", "request_digest", "result_snapshot",
                              "owner", "number", "security_code"):
                self.assertNotIn(forbidden, body)

    def test_campos_del_listado_y_formato_del_dinero(self):
        make_payment(self.ana, amount="15")
        item = self.get().json()["results"][0]
        self.assertEqual(set(item), {"id", "reference", "status", "reason_code", "operation", "amount",
                                     "currency", "created_at", "card_last4"})
        self.assertEqual(item["amount"], "15.00")
        self.assertIsInstance(item["amount"], str)
        self.assertEqual(item["card_last4"], "0001")

    def test_detalle_trae_lineas_y_plan_conservado(self):
        payment = make_payment(self.ana)
        body = self.client.get(f"/api/payments/{payment.id}/").json()
        self.assertEqual(body["lines"], [{"code": "contract_cycle", "description": "Primer ciclo Básico", "amount": "15.00"}])
        self.assertEqual(body["plan"]["name"], "Básico")
        self.assertEqual(body["plan"]["version_id"], 2)

    def test_rechazado_conserva_su_motivo(self):
        make_payment(self.ana, status="rejected", reason="insufficient_funds")
        item = self.get("?status=rejected").json()["results"][0]
        self.assertEqual(item["reason_code"], "insufficient_funds")

    # --- filtros ---
    def test_filtros_por_resultado_y_concepto(self):
        make_payment(self.ana, status="approved", operation="contract")
        make_payment(self.ana, status="rejected", operation="renew", reason="card_disabled")
        make_payment(self.ana, status="approved", operation="change")
        self.assertEqual(self.get("?status=approved").json()["count"], 2)
        self.assertEqual(self.get("?status=rejected").json()["count"], 1)
        self.assertEqual(self.get("?operation=change").json()["count"], 1)
        self.assertEqual(self.get("?status=approved&operation=renew").json()["count"], 0)

    def test_date_to_incluye_todo_el_dia_en_guatemala(self):
        # Guatemala es UTC-6 y no tiene horario de verano.
        inside_late = make_payment(self.ana, created=datetime(2026, 11, 1, 5, 59, tzinfo=dt_timezone.utc))   # 31 oct 23:59 GT
        outside_next = make_payment(self.ana, created=datetime(2026, 11, 1, 6, 0, tzinfo=dt_timezone.utc))   # 1 nov 00:00 GT
        inside_early = make_payment(self.ana, created=datetime(2026, 10, 31, 6, 0, tzinfo=dt_timezone.utc))  # 31 oct 00:00 GT
        before = make_payment(self.ana, created=datetime(2026, 10, 31, 5, 59, tzinfo=dt_timezone.utc))       # 30 oct 23:59 GT
        ids = {item["id"] for item in self.get("?date_from=2026-10-31&date_to=2026-10-31").json()["results"]}
        self.assertEqual(ids, {inside_late.id, inside_early.id})
        self.assertNotIn(outside_next.id, ids)
        self.assertNotIn(before.id, ids)

    def test_solo_date_from_o_solo_date_to(self):
        old = make_payment(self.ana, created=datetime(2026, 9, 1, 12, tzinfo=dt_timezone.utc))
        new = make_payment(self.ana, created=datetime(2026, 10, 20, 12, tzinfo=dt_timezone.utc))
        self.assertEqual([i["id"] for i in self.get("?date_from=2026-10-01").json()["results"]], [new.id])
        self.assertEqual([i["id"] for i in self.get("?date_to=2026-09-30").json()["results"]], [old.id])

    def test_filtros_invalidos_responden_400(self):
        for query in ("?status=pagado", "?operation=otra", "?date_from=31-10-2026", "?date_from=2026-10-31&date_to=2026-10-01",
                      "?page=0", "?page=abc", "?page_size=0"):
            response = self.get(query)
            self.assertEqual(response.status_code, 400, query)
            body = response.json()
            self.assertEqual(body["code"], "invalid_request")
            self.assertIn("field_errors", body)

    # --- orden y paginacion ---
    def test_orden_mas_reciente_primero_con_desempate_por_id(self):
        same = datetime(2026, 10, 20, 12, tzinfo=dt_timezone.utc)
        a = make_payment(self.ana, created=same)
        b = make_payment(self.ana, created=same)
        newest = make_payment(self.ana, created=datetime(2026, 10, 21, 12, tzinfo=dt_timezone.utc))
        self.assertEqual([i["id"] for i in self.get().json()["results"]], [newest.id, b.id, a.id])

    def test_paginacion_por_defecto_y_enlaces(self):
        for _ in range(25):
            make_payment(self.ana)
        first = self.get().json()
        self.assertEqual((first["count"], len(first["results"])), (25, 20))
        self.assertIsNone(first["previous"])
        self.assertIn("page=2", first["next"])
        second = self.client.get(first["next"]).json()
        self.assertEqual(len(second["results"]), 5)
        self.assertIsNone(second["next"])
        self.assertIn("page=1", second["previous"])
        ids = [i["id"] for i in first["results"]] + [i["id"] for i in second["results"]]
        self.assertEqual(len(set(ids)), 25)

    def test_los_enlaces_conservan_los_filtros(self):
        for _ in range(3):
            make_payment(self.ana, status="approved")
        body = self.get("?status=approved&page_size=2").json()
        self.assertIn("status=approved", body["next"])
        self.assertIn("page_size=2", body["next"])

    def test_page_size_maximo_100(self):
        for _ in range(105):
            make_payment(self.ana)
        self.assertEqual(len(self.get("?page_size=500").json()["results"]), 100)

    def test_historial_vacio_y_pagina_inexistente(self):
        self.assertEqual(self.get().json(), {"count": 0, "next": None, "previous": None, "results": []})
        make_payment(self.ana)
        response = self.get("?page=9")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")

    def test_fecha_final_maxima_no_produce_error_del_servidor(self):
        response = self.get("?date_to=9999-12-31")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_request")
        self.assertIn("date_to", response.json()["field_errors"])
