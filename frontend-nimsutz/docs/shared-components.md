# Componentes compartidos

Catálogo compartido: Button, Input, Modal, Badge, Table y temas claro y oscuro. La página de demostración es temporal y no realiza operaciones de archivos ni autenticación.

## Button

Importar desde `src/shared/components/Button/Button.jsx`.

```jsx
<Button onClick={save}>Guardar</Button>
<Button variant="secondary">Ver detalles</Button>
<Button variant="danger" onClick={remove}>Eliminar</Button>
<Button variant="ghost">Cancelar</Button>
<Button type="submit" loading={saving} loadingLabel="Guardando…">Guardar</Button>
```

- Variantes: `primary` (predeterminada), `secondary`, `danger`, `ghost`.
- `disabled` y `loading` bloquean interacción. `loading` expone `aria-busy`.
- Por defecto `type="button"` evita envíos accidentales de formularios.
- Admite atributos nativos, eventos y `className`. Para botones sin texto, proporcionar `aria-label`.
- El componente no llama a la API ni incorpora reglas de negocio.

## Temas y diseño

`src/index.css` contiene las variables comunes. `data-theme="dark"` en el elemento HTML activa el tema oscuro. `useTheme` se usa una vez en la raíz de la página, recuerda la selección local y utiliza la preferencia del sistema al iniciar sin selección guardada.

La paleta y Poppins proceden del design system. Poppins se carga desde Google Fonts; sin conexión se utiliza sans-serif. Los colores de hover y el texto secundario oscuro completan estados no especificados. Los botones usan texto blanco para reproducir los mockups. Esto prioriza fidelidad visual; el contraste del blanco sobre naranja y rosa necesita revisión con el equipo antes de afirmar conformidad WCAG.

Usar variables y CSS Modules. Mantener responsabilidades separadas y archivos de código por debajo de 200 líneas cuando sea posible. No dividir archivos únicamente para reducir el contador. Badge y Table ya están disponibles; la integración con archivos reales sigue pendiente.

## Input y Modal

`Input` incluye label asociado por id, hint, error con aria-invalid y aria-describedby. Admite atributos nativos como required, disabled, name, value y onChange. No valida reglas del negocio: recibe el mensaje de error del módulo que lo usa.

`Modal` recibe open, onClose, title, description opcional, icon opcional y children. Usa dialog nativo: limita el foco al modal y deja el fondo inactivo. Escape solicita el cierre y al cerrar se devuelve el foco al disparador. El contenido debe incluir una acción Cancelar o Cerrar. No se cierra al pulsar el fondo, para evitar perder datos por accidente. Usar un modal a la vez.

Los ejemplos de creación y eliminación siguen M15 (página 57) y M16 (página 58) del documento de requisitos. Renombrar reutiliza el patrón de nombre. El usuario simulado y las llamadas al backend corresponden al módulo de almacenamiento, no a los componentes compartidos.

La validación del ejemplo solo comprueba nombres vacíos. La integración debe presentar también errores del servidor (nombre duplicado, permisos, etc.). Los botones de la demostración no ejecutan operaciones reales.

## Ajuste visual a M15 y M16

Se retiró el texto auxiliar añadido dentro de los modales. M15 usa el placeholder Informes 2027 y deshabilita Crear carpeta si el nombre está vacío. M16 incorpora el icono Trash2 de Lucide, el nombre de archivo destacado y la advertencia original. El aviso de simulación permanece fuera del modal. Las dimensiones se estiman del PDF, que contiene imágenes rasterizadas, no medidas de Figma.

## Badge y Table

Badge recibe tone (success, danger, warning, info o neutral) y children. El texto identifica el estado, sin depender solo del color. Los tonos de éxito y advertencia del tema claro se oscurecen para mejorar la lectura de etiquetas pequeñas.

Table recibe caption obligatorio, columns, rows, rowKey (nombre de campo o función; por defecto id), loading, error y emptyMessage. Cada columna tiene key, label y render(row) opcional. Las claves deben ser únicas y estables. El orden, filtro y las peticiones pertenecen al módulo consumidor. La tabla admite botones en render, desplazamiento horizontal por teclado y estados vacío, carga y error.

```jsx
const columns = [
    { key: 'name', label: 'Nombre' },
    {
        key: 'status',
        label: 'Estado',
        render: (file) => <Badge tone="success">{file.status}</Badge>,
    },
];
<Table caption="Mis archivos" columns={columns} rows={files} />;
```

## Estado de entrega y responsables

El commit del catálogo contiene los componentes, sus ejemplos y estilos globales. Abre el catálogo en la raíz. La landing, los layouts y el router son avances locales separados; requieren otro PR antes de que el equipo pueda usarlos.

- Integrante A: explorador, organización, MainLayout, Header, Sidebar, App.jsx y router.
- Integrante B: carga, descarga, papelera y conexión de sus operaciones a la API.
- Integrante C: landing, PublicLayout, shared, index.css y esta guía.

Los componentes compartidos reciben datos y acciones por props. No realizan llamadas HTTP ni implementan reglas de almacenamiento. A y B pueden desarrollar sus pantallas usando el catálogo sin esperar la landing.

## Uso de los componentes

Importar desde @shared/components/Button/Button y las carpetas equivalentes de Input, Modal, Badge y Table. Cargar index.css una sola vez. Mantener una sola instancia de useTheme en la raíz.

Table requiere rows como arreglo, columns con claves únicas y caption descriptivo. Modal requiere una acción visible de Cancelar o Cerrar dentro de children. Los formularios y las validaciones del negocio corresponden a la pantalla que consume Input.

## Dependencias y comprobaciones

El catálogo añade lucide-react. La base local de rutas también requiere react-router-dom; esa dependencia debe viajar con el PR del router. Mantener el manifiesto y el único lockfile acordado con Docker.

Ejecutar npm run lint y npm run build desde frontend-nimsutz. Cuando cambien dependencias, reconstruir con docker compose up -d --build desde la raíz y seguir el procedimiento del proyecto si el volumen de dependencias requiere actualización.

No se consideran completas las operaciones reales por mostrar sus ejemplos en el catálogo.
