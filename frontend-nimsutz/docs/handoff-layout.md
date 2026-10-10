# Integración del frontend: acceso, perfil y planes

## Estado de esta entrega

Rama: feature/e2-acceso-planes. Solo frontend; no agrega modelos, migraciones ni reglas comerciales al backend.
La base revisada de Cristian entrega session/login/logout y roles/estados (C1).
Registro, verificación, recuperación, catálogo, cobertura y overview todavía no están en esta copia del backend.
Las pantallas llaman a los contratos propuestos abajo: requieren acuerdo e integración con sus responsables antes de completar el flujo real.
Un 404/405/501/503 muestra indisponibilidad; nunca se transforma en registro, correo enviado, plan activado o consumo ficticio.

## Recorrido y responsabilidades

- /register: nombre completo, correo, contraseña y confirmación. Validación visual, errores de servidor por campo, carga y protección contra doble envío. No solicita tarjeta ni plan.
- Registro exitoso conserva cuenta pendiente. Solo indica correo enviado si email_sent es true. La pantalla completa de verificación/reenvío es de Rodrigo; recuperación y correo son de Miguel.
- /login conserva la sesión Django y CSRF, utiliza la cuenta real y muestra errores legibles. No impone ocho caracteres al login de cuentas ya existentes.
- /plans: catálogo autenticado del servidor. /plans/summary: confirmación de condiciones vigentes. Gratis requiere confirmación explícita; los planes pagados no ejecutan pagos.
- La landing mantiene su diseño y precios publicitarios anteriores. Antes de guardar una preferencia consulta el catálogo actual. Guarda únicamente version_id en sessionStorage, nunca precios ni credenciales. Si el catálogo no existe aún, explica la indisponibilidad.
- La selección de la landing no concede cobertura. Registro envía preferred_plan_version_id al servicio de Rodrigo. La preferencia se elimina del navegador solo si el backend confirma preference_saved; en sesión, el resumen usa PUT idempotente para asociarla a la cuenta. Otra pestaña sin preferencia local consulta la persistida, no la borra.
- Logout exitoso limpia la preferencia temporal. No se comparten preferencias privadas entre cuentas.
- /profile mantiene nombre antes de @ y correo de la sesión. El plan/consumo demo se eliminaron. Overview fallido no significa Sin plan activo: ese estado solo se presenta si el servidor devuelve subscription: null.
- Una suscripción vigente no se sustituye visitando planes. Cambios de plan y pagos están fuera de esta entrega.
- El explorador no se rediseña. RequireSession envía files/trash a planes si la sesión devuelve ese destino. Con C1, sin next, conserva el acceso anterior. El control definitivo de cuota y cobertura del backend es pendiente de Miguel.

## Contratos propuestos pendientes de integrar

Concentrados en src/shared/api/accountApi.js; no son evidencia de endpoints ya disponibles.
Conservar apiRequest, cookies y X-CSRFToken. No JWT, credenciales persistidas ni otro cliente HTTP.

Session/login existentes: { user: { id, email, name, role, account_status, email_verified }, csrfToken }.
Ampliación propuesta: next = files | plans | plan_summary | admin. Los valores se traducen a rutas internas; nunca se utiliza una URL arbitraria enviada por el servidor. admin abre /profile hasta contar con una pantalla administrativa (sin simular backoffice).

POST /api/auth/register/
Entrada: { name, email, password, password_confirmation, preferred_plan_version_id? }
Salida: { status: "pending_verification", email_sent: true|false, preference_saved: true|false }
No debe iniciar sesión ni activar cobertura. El backend vuelve a validar contraseñas, identidad y unicidad; no acepta rol o estado desde el formulario.
Si el correo falla, conservar la cuenta pendiente y reportar email_sent: false. Rodrigo conectará su verificación/reenvío sin duplicar estas pantallas.

GET /api/plans/
Salida: { plans: [{ code: "gratis", version_id: "gratis-v1", name: "Gratis", price: "0.00", currency: "GTQ", period: null, capacity_bytes: 104857600, available: true }] }
Códigos propuestos: gratis, basico, premium. version_id cambia cuando cambian condiciones. price decimal en texto, capacity_bytes entero. period es etiqueta legible del servidor (ej. "mes"). available indica contratación habilitada.
El tamaño de ejemplo usa 100 * 1024 * 1024; confirmar esa convención con Cristian/Miguel antes de integrar. La interfaz muestra bytes / 1024 / 1024 y no establece cuotas.
Los planes de pago pueden aparecer con available: false. Aunque cambie ese indicador, no hay pasarela implementada en esta entrega.

GET /api/subscriptions/preference/
Salida: { preferred_plan_version_id: "gratis-v1" | null }
PUT al mismo endpoint: { preferred_plan_version_id: "gratis-v1" }; éxito 2xx, idempotente, validación del servidor.
Registro usa el mismo servicio de preferencia para conservarla al abrir la verificación en otra pestaña/dispositivo.

GET /api/subscriptions/current/
Salida sin cobertura: { subscription: null }
Con cobertura efectiva: { subscription: { plan: { version_id: "gratis-v1", name: "Gratis" } } }
No devolver preferencia o historial vencido como cobertura efectiva.

POST /api/subscriptions/activate-free/
Entrada: { plan_version_id: "gratis-v1" }
Salida: mismo contrato de current con subscription vigente.
El backend debe autenticar/verificar, validar versión y gratuidad y garantizar activación idempotente/atómica; nunca reemplazar cobertura existente de forma incompatible. Una versión caducada devuelve 409 para recargar y exigir nueva revisión, sin aceptar silenciosamente otras condiciones.

GET /api/account/overview/
Salida: { subscription: null } o { subscription: { plan: { version_id: "gratis-v1", name: "Gratis" } }, storage: { used_bytes: 26214400, capacity_bytes: 104857600 } }
used_bytes debe reflejar cuota ocupada según el servicio compartido (incluyendo papelera y reservas cuando corresponda). No calcularlo otra vez en accounts ni sumar registros en el frontend. Las identidades se leen de session, no del ejemplo de overview.

Errores: HTTP correspondiente y { detail: "Mensaje", code: "codigo_estable", field_errors: { email: ["Mensaje"] } }. También se soportan los errores DRF con campos en la raíz. La interfaz no imprime respuestas HTML, tokens ni trazas.

## Validación y ejecución

Desde frontend-nimsutz:

    npm run build
    npx --no-install eslint src/pages/RegisterPage.jsx src/pages/LoginPage.jsx src/pages/PlansPage.jsx src/pages/ProfilePage.jsx src/pages/landing/PlansSection.jsx src/shared/auth/accessFlow.js src/shared/auth/AuthProvider.jsx src/shared/auth/RequireSession.jsx src/shared/api/accountApi.js src/shared/api/httpClient.js src/layouts/Header.jsx src/layouts/PublicLayout.jsx src/router/AppRouter.jsx
    node --test src/shared/auth/accessFlow.test.mjs

Las pruebas de Node usan respuestas controladas para verificar contratos, errores, CSRF, preferencia y navegación. No sustituyen pruebas de integración del backend ni envían correos.

Lista manual antes del PR:
- Registro vacío, contraseña corta/no coincidente, correo duplicado del servidor y fallo de envío.
- Login Ana/Beto, perfil correcto, logout, recarga y acceso directo sin sesión.
- Tema claro/oscuro, foco por teclado y mensajes legibles.
- API ausente muestra error recuperable sin inventar datos.
- Con backend completo: preferencia desde landing -> registro -> verificación -> login -> resumen -> confirmación Gratis -> archivos.
- Cambio de versión y 409 obligan a revisar de nuevo; doble envío no duplica activación en servidor.
- Cuenta con cobertura no pierde plan por abrir landing/resumen. Cuenta sin cobertura no puede escribir en files (prueba de backend de Miguel).
- Perfil diferencia sin plan, fallo de consulta, consumo real y cuota sobrepasada.

No hacer push directo a develop/main. Revisar el PR con el responsable del contrato. No borrar volúmenes ni modificar código de otros módulos para completar las APIs pendientes.

## Comprobaciones realizadas en esta rama

- Build de producción y ESLint de archivos modificados: correctos. Ocho pruebas de Node: correctas.
- Navegador contra backend local: login de Ana, explorador, perfil con nombre/correo correctos, aviso por API comercial ausente, catálogo informativo y cierre de sesión.
- Registro: validación de campos vacíos y foco en el primer campo inválido.
- Navegador contra respuestas controladas aisladas (sin PostgreSQL): resumen Gratis, confirmación explícita, cobertura activa y perfil 25/100 MB; tema oscuro. Esto verifica el frontend contra el contrato propuesto, no la implementación real de suscripciones.
- Pendiente: registro/verificación/correo y suscripciones de extremo a extremo con las implementaciones del equipo, además de revisión cruzada.

El catálogo informativo comparte PLAN_INFORMATION con la landing: no duplica precios ni se utiliza para conceder activaciones o cuotas.

## Ajuste visual de acceso según mockups

Login y registro comparten AuthLayout: tarjeta centrada, selector de tema y regreso al inicio. PublicLayout sigue reservado para landing/about; no se duplica su navegación dentro de los formularios.
Login reutiliza Brand con logo sin nombre adicional. Input admite icono inicial y acción final opcionales; PasswordInput compone Input para mostrar/ocultar la contraseña con un botón accesible. Los consumidores anteriores de Input conservan sus propiedades.
Registro mantiene únicamente nombre completo, correo, contraseña y confirmación, sin planes/tarjetas ni botones para simular estados. Se conserva toda la validación y el contrato de registro.
Olvidé mi contraseña muestra un aviso de disponibilidad pendiente hasta integrar la pantalla de Miguel. No apunta a una ruta inexistente.

## Contraseña y salida de planes

Registro muestra en vivo longitud mínima de ocho caracteres y que no sea solo numérica. No exige mayúsculas/símbolos: no son reglas actuales. Confirmación vuelve a compararse cuando cambia cualquiera de los dos campos; indica coincidencia o diferencia y limpia errores anteriores del campo al editar.
Contraseñas comunes y similitud con datos del usuario se delegan al backend. AUTH_PASSWORD_VALIDATORS está configurado, pero create_user/set_password no lo ejecutan automáticamente: Rodrigo debe invocar validate_password(password, user) en el alta y Miguel en recuperación; acordar user_attributes para incluir el campo personalizado name además del correo. La lista visual no afirma que la contraseña haya pasado estas comprobaciones del servidor.

El flujo acordado mantiene la preferencia desde landing. Con sesión válida va al resumen; sin sesión no se puede saber si ya tiene cuenta, por lo que registro ofrece Ya tengo cuenta hacia login conservando preferencia. Cuenta nueva: registro -> verificación -> login -> resumen. Cambiar selección vuelve al catálogo sin activar nada; Salir sin confirmar vuelve a inicio y conserva la preferencia para retomarla, no crea suscripción ni cobro. El botón de salida espera mientras hay una petición de activación en curso.
Los pagos siguen pendientes; una cuenta con un plan activo necesita el flujo comercial de cambio de plan (fuera de la primera contratación), no llamar activate-free para reemplazarlo.

## Corrección: botones de la landing sin dependencia del catálogo

La landing ahora guarda inmediatamente solo el código público (gratis/basico/premium) en sessionStorage y navega a registro o resumen según la sesión. No consulta GET /api/plans/ antes de redirigir. Esta intención sustituye a una selección temporal anterior, no concede cobertura y no inventa version_id.
El resumen resuelve el código contra el catálogo del servidor cuando esté disponible, guarda la versión validada y exige confirmar sus condiciones. Mientras falta la API muestra el plan informativo elegido, permite cambiarlo o salir, sin activar ni cobrar. Logout elimina tanto el código temporal como la versión temporal.
Este ajuste reemplaza la descripción anterior que exigía resolver el catálogo en la landing. La continuidad en el mismo navegador está preparada; persistir una intención sin versión durante registro para otro dispositivo requiere acordar esa entrada con Rodrigo/Cristian. Nunca enviar el código como si fuera preferred_plan_version_id.


## Integración con subscriptions — 10 de octubre de 2026

Esta sección sustituye las suposiciones de contratos de suscripciones de las notas anteriores.

- accountApi adapta plan_code (free/basic/premium) a los identificadores de la landing; contractable controla disponibilidad y duration_days se muestra sin inventar periodicidad.
- GET preference devuelve {preference: null|{version_id,is_current,...}}; PUT envía plan_version_id. Una versión vencida exige seleccionar nuevamente.
- Overview devuelve coverage, usage y destination. Se adapta a las pantallas existentes; una respuesta incompleta produce error, nunca Sin plan activo.
- La sesión consulta overview para obtener el destino mientras login/session no lo incluyen. Cobertura activa permite volver a archivos aunque exista intención local. No sustituye permisos del backend.
- La preferencia local solo se limpia después de guardarla en el endpoint autenticado. El registro actual declara preference_saved sin persistirla, por eso no se utiliza esa bandera para borrarla. Continuidad entre dispositivos sigue pendiente del backend.
- Antes de activar Gratis se reconsulta la versión y capacidad del catálogo. El backend aún ignora plan_version_id en activate-free: debe validarlo de forma atómica para cubrir cambios concurrentes entre consulta y activación.

Verificación: build y ESLint de archivos modificados; pruebas Node del contrato y navegación. Navegador contra API local: Premium desde landing -> registro -> login Ana -> resumen Premium; cambio a Gratis -> activación -> perfil con 100 MB -> recarga -> archivos. La cuenta local ana@nimsutz.local quedó con Gratis activo durante la prueba. No se modificó código backend.

Pendientes externos: cuota de cargas sigue simulada, falta release_expired_uploads, entrega de correo y registro/verificación completos no se validaron en este cambio. No declarar cerrado el recorrido completo de usuarios y archivos.
