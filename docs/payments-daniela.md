# Pagos simulados — entrega de Daniela

Fuentes de alcance: `guia_entrega_30_octubre_2026.txt`, sección 3 y contratos 7.5–7.6; `guia de codigo.txt`; `Entrega de requisitos y diseño preliminar - Nim sutz'.pdf`, M08/M09 y RN-E2. Estas referencias se entregaron fuera del repositorio. La guía del 30 define la asignación y los contratos concretos de esta entrega.

## Implementación

- D1: modelos TestCard, Payment, PaymentDetail y CardMovement; migración inicial aditiva y comando idempotente. El código de seguridad usa el hasher de Django; pagos y respuestas conservan solo la terminación de tarjeta.
- D2–D4: validación de formato y simulador, rechazo persistente con motivo, huella HMAC con secreto independiente, recuperación de resultados y restricción de una aprobación por cotización. Vigencia de tarjeta hasta terminar su mes en America/Guatemala. Importes decimales y movimiento incluso si el ajuste es 0.00.
- D5: coordinador atómico y bloqueo del cliente antes de validar la cotización y bloquear la tarjeta. Descuento, movimiento, pago, detalles y aplicación comercial comparten la misma transacción. La aplicación comercial real depende de los servicios de subscriptions descritos abajo.
- D6–D8: resumen del servidor, checkout y resultado con componentes existentes. Doble clic protegido, campos y errores, cancelación antes del envío, clave persistida por cuenta/cotización y recuperación después de fallos técnicos. Los datos de tarjeta no se guardan en sessionStorage. Un rechazo permite otro intento con una clave nueva.

## Preparar el entorno

1. Generar una clave técnica independiente de al menos 32 caracteres y guardarla localmente como `PAYMENTS_IDEMPOTENCY_SECRET`. Por ejemplo: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. No publicar el valor ni cambiarlo mientras deban recuperarse operaciones antiguas.
2. Recrear backend para cargar la variable: `docker compose up -d backend`.
3. Aplicar migraciones: `docker compose exec backend python manage.py migrate`.
4. Con entorno de pruebas y DEBUG=True: `docker compose exec backend python manage.py seed_payment_cards`.

El comando conserva las tarjetas ya creadas, incluyendo saldo, vencimiento y hash. No ofrece recargas. En entornos sin DEBUG se rechaza su ejecución.

| Caso | Número ficticio | Saldo inicial | Moneda |
| --- | --- | --- | --- |
| Aprobable | 9999000000000001 | 500.00 | GTQ |
| Sin saldo | 9999000000000002 | 0.00 | GTQ |
| Deshabilitada | 9999000000000003 | 500.00 | GTQ |
| Vencida | 9999000000000004 | 500.00 | GTQ |
| Moneda incompatible | 9999000000000005 | 500.00 | USD |

Todas usan titular ficticio `NIM SUTZ DEMO`, mes 12 y código de prueba `123`. Al crearse por primera vez, el año de vencimiento es el año de ejecución + 2; la vencida usa el año de ejecución - 1. Para datos inexistentes puede usarse `9999000000000099`. Nunca utilizar datos bancarios reales.

## Contratos y límites de integración

Se implementan POST `/api/payments/checkout/` y GET `/api/payments/operations/<UUID>/` de la guía. La pantalla `/payments/result/:paymentId` consulta GET `/api/payments/results/<id>/`, una ruta adicional de resultado propio que devuelve el mismo objeto de checkout; evita depender del historial de Miguel. La consulta filtra por propietario y no permite editar pagos. No sustituye GET `/api/payments/<id>/` del historial, que Miguel implementará en read_views.py y read_serializers.py.

El checkout consume GET `/api/subscriptions/quotes/<UUID>/`, respuesta `{ "quote": ... }`. El adaptador `payments/commercial.py` requiere:

- `subscriptions.services.validate_quote_for_execution(user=..., quote_id=...)`: cotización validada bajo bloqueo con los campos públicos de la guía (mapping). Debe bloquear cotización y suscripción antes del bloqueo de tarjeta, y revalidar condiciones sin cobrar importes nuevos silenciosamente.
- `subscriptions.services.apply_approved_quote(user=..., quote=..., payment=..., approved_at=...)`: aplica derechos en la transacción existente y devuelve la suscripción serializable mediante subscription_payload.

Estos servicios y las rutas de cotización aún no existen en la copia revisada de subscriptions. El adaptador responde 503 sin descontar ni crear pagos si faltan. No se añadió una activación pagada alternativa ni se duplicaron cálculos comerciales. Hasta integrar los servicios de Rodrigo, D5 y el recorrido real de D6–D8 permanecen pendientes de validación conjunta.

Después de un timeout se consulta la operación y se conserva su clave incluso ante 404. Se puede reenviar con la misma clave y el mismo contenido. Tras recargar hay que volver a ingresar los datos originales, ya que nunca se persistió la tarjeta. Reutilizar la clave con otro contenido devuelve 409. Solo un resultado procesado, o un error inicial de formato que no llegó al procesamiento, libera el intento.

## Verificación

Backend: `docker compose exec backend python manage.py test payments subscriptions` y `docker compose exec backend python manage.py makemigrations --check --dry-run`.

Frontend, desde frontend-nimsutz:

```text
node --test src/features/payments/paymentAttempt.test.mjs
npx --no-install eslint src/features/payments src/router/AppRouter.jsx
npm run build
```

La suite de pagos prueba aprobación/rechazos, importe cero, idempotencia, permisos, CSRF, recuperación propia, normalización, seguridad de respuestas, límite mensual de vencimiento y reversión de registros/cobertura. Los dobles comerciales son explícitos: no prueban los prorrateos ni la cobertura pagada de Rodrigo. `test_concurrency.py` contiene tres pruebas de bloqueo con conexiones concurrentes; se omiten cuando el motor no soporta select_for_update.

Validación realizada localmente: Django 5.2.18 y SQLite en memoria como alternativa, porque Docker no estaba disponible; frontend con las dependencias ya instaladas. Es necesario repetir en el entorno Docker/PostgreSQL y con las versiones fijadas por el proyecto. El lint global reportó seis errores previos fuera de payments (FolderFormModal, UploadPanel, useFiles, Trash, PlansPage y usePlans). No se modificaron esas áreas.

Pendiente antes de la entrega integrada:

- Integrar y verificar los servicios y cotizaciones reales de Rodrigo; hacer contratación, renovación y mejora con dos conceptos.
- Ejecutar concurrencia con PostgreSQL y migraciones sobre una copia con datos previos.
- Verificar manualmente claro/oscuro, móvil, teclado, red interrumpida, reintento y navegación después de aprobación/rechazo. No hay evidencia visual completa todavía.
- Abrir PR hacia develop después de comprobar el remoto y obtener revisión de un compañero.

Resultados locales de esta revisión: 46 pruebas de backend descubiertas entre payments y subscriptions, 43 aprobadas y 3 de concurrencia omitidas por SQLite; 7 pruebas de recuperación/idempotencia del frontend aprobadas; lint de payments y router aprobado; build de Vite aprobado. Las advertencias W042 de claves primarias corresponden a las apps existentes. Estas comprobaciones no certifican Docker/PostgreSQL ni el flujo comercial integrado.
