# Cierre de Miguel — entrega del 30 de octubre de 2026

## Alcance y base

Guía del 30 de octubre, pendientes_miguel.txt y guía de código del proyecto, incluidas sus reglas de Git. Rama feature/e2-cierre-visual-miguel desde develop b90a745, con PR #24 ya integrado. Se conservan los contratos, la sesión Django, el design system y las implementaciones de C1–C3/R10/R11 existentes.

## Resultado por tarea

| Tarea | Cierre y evidencia |
| --- | --- |
| C1 | Historial y detalle propios de solo lectura, filtros y paginación existentes verificados. Se corrigió date_to=9999-12-31: devuelve 400 con error de campo en lugar de 500. 21 pruebas específicas del historial. |
| C2 | Historial aprobado/rechazado, detalle, conceptos, referencia, moneda, fecha de Guatemala, nombre/versiones conservados y tarjeta enmascarada verificados con registros reales. |
| C3 | Perfil → suscripción → renovación/cambio → checkout → modal de aprobación → archivos; historial → detalle. El foco continúa en el contenido al navegar y los modales mantienen Tab/Escape y restituyen el foco. |
| C4 | El test de intención usa el catálogo dinámico y pasa. Lint global sin errores, conservando las reglas de ESLint. |
| C5 | Revisión visual de acceso, planes, perfil, suscripción, renovación, cambio, pago/resultado, historial/detalle, archivos, carga, previsualización y papelera en claro/oscuro y escritorio/móvil. Estados de error/carga/vacío y teclado comprobados según la matriz siguiente. |
| C6 | Lista de comprobación, capturas y resumen JSON de esta versión en docs/evidence. Los casos con respuestas controladas se distinguen de los recorridos reales. |
| R10 | Plan efectivo, consumo, vigencia, ciclo anticipado y acciones del backend. La selección pendiente ahora se muestra como pago pendiente y nunca como cobertura. |
| R11 | Gratis sin renovación, segundo anticipo bloqueado, mejora con dos conceptos, programación/cancelación y paso al checkout. El resumen vence en pantalla; un conflicto al confirmar exige generar otro. La renovación explica que desplaza la fecha del cambio programado. |

## Correcciones realizadas

- Filtros del historial con nombres, errores asociados por aria-describedby y foco en el primer dato inválido.
- Suscripción pendiente, catálogo sin alternativas y vencimiento automático del resumen. Sin precios ni prorrateos calculados en React.
- Gestor de subidas compuesto con Modal: título y cierre accesibles, selección por teclado, bloqueo del fondo, Tab contenido, Escape y devolución del foco. La acción de ocultar un estado no se presenta como cancelación de la transferencia.
- Extensión opcional headerAction del modal compartido, compatible con los consumidores existentes. El resultado aprobado sigue siendo emergente.
- Contraste del texto sobre acciones naranjas y sobre botones de peligro oscuros mediante tokens, conservando la paleta del proyecto. Corrección de caracteres mal codificados en mensajes de catálogo/preferencia.

## Lista de comprobación del recorrido

| Caso | Resultado esperado | Resultado obtenido | Tipo |
| --- | --- | --- | --- |
| Cuenta A sin plan | Sin cobertura; historial vacío | Conforme; sin pago inventado | API y navegador reales |
| Contratación rechazada/corregida | Selección pendiente, ningún derecho hasta aprobar | Rechazo visible, pago pendiente y luego activación | API y navegador reales |
| Resultado aprobado | Modal, foco y continuación a archivos | Conforme | API y navegador reales |
| Renovación manual | Resumen del servidor, un anticipo como máximo | Pago aprobado y siguiente renovación bloqueada | API y navegador reales |
| Mejora con ciclo anticipado | Dos conceptos del servidor | Ajuste actual + diferencia del ciclo anticipado, checkout y aprobación | API y navegador reales |
| Bajada a Gratis | Confirmar sin cobrar; cancelar sin perder cobertura | Programación y cancelación comprobadas | API y navegador reales |
| Historial y detalle | Solo registros propios y tarjeta enmascarada | Filtro de rechazados y motivo visibles; cuenta B recibe 404 al consultar pago de A | Dos sesiones reales |
| Gratis | Activación explícita, sin pago ni renovación | Conforme | API y navegador reales |
| Archivo de QA | Carga, PNG visible, descarga, papelera, restauración | Conforme, sin tocar archivos ajenos | Django y MinIO reales |
| Filtro de fechas inválido | Error de campo y foco | Conforme | Formulario real |
| Carga y vacío de historial | Mensajes claros, sin filas inventadas | Conforme | Respuestas controladas |
| Fallo de historial/suscripción | Error legible y recuperación | Reintento recupera los datos | Respuestas controladas |
| Catálogo sin alternativas | Estado vacío explícito | Conforme | Respuesta controlada |
| Cuota incompatible | Mostrar motivo, impedir checkout | Conforme | Respuesta controlada |
| Resumen vencido | Generar otro, sin botón de pago anterior | Conforme | Vencimiento corto controlado |
| Falla de correo de recuperación | Mostrar error sin afirmar envío | Conforme; no se envió correo durante esta prueba | Respuesta controlada |
| Teclado de carga | Tab dentro, Escape cierra y devuelve foco | Conforme | Modal real |

## Validación técnica

- 212 pruebas backend del código versionado aprobadas en Docker/PostgreSQL, sin omisiones; copia producida con git archive. No se incluyen las tres pruebas locales de almacenamiento sin seguimiento.
- 47 pruebas frontend aprobadas; lint global y build en Docker/Linux aprobados.
- manage.py check y makemigrations --check --dry-run sin incidencias. Este PR no añade migraciones ni dependencias.
- Capturas y métricas de anchura/errores JavaScript: evidence/miguel-validation-2026-10-29.json.

## Límites del cierre

La prueba visual del error de correo no acredita entrega a un buzón real. SMTP, recuperación/verificación real por correo, limpieza periódica y compensaciones de almacenamiento siguen su validación técnica con Cristian. Se comprobó el recorrido normal de archivos, no se sustituye su batería de fallos y concurrencia. Los datos nuevos pertenecen exclusivamente a QA; las credenciales y URLs firmadas no se versionan.

Los cuatro archivos locales de almacenamiento sin seguimiento se conservaron fuera del PR. La integración a develop requiere revisión de un compañero según la guía de Git; no se integra automáticamente. Este cierre corresponde a Miguel y no certifica despliegue público ni administración final.

## Evidencia visual seleccionada

Matriz de 20 pantallas/estados por dos temas y dos anchuras: 80 capturas revisadas, sin desbordamiento de página ni errores JavaScript. En checkout y vista previa se comprobó explícitamente que el formulario y la imagen terminaran de cargar. Se conservan estas capturas representativas:

| Pantalla | Claro / escritorio | Oscuro / móvil |
| --- | --- | --- |
| Mi suscripción | [Captura](evidence/miguel/subscription-light-desktop.png) | [Captura](evidence/miguel/subscription-dark-mobile.png) |
| Resumen de renovación | [Captura](evidence/miguel/renew-summary-light-desktop.png) | [Captura](evidence/miguel/renew-summary-dark-mobile.png) |
| Checkout | [Captura](evidence/miguel/checkout-light-desktop.png) | [Captura](evidence/miguel/checkout-dark-mobile.png) |
| Historial | [Captura](evidence/miguel/history-light-desktop.png) | [Captura](evidence/miguel/history-dark-mobile.png) |
| Resultado emergente | [Captura](evidence/miguel/result-light-desktop.png) | [Captura](evidence/miguel/result-dark-mobile.png) |
| Gestor de subidas | [Captura](evidence/miguel/upload-light-desktop.png) | [Captura](evidence/miguel/upload-dark-mobile.png) |
| Vista previa PNG | [Captura](evidence/miguel/file-preview-light-desktop.png) | [Captura](evidence/miguel/file-preview-dark-mobile.png) |

Estados: [selección pendiente](evidence/miguel/pending-selection.png), [rechazo conservado](evidence/miguel/rejected-detail.png), [renovación bloqueada](evidence/miguel/renew-blocked.png), [fechas inválidas](evidence/miguel/invalid-date.png), [error del historial](evidence/miguel/history-error.png), [resumen vencido](evidence/miguel/expired-quote.png) y [conflicto al confirmar](evidence/miguel/conflict-summary.png).

Contraste medido de los tokens sobre sus fondos: acción primaria 5,70:1 en claro y 7,06:1 en oscuro; peligro 4,70:1 y 5,94:1. Esto verifica esos pares de colores; no se presenta como certificación completa WCAG.
