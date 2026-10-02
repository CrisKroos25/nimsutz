/**
 * mimeValidator.js  —  Módulo B (Rodrigo)
 *
 * SRP: Única responsabilidad → validar y normalizar tipos MIME de archivos.
 * OCP: Agregar soporte a un nuevo tipo no requiere modificar la lógica de subida,
 *       solo ampliar las constantes exportadas.
 */

/** Tipos MIME permitidos por el backend (RN-E3-18). */
export const ALLOWED_MIME_TYPES = Object.freeze([
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'image/png',
    'image/jpeg',
]);

/** Máximo tamaño de archivo en bytes (RN-E3-17: 25 MB). */
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024;

/**
 * Mapa de extensión → MIME para navegadores que asignan tipos vacíos
 * o incorrectos (ej. Windows con archivos .pdf o .docx).
 */
const EXT_TO_MIME = Object.freeze({
    pdf: 'application/pdf',
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    txt: 'text/plain',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
});

/**
 * Resuelve el tipo MIME efectivo de un archivo.
 * Si el navegador no lo detectó correctamente, lo infiere por extensión.
 *
 * @param {File} file
 * @returns {string} Tipo MIME normalizado
 */
export function resolveMimeType(file) {
    const reported = file.type;
    if (reported && reported !== 'application/octet-stream') {
        return reported;
    }
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    return EXT_TO_MIME[ext] ?? reported;
}

/**
 * Valida que el archivo cumpla los límites del sistema.
 * Lanza un Error con mensaje legible si falla.
 *
 * @param {File}   file
 * @param {string} resolvedMime  — tipo ya normalizado por resolveMimeType()
 * @throws {Error}
 */
export function assertFileAllowed(file, resolvedMime) {
    if (file.size > MAX_FILE_SIZE_BYTES) {
        throw new Error('El archivo supera el límite de 25 MB.');
    }
    if (!ALLOWED_MIME_TYPES.includes(resolvedMime)) {
        throw new Error(
            'Tipo de archivo no permitido. Solo se permiten PDF, DOCX, TXT, PNG y JPG.',
        );
    }
}
