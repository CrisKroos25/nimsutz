# Eliminación de cuenta desde el perfil

## Experiencia

En Mi perfil aparece Eliminar cuenta. El primer clic abre una confirmación del design system que explica el borrado permanente de perfil, archivos/carpetas y papelera, suscripción e historial de pagos. Solo Aceptar y eliminar cuenta ejecuta la solicitud; Cancelar y Escape conservan la cuenta. Mientras se procesa, no se puede duplicar el envío ni cerrar la confirmación.

Al finalizar se cierra la sesión y se muestra el resultado en login. El correo queda libre inmediatamente para un registro nuevo: otra identidad, sin verificación, plan, preferencias, archivos ni pagos anteriores. No se reactiva el registro antiguo.

## API y responsabilidades

DELETE /api/auth/account/ con JSON {"confirm": true}. Solo la cuenta de la sesión, sin ID de propietario recibido del cliente. Autenticación y CSRF obligatorios; una confirmación ausente/ambigua o campos adicionales devuelven 400. HTTP 200 indica borrado completado; 202 indica que los datos de cuenta se borraron y queda limpieza física en proceso. La respuesta incluye user: null y deletion_pending: boolean.

accounts/deletion.py coordina la transacción bajo el mismo bloqueo de usuario que los servicios comerciales y de cuota. subscriptions/deletion.py retira operaciones e intervalos históricos protegidos; payments/deletion.py borra movimientos, detalles y pagos propios. Después se elimina el usuario con sus relaciones en cascada, tokens y sesiones, incluidas las vencidas. También se retiran las entradas de administración que identifican sus archivos/carpetas. Un fallo de base de datos revierte el conjunto antes de borrar objetos.

Los planes/versiones y tarjetas del simulador son recursos compartidos: se conservan. No se reinician saldos ni se producen reembolsos implícitos. Las otras cuentas mantienen sus datos y sesiones.

## Borrado físico y recuperación

files.PendingObjectDeletion conserva únicamente la clave técnica del objeto y sus fechas, sin correo, perfil ni relación con el usuario eliminado. Los trabajos se crean en la misma transacción que libera el correo. Tras confirmar PostgreSQL se intenta el borrado en MinIO; si falla, el trabajo sigue disponible para cleanup_expired_uploads, ejecutado cada minuto por el servicio cleanup existente. Se procesa por lotes y se corta una serie de fallos para evitar acumular timeouts.

Una URL de carga emitida antes del borrado puede seguir vigente. Por eso el objeto se borra inmediatamente y se mantiene un último reintento hasta que vence ese permiso, evitando que una carga tardía deje un objeto huérfano. La UI informa que se está terminando la limpieza cuando corresponde; no afirma que todo terminó si quedan trabajos. Al completar el borrado físico se elimina también el trabajo técnico. Las claves de objetos de otra identidad nueva nunca se mezclan por reutilizar el correo.

Los dos procesos periódicos toleran que una cuenta se elimine después de obtener su lista de candidatos. No fallan por ese usuario ausente ni recrean su identidad.

## Instalación

Aplicar files.0004_pending_object_deletion antes de ejecutar la eliminación y mantener activo cleanup:

```sh
docker compose exec backend python manage.py migrate
docker compose up -d --build backend frontend cleanup subscription_worker
```

No requiere variables ni dependencias nuevas. La migración solo agrega la tabla técnica: no elimina datos de cuentas existentes.

## Validación

- 263 pruebas backend del código versionado aprobadas en PostgreSQL, sin omisiones. Incluyen 11 casos específicos de borrado: datos/relaciones protegidas, reutilización de correo, sesiones/tokens, confirmación y CSRF, rollback, fallos/reintentos de almacenamiento, cargas tardías y carreras con otra confirmación y con los workers.
- 51 pruebas frontend aprobadas; lint global y build de Docker/Linux sin errores.
- manage.py check y makemigrations --check --dry-run correctos.
- Las suites completas se ejecutaron desde copias limpias producidas por git archive.

Se probó en navegador y con Django/MinIO reales una cuenta exclusiva de QA con pago aprobado, plan y archivos dentro/fuera de papelera. El primer clic y cancelar no enviaron DELETE; dos clics en aceptar produjeron una sola solicitud; se comprobó el borrado físico del objeto y otra sesión de control siguió intacta. Después se registró el mismo correo desde la UI y se verificó una identidad nueva, pendiente de verificación, con cero archivos, carpetas, reservas, suscripciones, preferencias y pagos. También se observó que el worker real completó los trabajos pendientes. Esta prueba de registro no certifica entrega SMTP a un buzón.

Revisión en claro/oscuro a 1440/390 px: confirmación dentro del viewport, foco inicial en Cancelar, navegación por Tab, Escape y foco devuelto. Un error 503 controlado conserva la cuenta y permite cancelar/reintentar. Credenciales y URLs firmadas de QA no se versionan.

[Resumen de evidencia](evidence/account-deletion-validation-2026-10-30.json).

## Capturas

| Estado | Captura |
| --- | --- |
| Confirmación clara, escritorio | [Ver](evidence/account-deletion/confirmation-light-desktop.png) |
| Confirmación oscura, móvil | [Ver](evidence/account-deletion/confirmation-dark-mobile.png) |
| Cuenta eliminada | [Ver](evidence/account-deletion/result.png) |
| Nuevo registro con el mismo correo | [Ver](evidence/account-deletion/register-again.png) |

Los cambios locales de administración y almacenamiento sin seguimiento se preservaron fuera de este trabajo. Sus fallos ya conocidos no se incluyen en la validación del código versionado del PR.
