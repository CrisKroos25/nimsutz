# Instrucciones de Integración - Módulo de Transferencias (Integrante B)

Este documento explica cómo el Integrante A (Explorador) debe montar y utilizar los componentes de Transferencias y Papelera.

## 1. UploadPanel (Panel de Carga)
Componente para subir archivos. Debe montarse en la cabecera o barra de acciones del explorador.

**Props requeridas:**
- `folderId`: ID de la carpeta actual donde se subirá el archivo (enviar `null` si es la raíz).
- `onCompleted`: Función callback que debes pasarle para recargar tu listado de archivos cuando una subida termine con éxito.

**Ejemplo de uso:**
```jsx
import UploadPanel from '../transfers/components/UploadPanel/UploadPanel';

// Dentro de tu componente Explorador:
<UploadPanel 
    folderId={currentFolderId} 
    onCompleted={recargarListado} 
/>
```

## 2. FileActions (Menú de Acciones por Archivo)
Menú desplegable (tres puntos) que debe ir en cada fila de tu listado de archivos. Contiene las opciones de "Descargar" y "Mover a Papelera".

**Props requeridas:**
- `file`: El objeto completo del archivo tal como viene de la API.
- `onChanged`: Función callback para recargar tu listado cuando un archivo sea enviado a la papelera.

**Ejemplo de uso:**
```jsx
import FileActions from '../transfers/components/FileActions/FileActions';

// En el renderizado de tu tabla/grid, por cada archivo:
<FileActions 
    file={archivo} 
    onChanged={recargarListado} 
/>
```

## 3. Trash (Página de Papelera)
Es una página 100% autónoma. Solo necesitas montarla en el router en la ruta `/trash`. No requiere props, ya que gestiona su propio estado y peticiones.

**Ejemplo de uso (AppRouter.jsx):**
```jsx
import TrashPage from '../features/files/transfers/components/TrashView/Trash';

<Route path="/trash" element={<TrashPage />} />
```

## Notas para pruebas
1. Asegúrate de tener el backend de Django corriendo y haber ejecutado las migraciones.
2. El sistema requiere que estés autenticado para que funcione (las peticiones usan la sesión).
3. Para probar descargas reales y subidas, asegúrate de que el contenedor de MinIO esté activo.
