# Pagos de Daniela: integración y validación

Estado al 29 de octubre de 2026: D1–D8 implementadas y validadas en el entorno Docker local, con los servicios reales de subscriptions. Este cierre se refiere a pagos; no certifica el resto de la entrega ni un despliegue público.

## Alcance y evidencia

| Tarea | Implementación y validación |
| --- | --- |
| D1 | TestCard, Payment, PaymentDetail, CardMovement, migraciones y seed idempotente. Los saldos existentes no se restablecen y el código de seguridad se conserva como hash. |
| D2 | Formato, datos de tarjeta, habilitación, vigencia hasta fin de mes en America/Guatemala, moneda y saldo. Casos de rechazo cubiertos por pruebas. |
| D3 | Aprobaciones/rechazos con motivo y detalles; permisos y formato se validan antes de crear pagos. API probada con sesión Django y CSRF reales. |
| D4 | HMAC con clave independiente, recuperación por UUID, conflicto ante contenido distinto y una aprobación por cotización. Repetición y concurrencia probadas en PostgreSQL. |
| D5 | Contratación, renovación, mejora con dos conceptos y ajuste 0.00 con los servicios reales de Rodrigo. Fallo inyectado después de aplicar cobertura revierte descuento, registros y cobertura. |
| D6 | Resumen de solo lectura e importes, conceptos, moneda y efectos del servidor. Mejora con ciclo anticipado comprobada en navegador. |
| D7 | Formato de número/vencimiento, teclado, carga y doble clic; pérdida de respuesta después de procesar el pago y recuperación tras recargar sin otro cobro. |
| D8 | Resultado consultado al servidor, aprobación en modal, rechazo con corrección/nuevo intento, navegación a archivos, ambos temas y móvil. |

Referencias de alcance: guía de entrega del 30 de octubre, guía de código y mockups M08/M09 aportados por el equipo.

## Correcciones encontradas al integrar

- La validación de checkout rechazaba renovar un contrato cuyo plan fue desactivado. Ahora conserva esa posibilidad sin habilitar nuevas contrataciones hacia un plan desactivado.
- Una mejora cotizada antes de renovar podía omitir el ajuste del ciclo futuro. Quote.execution_context congela cobertura, versión destino y cambio programado. Una variación exige otra cotización/confirmación y devuelve 409; no recalcula y cobra silenciosamente.
- get_active_subscription ahora reutiliza la resolución efectiva: reconoce el ciclo anticipado al llegar a su inicio y el retorno a Gratis al terminar cobertura.
- Renovar informa y guarda la nueva fecha de una bajada ya programada.
- El resultado muestra coverage_end, para reflejar la cobertura ampliada por una renovación.

La migración subscriptions.0003_quote_execution_context es aditiva. Cotizaciones pendientes creadas antes de esta protección requieren un nuevo resumen; no se eliminan pagos ni contratos. Los reintentos de pagos completados siguen recuperando el resultado antes de validar la cotización.

## Configuración y preparación

En el .env local:

```text
PAID_PLANS_ENABLED=true
PAYMENTS_IDEMPOTENCY_SECRET=<clave técnica independiente de al menos 32 caracteres>
```

La clave no se sube a Git ni se comparte con el equipo. No cambiarla mientras se necesite reproducir huellas de operaciones existentes. docker-compose.yml transmite el indicador al backend; .env.example deja los pagos deshabilitados por defecto.

```text
docker compose up -d backend
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_plans
docker compose exec backend python manage.py seed_payment_cards
```

Se configuró una clave local independiente y se aplicó la migración. Los archivos de configuración descargados se revisaron: solo se incorporó la variable necesaria al compose, conservando las opciones de correo actuales.

## Tarjetas precargadas del seed

| Número ficticio | Caso | Saldo inicial | Moneda |
| --- | --- | --- | --- |
| 9999000000000001 | Aprobable | 500.00 | GTQ |
| 9999000000000002 | Sin saldo | 0.00 | GTQ |
| 9999000000000003 | Deshabilitada | 500.00 | GTQ |
| 9999000000000004 | Vencida | 500.00 | GTQ |
| 9999000000000005 | Moneda incompatible | 500.00 | USD |

Titular NIM SUTZ DEMO, código de prueba 123 y mes 12. Al crearse, el año normal es el año de ejecución + 2; la vencida usa el año - 1. El comando conserva el vencimiento, saldo y hash de las tarjetas existentes. Solo admite DEBUG=True y no ofrece recargas. Usar exclusivamente datos ficticios.

## Contratos

- POST /api/payments/checkout/ con Idempotency-Key UUID y cuerpo quote_id/card. No acepta precios, resultado ni propietario del navegador.
- GET /api/payments/operations/<UUID>/ recupera el resultado propio. Un 404 no permite iniciar otra operación: se conserva la clave.
- GET /api/payments/results/<id>/ alimenta el resultado propio. El historial de Miguel usa sus rutas y modelos compartidos.
- payments/commercial.py llama a subscriptions.services.validate_quote_for_execution y apply_approved_quote. El primero devuelve un mapping y el segundo una Subscription serializable mediante subscription_payload.
- execute_checkout abre la transacción; saldo, movimiento, pago, detalles y cobertura se confirman juntos. Orden: cliente, cotización, suscripción y tarjeta.

El frontend solo guarda la clave y referencias de navegación en sessionStorage. Para reenviar tras recargar se vuelven a ingresar los datos originales, pues no se persistió la tarjeta. Un rechazo procesado permite un intento voluntario nuevo con otra clave.

## Validación ejecutada en Docker/PostgreSQL

```text
docker compose exec backend python manage.py test --noinput
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py check
docker compose exec frontend node --test src/features/payments/paymentAttempt.test.mjs src/features/payments/paymentPresentation.test.mjs src/features/subscription/subscriptionModel.test.mjs
docker compose exec frontend npx --no-install eslint src/features/payments src/features/subscription src/router/AppRouter.jsx src/shared/components/Modal/Modal.jsx
docker compose exec frontend npm run build
```

Resultados: 190 pruebas backend aprobadas, sin omisiones; 19 frontend aprobadas; check, coherencia de migraciones, lint del alcance comercial y build aprobados. Hay seis pruebas de concurrencia: tres del coordinador aislado y tres con cotizaciones/cobertura reales.

La prueba test_migrations.py retrocede únicamente la base efímera de pruebas a subscriptions.0001 y vuelve a la última migración, conservando cuenta, propietario, carpeta, archivo y condiciones históricas. En la base local se compararon huellas antes/después de migrar y después de QA: las cuatro cuentas, tres archivos, una carpeta, dos suscripciones y los cinco saldos anteriores permanecieron idénticos.

### Navegador con API real

Se crearon dos cuentas verificadas y dos tarjetas exclusivas de QA, sin reutilizar cuentas personales ni descontar tarjetas previas. Se comprobó:

1. Selección de Básico desde planes, cotización, checkout, doble clic con un único POST y acceso a archivos.
2. Renovación: el POST se procesó realmente y se abortó solo su respuesta hacia el navegador. Tras recargar, la consulta de la misma operación recuperó el resultado sin otro pago.
3. Mejora a Premium con ajuste actual y diferencia del ciclo anticipado; ambos ciclos quedaron en Premium.
4. Modal en claro/oscuro y móvil de 390 px, foco inicial, Escape y ausencia de desbordamiento horizontal.
5. Segundo usuario: rechazo por código incorrecto sin cobertura, corrección con otro intento y aprobación. Pagos, detalle y cotización del primero devolvieron 404 al segundo.

Se conservaron las cuentas/tarjetas de QA como datos locales de prueba; sus contraseñas no se incluyen en el repositorio. Evidencia resumida sin credenciales: evidence/payments-validation-2026-10-29.json.

## Fuera de este cierre

El lint global todavía tiene siete errores anteriores en FolderFormModal, UploadPanel, useFiles, Trash, PlansPage, RequireSession y usePlans. No se modificaron esas implementaciones para ocultar sus errores. Los cambios de pruebas de cuota/destino actualizan expectativas antiguas de capacidad cero al retorno a Gratis definido por la guía; no alteran el almacenamiento.

No se incluyen administración, correo real, cierre de todas las tareas de Rodrigo/Miguel/Cristian ni despliegue público. Las correcciones de integración deben revisarse mediante PR a develop.

Actualización de suscripciones: el cierre posterior de R1–R9 y la validación ampliada a 211 pruebas backend del código versionado están documentados en [subscriptions-rodrigo.md](subscriptions-rodrigo.md).
