# Flujo de trabajo — Nim Sutz'

## Estrategia de ramas

```
main                    ← producción / entrega de sprint, siempre estable
 └─ develop             ← integración del equipo, aquí se juntan los módulos
     ├─ feature/e1-usuarios
     ├─ feature/e2-suscripciones
     ├─ feature/e3-archivos
     └─ feature/e4-admin
```

- `main`: protegida, nadie hace push directo. Solo recibe merges desde `develop`
  cuando el sprint está cerrado y probado.
- `develop`: rama de integración. Todos mergean aquí primero, vía Pull Request.
- `feature/<modulo>`: una por responsable. Se crea desde `develop`, se actualiza
  seguido con `develop` (no con `main`) para evitar divergir demasiado.

## Convención de nombres

| Tipo                | Formato                       | Ejemplo                         |
| ------------------- | ----------------------------- | ------------------------------- |
| Módulo              | `feature/e{n}-{nombre-corto}` | `feature/e3-archivos`           |
| Corrección puntual  | `fix/{descripcion-corta}`     | `fix/cors-minio`                |
| Ajuste no funcional | `chore/{descripcion-corta}`   | `chore/actualizar-dependencias` |

## Regla clave para evitar choques: una app de Django por módulo

Cada responsable trabaja dentro de su propia app (`users`, `subscriptions`, `files`,
`adminpanel`). Esto es lo que realmente evita que las migraciones choquen entre
personas — cada app tiene su propia carpeta `migrations/`, independiente de las
demás.

Los únicos archivos verdaderamente compartidos son:

- `config/settings.py` (o donde tengan `INSTALLED_APPS`)
- `config/urls.py` (raíz de rutas)
- `requirements.txt`

**Regla para estos tres archivos:** cambios ahí van en commits pequeños y
aislados (no mezclados con el resto de la lógica del módulo), para que un PR que
solo agrega `"files"` a `INSTALLED_APPS` sea trivial de revisar y de resolver si
hay conflicto.

## Flujo de trabajo

1. Actualizar `develop` local antes de empezar:
   ```bash
   git checkout develop
   git pull origin develop
   ```
2. Crear (o continuar) tu rama de módulo:
   ```bash
   git checkout -b feature/e3-archivos   # solo la primera vez
   ```
3. Traer cambios recientes de `develop` seguido, para no acumular conflictos:
   ```bash
   git checkout feature/e3-archivos
   git merge develop
   ```
4. Al terminar una parte funcional del módulo (no al final del sprint completo),
   abrir un Pull Request hacia `develop` — PRs pequeños y frecuentes, no uno gigante
   al final.
5. Al menos un compañero revisa el PR antes de mergear a `develop`.
6. Al cerrar el sprint, se abre un PR de `develop` → `main`.

## Checklist antes de abrir un PR

- [ ] `python manage.py makemigrations --check` no reporta migraciones faltantes
- [ ] El servidor levanta sin errores con `docker compose up`
- [ ] No se tocó `INSTALLED_APPS` ni `urls.py` en el mismo commit que lógica de
      negocio (van aparte)
- [ ] Variables de entorno nuevas están documentadas en `.env.example`, no solo en
      tu `.env` local

## Convención de commits

Formato libre, pero con prefijo por tipo de cambio, para que el historial sea
legible entre los cuatro:

```
feat(files): endpoint de solicitud de carga con reserva de cuota
fix(files): CORS de MinIO no permitía PUT desde localhost
chore(files): agregar boto3 a requirements.txt
```
