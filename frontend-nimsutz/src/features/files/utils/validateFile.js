// @features/files/validateFile.js
import { formatStorage } from '@shared/utils/planFormat';
import { FILE_TYPES } from './fileTypes';

// Si el backend agrega un tipo que el front aún no conoce, se muestra su subtipo.
const typeLabel = (mime) =>
    FILE_TYPES[mime]?.label ?? mime.split('/')[1]?.toUpperCase() ?? mime;

// "PDF, DOCX, TXT, PNG y JPG"
export function describeAllowedTypes(rules) {
    return new Intl.ListFormat('es', { style: 'long', type: 'conjunction' }).format(
        rules.allowed_content_types.map(typeLabel),
    );
}

// Valor para <input accept="...">
export const acceptAttribute = (rules) => rules.allowed_content_types.join(',');

// Algunos navegadores no detectan el tipo: se completa por extensión.
export function resolveContentType(file) {
    if (file.type && file.type !== 'application/octet-stream') return file.type;
    const ext = file.name.split('.').pop()?.toLowerCase();
    const match = Object.entries(FILE_TYPES).find(([, info]) => info.extensions.includes(ext));
    return match ? match[0] : file.type;
}

export function validateFile(file, contentType, rules) {
    if (file.size > rules.max_file_size_bytes) {
        throw new Error(`El archivo supera el límite de ${formatStorage(rules.max_file_size_bytes)}.`);
    }
    if (!rules.allowed_content_types.includes(contentType)) {
        throw new Error(`Tipo de archivo no permitido. Solo se permiten ${describeAllowedTypes(rules)}.`);
    }
}