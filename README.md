# Nimsutz — Entorno de Desarrollo Local con Docker

Este proyecto corre completamente en contenedores Docker: Frontend (React/Vite), Backend (Django REST Framework), PostgreSQL y MinIO. No necesitas instalar Python, Node, PostgreSQL ni MinIO en tu máquina — solo Docker.

---

## Requisitos previos

- **Docker Desktop** instalado y corriendo ([docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)).
- Git.
- **Importante:** clona el proyecto en una ruta **fuera de OneDrive/Google Drive/Dropbox** (por ejemplo `C:\dev\nimsutz` en Windows, o `~/dev/nimsutz` en Mac/Linux). Carpetas sincronizadas en la nube pueden causar errores intermitentes al montar volúmenes de Docker.

---

## Primera vez levantando el proyecto (hazlo en este orden)

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd nimsutz
```

### 2. Crear tu archivo de variables de entorno

```bash
cp .env.example .env
```

**Por qué es necesario:** Docker Compose lee las credenciales y configuración desde `.env` — sin este archivo, los contenedores no van a tener los valores que necesitan para conectarse entre sí.

### 3. Construir y levantar todos los contenedores

```bash
docker compose up --build
```

Esto va a levantar 4 contenedores: `backend`, `frontend`, `db`, `minio`. Déjalo corriendo en esta terminal y abre una **segunda terminal** para los siguientes pasos (los contenedores deben seguir corriendo mientras ejecutas los comandos de abajo).

### 4. Aplicar las migraciones de la base de datos

En la segunda terminal:

```bash
docker compose exec backend python manage.py migrate
```

**Por qué es necesario:** la base de datos empieza completamente vacía (sin tablas) la primera vez. Este comando crea todas las tablas que Django necesita.

### 5. Crear tu superusuario (para entrar al admin de Django)

```bash
docker compose exec backend python manage.py createsuperuser
```

### 5.1 O crear un usuario temporal
```bash
docker compose exec backend python manage.py create_demo_user --email usuario@email.com
```

Sigue las instrucciones en pantalla (usuario, correo, contraseña).
Es el mismo que usara luego para loguearse.

### 6. Crear el bucket de MinIO

```bash
docker compose exec backend python crear_bucket.py
```

**Por qué es necesario:** el volumen de MinIO empieza vacío — este script crea el bucket `nimsutz-storage` donde se guardarán los archivos.

### 7. Verificar que todo esté funcionando

| Servicio         | URL                          | Qué deberías ver                                 |
| ---------------- | ---------------------------- | ------------------------------------------------ |
| Frontend         | http://localhost:5173        | La app de React                                  |
| Backend (API)    | http://localhost:8000        | Página de bienvenida de Django                   |
| Admin de Django  | http://localhost:8000/admin/ | Login con el superusuario que creaste            |
| Consola de MinIO | http://localhost:9001        | Login con `nimsutz_admin` / `nimsutz_admin_pass` |

### 8. Correr script de prueba para carga, descarga y papelera

```bash
bash smoke_test_files.sh
```

Ingresa con el usuario creado anteriormente.

---

## Uso diario (después de la primera vez)

Para trabajar en el día a día, normalmente solo necesitas:

```bash
docker compose up
```

(sin `--build`, a menos que hayas cambiado el `Dockerfile` o `requirements.txt`/`package.json` — en ese caso sí usa `--build`).

Para detener todo:

```bash
docker compose down
```

Esto detiene los contenedores **sin borrar** la base de datos ni los archivos de MinIO (esos viven en volúmenes persistentes).

---

## Comandos útiles

| Comando                                                     | Qué hace                                                                                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `docker compose ps`                                         | Ver qué contenedores están corriendo                                                                                           |
| `docker compose logs backend`                               | Ver los logs del backend (o cambia `backend` por `frontend`, `db`, `minio`)                                                    |
| `docker compose logs -f backend`                            | Ver los logs en tiempo real (`-f` de "follow")                                                                                 |
| `docker compose exec backend python manage.py <comando>`    | Correr cualquier comando de Django dentro del contenedor (ej. `makemigrations`, `shell`)                                       |
| `docker compose exec db psql -U nimsutz_user -d nimsutz_db` | Entrar directo a la base de datos por consola                                                                                  |
| `docker compose down -v`                                    | Detener todo **y borrar los volúmenes** (pierdes la BD y los archivos de MinIO — usar solo si quieren empezar 100% desde cero) |

---

## Estructura del proyecto

```
nimsutz/
├── docker-compose.yml
├── backend-nimsutz/       ← Django REST Framework
│   ├── Dockerfile
│   ├── manage.py
│   └── ...
└── frontend-nimsutz/      ← React + Vite
    ├── Dockerfile
    ├── package.json
    └── ...
```

---

## Cuando alguien agrega una dependencia nueva

**Backend (nueva librería de Python):**

1. Instálala dentro del contenedor o en tu entorno local y actualiza `requirements.txt`.
2. Avisa al equipo — quien haga `git pull` debe correr `docker compose up --build backend` para que la nueva dependencia se instale en la imagen.

**Frontend (nuevo paquete de npm):**

1. `docker compose exec frontend npm install <paquete>` (esto actualiza `package.json` dentro del contenedor, reflejado en tu carpeta local gracias al volumen).
2. Avisa al equipo — igual necesitan `docker compose up --build frontend`.

**Nueva migración de Django:**

1. `docker compose exec backend python manage.py makemigrations`
2. `docker compose exec backend python manage.py migrate`
3. Sube el archivo de migración generado (queda en `backend-nimsutz/<app>/migrations/`) — el resto del equipo solo necesita correr `migrate` tras hacer `git pull`, no `makemigrations`.

---

## Problemas comunes

| Síntoma                                                                            | Causa probable / Solución                                                                                                                                                  |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `connection refused` al abrir localhost:8000 o :5173                               | El contenedor correspondiente no llegó a levantar. Corre `docker compose ps` para ver su estado y `docker compose logs <servicio>` para ver el error                       |
| `relation "django_session" does not exist` o errores similares de tablas faltantes | Faltó correr `migrate` (paso 3) — común la primera vez o después de un `down -v`                                                                                           |
| Error 403/CORS al subir archivos desde el Frontend                                 | Revisar que `CORS_ALLOWED_ORIGINS` en `settings.py` incluya `http://localhost:5173`                                                                                        |
| Cambios en el código no se reflejan                                                | Verifica que el contenedor siga corriendo y que no haya que reconstruir la imagen (`--build`)                                                                              |
| Todo falla de forma rara e intermitente                                            | Si el proyecto está dentro de OneDrive/Google Drive, muévelo fuera de esa carpeta                                                                                          |
| `manage.py` o `package.json` "no encontrado" al hacer build                        | Verifica que estás corriendo `docker compose up` desde la raíz del proyecto (donde está `docker-compose.yml`), no desde dentro de `backend-nimsutz/` o `frontend-nimsutz/` |

---

## Correo electronico y cuota por cobertura (Etapa 5)

### Servicio de correo

Todo el correo sale por `backend-nimsutz/accounts/emails.py`, que expone dos funciones estables:

- `send_verification_email(user_email, user_name, verification_link)`: correo de verificacion de cuenta (token firmado, regla de Rodrigo).
- `send_password_reset_email(*, user, token)`: correo de recuperacion (token de un solo uso en base de datos, regla de Miguel).

Comparten solo el transporte (`_send`); las reglas de cada token no se mezclan. Si el proveedor falla se registra en el log (`accounts.emails`) y se lanza `EmailDeliveryError`. El registro responde `email_sent: false`; el reenvio de verificacion y la solicitud de recuperacion siguen dando su respuesta generica.

Variables de entorno (en `.env`; todas tienen valor por defecto en `docker-compose.yml`):

| Variable | Para que sirve | Defecto |
|---|---|---|
| `DEFAULT_FROM_EMAIL` | Remitente de los correos | `no-reply@nimsutz.local` |
| `FRONTEND_URL` | URL base de los enlaces de verificacion y recuperacion. La verificacion no usa el encabezado `Origin`. | `http://localhost:5173` |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | Vigencia del enlace de recuperacion | `30` |
| `EMAIL_VERIFICATION_TOKEN_TTL_MINUTES` | Vigencia del enlace de verificacion (el mensaje y el token usan este valor) | `1440` |

Por defecto el backend de correo es el de consola (`MAILERS` en `config/settings.py`): el mensaje aparece en `docker compose logs backend`. Para enviar correo real basta definir `EMAIL_HOST` en el `.env`; no se requiere cola ni infraestructura adicional. Variables SMTP (todas opcionales):

| Variable | Para que sirve | Defecto |
|---|---|---|
| `EMAIL_HOST` | Servidor SMTP. Vacio = correo a consola | vacio |
| `EMAIL_PORT` | Puerto | `587` |
| `EMAIL_USE_TLS` | STARTTLS | `true` |
| `EMAIL_HOST_USER` | Usuario SMTP | vacio |
| `EMAIL_HOST_PASSWORD` | Contrasena SMTP | vacio |
| `EMAIL_TIMEOUT` | Tiempo maximo de espera SMTP en segundos | `10` |

Ejemplo con Gmail (cuenta con verificacion en dos pasos y una contrasena de aplicacion): `EMAIL_HOST=smtp.gmail.com`, `EMAIL_HOST_USER=<cuenta>@gmail.com`, `EMAIL_HOST_PASSWORD=<contrasena de aplicacion>` y `DEFAULT_FROM_EMAIL=<la misma cuenta>`. Las credenciales viven solo en el `.env` local; nunca se suben al repositorio. Tras cambiar el `.env` hay que recrear el contenedor: `docker compose up -d --force-recreate backend`.

### Cuota de almacenamiento por cobertura

La capacidad de cada usuario sale de su suscripcion activa y vigente (`subscriptions.services.get_active_subscription`), no de una cuota global:

- Sin selección confirmada: capacidad 0; una selección pendiente no concede almacenamiento. Al terminar cobertura pagada se resuelve el siguiente ciclo anticipado o se retorna a Gratis.
- Plan Gratis: 100 MB. Los planes de pago toman la capacidad de su version contratada.
- Consumo = reservas pendientes + confirmadas del propietario, incluida la papelera. Solo el borrado definitivo libera espacio.
- Al volver a Gratis se conservan los archivos y su consumo. Si se exceden sus 100 MB, se bloquean carga y restauración; se permite consultar, descargar y eliminar.

Puntos de integracion en `files/services.py`: `get_capacity_bytes(owner)`, `get_used_bytes(owner)` y `get_available_quota(owner)`. `SIMULATED_QUOTA_BYTES` ya no interviene en el flujo normal.

Para probar subidas en local el usuario necesita cobertura:

```bash
docker compose exec backend python manage.py seed_plans
```

y luego activar el plan Gratis desde la aplicacion (`POST /api/subscriptions/activate-free/` o el flujo de planes). El usuario creado con `create_test_users` o `create_demo_user` no tiene cobertura por defecto.

Pruebas: `docker compose exec backend python manage.py test`.

Después de aplicar las migraciones, iniciar `docker compose up -d subscription_worker`: reconcilia las suscripciones cada 60 segundos, sin cobrar automáticamente. El backend también resuelve la cobertura al autorizar. La selección pendiente, el historial conservado y las bajadas que requieren pago manual se documentan en [el cierre de suscripciones](docs/subscriptions-rodrigo.md).

---

## Notas para la exposición / Manual Técnico

Este mismo flujo (`docker compose up --build` + migraciones + creación de bucket) es la base de cómo se documentará el despliegue en el Manual Técnico del proyecto — en producción, cada paso equivalente ocurre automáticamente o vía el proceso de deploy de Render/Vercel/Railway, pero la lógica de "construir imagen → aplicar migraciones → crear recursos iniciales" es la misma.
