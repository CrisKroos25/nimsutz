/*  Llamadas HTTP crudas. Sin estado ni logica de UI.

    Endpoints existentes en el backend (rama develop, files/urls.py):
      GET    /api/folders/                (SIN "parent": todas las carpetas del usuario, útil para el breadcrumb)
      GET    /api/folders/?parent=root|<id>
      POST   /api/folders/
      PATCH  /api/folders/<id>/           (solo renombra, no mueve)
      DELETE /api/folders/<id>/           (falla si no está vacía)
      GET    /api/files/?folder=<id>&status=available   (solo lectura, para el listado)
*/

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
    return {
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    };
}

// ---------- Folders (propiedad de A) ----------

/** Lista carpetas hijas de "parentId". Usa "root" para el nivel superior. */
export function listFolders(parentId) {
    const parentParam = parentId == null ? 'root' : parentId;
    return apiRequest(
        `/api/folders/?parent=${encodeURIComponent(parentParam)}`,
    );
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
    return apiRequest('/api/folders/', {
        method: 'POST',
        ...jsonBody({ parent, name }),
    });
}

export function renameFolder(id, name) {
    return apiRequest(`/api/folders/${id}/`, {
        method: 'PATCH',
        ...jsonBody({ name }),
    });
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
