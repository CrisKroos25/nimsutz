# Cierre de suscripciones de Rodrigo — 29 de octubre de 2026

Implementación de R1–R9 según la guía del 30 y la guía de código. La rama parte de develop con la integración de pagos del PR #23. Las pantallas R10/R11 siguen perteneciendo a Miguel; solo se ajustaron los mensajes necesarios para explicar el pago manual del destino.

## Reglas y comportamiento

- **R1:** una identidad de Subscription por cliente, respaldada por restricción única. La primera cotización pagada guarda selección/versiones y estado pending; no concede cuota. Un rechazo conserva la identidad. Confirmar Gratis o aprobar el pago reutiliza ese registro.
- **R2:** Gratis sigue siendo explícito e idempotente. apply_approved_quote exige un pago aprobado propio, persistido y correspondiente a la cotización, importe y moneda; no puede activar derechos con payment=None.
- **R3:** cálculo y revalidación en backend. Las cotizaciones congelan las condiciones e identifican la cobertura/selección/cambio que existían al emitirlas. Si cambian, requieren nueva confirmación; no se cobra un importe recalculado sin mostrarlo.
- **R4:** meses calendario en America/Guatemala, hora y día ancla conservados e intervalos [inicio, fin). El catálogo publica periodicity=calendar_month; la interfaz muestra mes, conservando duration_days por compatibilidad.
- **R5:** como máximo un ciclo anticipado, con versión y condiciones contratadas. Renovar comunica y actualiza la fecha de una bajada pendiente.
- **R6:** mejora con ajuste del ciclo actual y diferencia completa del ciclo anticipado cuando existe. Los intervalos originales quedan como sustituidos y se registran los segmentos efectivos, conservando el ciclo/ancla de referencia.
- **R7:** confirmar una bajada solo la programa. Gratis admite exceso de cuota y conserva archivos/consumo. Si el destino es Básico, vencer Premium no activa almacenamiento pagado ni cobra: se aplica Gratis y la programación queda pendiente de revisar y pagar. La aprobación manual posterior activa un ciclo desde ese instante, con condiciones y consumo revalidados.
- **R8:** las consultas autorizadas resuelven la cobertura efectiva, aunque el proceso periódico se retrase. subscription_worker ejecuta reconcile_subscriptions cada 60 segundos. Un ciclo anticipado ya terminado no concede capacidad pagada vencida.
- **R9:** nombre versionado e inmutable junto con precio, capacidad, moneda y periodicidad congelados en los tramos. Publicar otra versión o desactivar el catálogo no modifica los contratos anteriores ni bloquea su renovación.

### Programación y pago: dos momentos diferentes

En una cotización schedule_downgrade, requires_payment=false significa que confirmar la programación no cobra. En ScheduledChange, requires_payment=true significa que activar el destino pagado requerirá aprobación posterior. payment_due indica, desde el servidor, que la fecha programada ya llegó.

La interfaz muestra esta condición y permite ir al flujo existente de cambio/checkout. No se añadió una ruta de activación pagada alternativa.

## Organización del código

services.py conserva las entradas públicas compatibles para payments, files y las vistas. Las responsabilidades están separadas en:

| Módulo | Responsabilidad |
| --- | --- |
| catalog.py | Catálogo y condiciones publicadas. |
| terms.py | Instantáneas, contexto comercial, elegibilidad y bloqueo del cliente. |
| coverage.py | Identidad pendiente, Gratis explícito y resolución/proyección efectiva. |
| history.py | Registro y sustitución de intervalos, conservando originales. |
| entitlements.py | Aplicar los derechos de contratación, renovación o mejora aprobadas. |
| quotations.py | Cálculo/validación de cotizaciones y coordinación de su ejecución aprobada. |
| scheduled.py | Confirmación idempotente y cancelación sin cobro. |
| payloads.py | Representación pública de los estados y resultados. |
| preferences.py | Preferencias de navegación que no conceden cobertura. |

Los constructores de cotización y aplicadores de derechos se seleccionan mediante registros de operaciones. Las vistas validan el contrato y coordinan respuestas, sin contener cálculos de precio o fechas. Se mantienen las sesiones Django, CSRF, el cliente HTTP y los componentes existentes.

## Compatibilidad de API

Se conservan las rutas y campos existentes. GET /api/subscriptions/current/ mantiene subscription=null si la identidad está pendiente y añade pending_selection, sin presentar selección como cobertura. El campo scheduled_change añade target_plan_version_id y payment_due.

POST /api/subscriptions/quotes/<UUID>/confirm/ exige cuerpo {} e Idempotency-Key UUID. ScheduledOperation conserva el resultado por propietario/clave y una confirmación por cotización. Repetir la misma operación devuelve el resultado anterior incluso tras vencer la cotización. Reutilizar la clave con otra cotización devuelve 409. Cancelar no borra la evidencia; un replay no resucita el cambio cancelado.

Las rutas comerciales nuevas exigen cliente activo y verificado y entregan errores uniformes, incluyendo CSRF. Recursos ajenos responden 404. Se conserva el orden de bloqueo cliente, cotización, suscripción y tarjeta en la integración con pagos.

## Migración conservadora

subscriptions.0004_coverageperiod_scheduledoperation_planversion_name_and_more:

- Añade selección pendiente, nombre de versión, instantánea de cotización, CoveragePeriod y ScheduledOperation.
- Congela los contratos existentes sin cambiar IDs, propietarios, saldos, pagos ni fechas.
- Reutiliza nombres históricos disponibles en pagos; si no existen, conserva el nombre disponible al migrar. No inventa intervalos intermedios que el modelo anterior ya hubiera sobrescrito; los pagos y sus instantáneas anteriores permanecen intactos.
- Se detiene antes de modificar datos si encuentra varias identidades de suscripción por cliente. Requiere consolidación revisada; no borra automáticamente registros para que la restricción pase.

La migración ya se aplicó en el entorno local. Las pruebas de retroceso del esquema se ejecutan exclusivamente sobre la base efímera de tests. No revertir esta migración en un entorno con historial nuevo sin preparar la conservación de ese historial.

## Proceso periódico

```text
docker compose up -d backend db
docker compose exec backend python manage.py migrate
docker compose up -d subscription_worker
docker compose logs subscription_worker
```

El worker comparte configuración del backend mediante un ancla de Compose, usa restart=unless-stopped y no publica puertos. Espera si faltan migraciones o la base aún no está disponible. Se puede verificar una ejecución con:

```text
docker compose exec backend python manage.py watch_subscriptions --once
```

--once devuelve error si no puede verificar/procesar por migraciones pendientes o base no disponible. Los registros usan IDs de suscripción, no correos. El worker ejecutado realmente durante QA reconcilió una bajada vencida sin cobrar ni conceder Básico.

## Validación

- **211 pruebas backend del código versionado aprobadas en Docker/PostgreSQL, sin omisiones.** Además pasaron las 214 del entorno local, que incluye tres pruebas de almacenamiento sin seguimiento y fuera de este PR.
- Concurrencia de selecciones, confirmación repetida y vencimiento, además de la concurrencia de checkout ya existente.
- Migración desde contratos anteriores y rechazo conservador de identidades duplicadas.
- Fronteras de cobertura, febrero bisiesto y recuperación del día ancla; conservación del original y tramos sustituidos al mejorar.
- Rechazo con selección pendiente, activación sobre la misma identidad, pago requerido, cambios de catálogo, nombres históricos y versiones inmutables.
- Gratis con exceso, Básico pendiente de pago, consumo revalidado al pagar, cancelación/replay, permisos y CSRF.
- **38 pruebas frontend aprobadas**, lint de los archivos comerciales modificados y build correctos.
- manage.py check y makemigrations --check --dry-run sin incidencias.

### Navegador con API real

Con dos cuentas y tarjetas exclusivas de QA se comprobó selección pendiente/rechazo/corrección sobre la misma identidad; programación sin cobro y cancelación idempotente; worker real cada minuto; paso a Gratis al vencer Premium, pago manual de Básico y retorno a Gratis conservando 150 MB usados. Las credenciales de QA no se versionan.

Se compararon los registros originales antes y después de migrar y de ejecutar QA: seis cuentas, tres archivos, una carpeta, cuatro suscripciones, cinco pagos, cuatro cotizaciones y siete saldos permanecieron iguales en sus campos anteriores. Las cotizaciones se identificaron por sus UUID originales, no por su orden frente a las nuevas cotizaciones de QA.

Resumen portable: evidence/subscriptions-validation-2026-10-29.json.

## Fuera de este trabajo

Los pendientes de correo/almacenamiento de Cristian, el lint global y la evidencia visual global de Miguel mantienen sus responsables. Los cuatro archivos locales sin seguimiento de almacenamiento se conservaron fuera de los commits. El cierre completo de la entrega y el despliegue público no se deducen de estas pruebas.
