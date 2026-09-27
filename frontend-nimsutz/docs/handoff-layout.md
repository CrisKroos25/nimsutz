# Integración de A, B y C

C entrega la landing, /about, /login y la sesión de prueba. A sustituye StoragePreviewPage por el explorador en /files; B entrega la vista /trash. Ambas rutas deben permanecer dentro de RequireSession en AppRouter. El catálogo /design-system sigue público.

## Sesión y peticiones

- AuthProvider restaura la sesión con GET /api/auth/session/. useAuth() expone user, loading, error, refresh, signIn y signOut.
- POST /api/auth/login/ valida correo y contraseña contra la cuenta de prueba configurada en Django. POST /api/auth/logout/ cierra la sesión.
- La API de archivos requiere una sesión: ya no asigna automáticamente el usuario a solicitudes anónimas. Mantiene los filtros por propietario existentes.
- A y B deben importar apiRequest desde src/shared/api/httpClient.js y usar rutas relativas /api/. El cliente envía la cookie y el token CSRF en escrituras. Para JSON, pasar Content-Type y JSON.stringify en body. Para FormData, no fijar Content-Type.
- Ante un 403, comprobar la sesión con refresh(): también puede indicar un error CSRF o de permisos; no asumir que todos los 403 son una contraseña incorrecta.
- Las transferencias a URLs firmadas de MinIO usan fetch directo con el método y encabezados indicados por el backend, sin cookie ni token CSRF de Django.

## Desarrollo

Vite redirige /api al backend local :8000. En Compose usa API_PROXY_TARGET=http://backend:8000. Reiniciar Vite tras integrar la configuración; si se usa Compose, ejecutar docker compose up -d --build frontend backend. No se añadieron dependencias.

Crear la cuenta local una sola vez con docker compose exec backend python manage.py create_demo_user --email CORREO. La contraseña se solicita de forma oculta; no guardar credenciales en código ni Git. El registro no está habilitado. El login admite únicamente SIMULATED_USER_ID y no implementa contratación ni verificación de correo.

## Verificación y revisión

Ejecutar docker compose exec backend python manage.py test accounts y los scripts lint/build del frontend. Probar login correcto e incorrecto, recarga, cierre de sesión y acceso directo a /files sin sesión. A y B prueban sus flujos después de integrar apiRequest.

Entregar mediante PR a develop con revisión del equipo. Separar los cambios de configuración compartida (settings.py, urls.py, vite.config.js, docker-compose.yml) de la lógica en los commits. No reemplazar el trabajo del explorador ni la papelera al integrar.
