# Contratos Fase 1: Registro y Verificación

Este documento define la estructura exacta de las peticiones y respuestas para los endpoints de registro y verificación, asegurando que el equipo (Frontend y Backend) trabaje sobre la misma base.

## 1. Endpoints de Autenticación (accounts/urls.py)

### 1.1 Registro Público
**POST** `/api/auth/register/`
Crea una cuenta con rol `cliente` en estado `pendiente_verificacion`. No otorga sesión automática.

**Request Body:**
```json
{
  "name": "Juan Pérez",
  "email": "juan.perez@example.com",
  "password": "Password123",
  "password_confirmation": "Password123",
  "preferred_plan_version_id": 4  // (Opcional) Id de la versión del plan que prefirió en la landing
}
```

**Response (201 Created):**
```json
{
  "id": 105,
  "email": "juan.perez@example.com",
  "name": "Juan Pérez",
  "account_status": "pendiente_verificacion"
}
```

**Response de Errores Comunes (400 Bad Request):**
```json
{
  "code": "validation_error",
  "detail": "Datos inválidos",
  "field_errors": {
    "email": ["El correo ingresado ya se encuentra en uso."],
    "password": ["La contraseña debe tener al menos 8 caracteres."]
  }
}
```

### 1.2 Verificación de Correo
**POST** `/api/auth/verify-email/`
Valida el token enviado por correo y pasa la cuenta a estado `activa`. No otorga sesión.

**Request Body:**
```json
{
  "token": "d7a8f9s8d7f..." 
}
```

**Response (200 OK):**
```json
{
  "detail": "Correo verificado exitosamente."
}
```

**Response de Error (400 Bad Request):**
```json
{
  "code": "invalid_token", // Posibles valores: "invalid_token", "expired_token", "used_token"
  "detail": "El enlace de verificación es inválido o ya expiró."
}
```

### 1.3 Reenvío de Verificación
**POST** `/api/auth/resend-verification/`
Genera un nuevo token e invalida el anterior. 

**Request Body:**
```json
{
  "email": "juan.perez@example.com"
}
```

**Response (200 OK):**
```json
{
  "detail": "Si el correo está registrado y pendiente, se ha enviado un nuevo enlace."
}
```

---

## 2. Contrato de Servicio (Firma para Miguel)

Para el envío de correos, Miguel nos entregará la siguiente función en `accounts/services.py` o módulo equivalente:

```python
def send_verification_email(user_email: str, user_name: str, verification_link: str) -> None:
    """
    Envía el correo con la plantilla de verificación.
    Lanza una excepción específica si falla el proveedor, para que 
    el endpoint de registro o reenvío no muestre éxito si el correo no salió.
    """
    pass
```

---

## 3. Estado del Modelo (Acuerdo con Cristian)

Revisando el código base (`accounts/models.py`), el modelo ya cumple con el contrato:
- `username` eliminado, se usa `email`.
- `first_name` y `last_name` eliminados, unificado en `name`.
- `role`: "cliente" / "administrador".
- `account_status`: "pendiente_verificacion" / "activa" / "suspendida".
- Propiedad `can_use_private_features`: Sólo verdadera si `email_verified` y status `activa`.

---

## 4. Próximos Pasos de Integración

Con estos contratos, podemos proceder a:
1. **Rodrigo (Backend):** Implementar la vista y serializer para `register/`, generar tokens y armar el endpoint `verify-email/`.
2. **Daniela (Frontend):** Configurar sus peticiones `fetch` usando estas firmas exactas para su formulario de registro y preparar la conexión a la pantalla M02.
3. **Miguel (Correo):** Desarrollar internamente `send_verification_email`.

