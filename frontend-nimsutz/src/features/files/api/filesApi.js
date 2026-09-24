/*  Llamadas HTTP crudas. Sin estado ni logica de UI.

    Alcance de A (Miguel): organización de carpetas y LECTURA del listado
    de archivos para mostrarlo en el explorador. Subir, descargar,
    enviar a papelera, restaurar y eliminar definitivamente son
    operaciones de B (Rodrigo, src/features/files/transfers y trash) y
    no se implementan aquí, según el contrato mínimo A-B.

    El equipo agregó sesión real (login/CSRF) en develop (PR
    "feature/demo-login"). Los endpoints de /api/folders/ y /api/files/
    exigen sesión iniciada (files/auth.py usa SessionAuthentication).
    Por eso aquí se usa apiRequest de @shared/api/httpClient en vez de
    un fetch propio: reutiliza la cookie de sesión y el token CSRF que
    ya maneja AuthProvider (DRY, y el contrato pide reutilizar el
    cliente HTTP existente).

    Endpoints existentes en el backend (rama develop, files/urls.py):
      GET    /api/folders/                (SIN "parent": todas las carpetas del usuario, útil para el breadcrumb)
      GET    /api/folders/?parent=root|<id>
      POST   /api/folders/
      PATCH  /api/folders/<id>/           (solo renombra, no mueve)
      DELETE /api/folders/<id>/           (falla si no está vacía)
      GET    /api/files/?folder=<id>&status=available   (solo lectura, para el listado)

    IMPORTANTE: no existe ningún endpoint para mover una carpeta o un
    archivo a otra ubicación (PATCH de carpeta solo acepta "name"). Esta
    función NO se implementa a propósito: es un endpoint pendiente que
    hay que pedirle al equipo de backend, tal como indica la consigna
    ("las funciones ausentes... se registran para su resolución, sin
    crear un backend paralelo"). Ver moveFolder mas abajo. */

import { apiRequest } from '@shared/api/httpClient';

/** Error compatible con el que lanza apiRequest (tiene .status). */
export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

function jsonBody(body) {
    return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ---------- Folders (propiedad de A) ----------

/** Lista carpetas hijas de "parentId". Usa "root" para el nivel superior. */
export function listFolders(parentId) {
    const parentParam = parentId == null ? 'root' : parentId;
    return apiRequest(`/api/folders/?parent=${encodeURIComponent(parentParam)}`);
}

/**
 * Lista TODAS las carpetas del usuario (sin filtrar por parent). El
 * backend, al no recibir "parent", no filtra. Se usa solo para
 * reconstruir la ruta de migas de pan a partir del campo "parent" de
 * cada carpeta, sin depender del historial de clics del usuario.
 */
export function listAllFolders() {
    return apiRequest('/api/folders/');
}

export function createFolder({ parent, name }) {
    return apiRequest('/api/folders/', { method: 'POST', ...jsonBody({ parent, name }) });
}

export function renameFolder(id, name) {
    return apiRequest(`/api/folders/${id}/`, { method: 'PATCH', ...jsonBody({ name }) });
}

export function deleteFolder(id) {
    return apiRequest(`/api/folders/${id}/`, { method: 'DELETE' });
}

/** PENDIENTE: no existe endpoint de backend para mover una carpeta o archivo. */
export function moveFolder() {
    throw new ApiError(
        'Mover carpetas todavía no está soportado por el backend (falta el endpoint).',
        501,
    );
}

// ---------- Files: SOLO lectura para el listado (propiedad de A) ----------
// Subir, descargar, papelera, restaurar y eliminar definitivo son de B.

export function listFiles(folderId) {
    const params = new URLSearchParams({ status: 'available' });
    if (folderId != null) params.set('folder', folderId);
    return apiRequest(`/api/files/?${params.toString()}`);
}
