/**
 * fileTypeInfo.js  —  Módulo B (Rodrigo)
 *
 * SRP: Única responsabilidad → resolver la metadata visual de un tipo de archivo
 *      (etiqueta, icono, clase CSS) a partir del MIME y la extensión.
 * OCP: Para soportar un nuevo tipo (ej. XLSX) basta con agregar una entrada
 *      en FILE_TYPE_RULES, sin tocar los componentes consumidores.
 */

import {
    FileText,
    Image as ImageIcon,
    File as FileGenericIcon,
} from 'lucide-react';

/**
 * @typedef {Object} FileTypeInfo
 * @property {string}   label      - Etiqueta corta del tipo (ej. "PDF")
 * @property {Function} icon       - Componente de icono de lucide-react
 * @property {string}   className  - Nombre de clase CSS (sin prefijo de módulo)
 */

/** Reglas de detección en orden de prioridad. */
const FILE_TYPE_RULES = [
    {
        test: (mime, ext) => mime.includes('pdf') || ext === 'PDF',
        result: { label: 'PDF', icon: FileText, className: 'typePdf' },
    },
    {
        test: (mime, ext) =>
            mime.includes('presentation') ||
            ['PPT', 'PPTX'].includes(ext),
        result: (ext) => ({ label: ext || 'PPTX', icon: FileText, className: 'typePpt' }),
    },
    {
        test: (mime, ext) =>
            mime.includes('image') ||
            ['PNG', 'JPG', 'JPEG', 'WEBP', 'SVG'].includes(ext),
        result: (ext) => ({ label: ext || 'IMG', icon: ImageIcon, className: 'typeImage' }),
    },
    {
        test: (mime, ext) =>
            mime.includes('word') || ['DOC', 'DOCX'].includes(ext),
        result: { label: 'DOCX', icon: FileText, className: 'typeDoc' },
    },
    {
        test: (mime, ext) =>
            mime.includes('spreadsheet') ||
            ['XLS', 'XLSX', 'CSV'].includes(ext),
        result: (ext) => ({ label: ext || 'XLSX', icon: FileText, className: 'typeExcel' }),
    },
    {
        test: (mime, ext) =>
            mime.includes('zip') || ['ZIP', 'RAR', 'TAR', 'GZ'].includes(ext),
        result: (ext) => ({ label: ext || 'ZIP', icon: FileText, className: 'typeZip' }),
    },
    {
        test: (mime, ext) =>
            mime.includes('text') || ext === 'TXT',
        result: { label: 'TXT', icon: FileText, className: 'typeTxt' },
    },
];

/**
 * Resuelve la metadata visual de un archivo a partir de su tipo MIME y nombre.
 *
 * @param {string} contentType  - Tipo MIME del archivo
 * @param {string} [fileName]   - Nombre del archivo (para inferir por extensión)
 * @param {Object} styles       - Objeto de CSS Modules del componente consumidor
 * @returns {FileTypeInfo}
 */
export function getFileTypeInfo(contentType, fileName = '', styles = {}) {
    const ext = String(fileName).split('.').pop()?.toUpperCase() ?? '';
    const mime = String(contentType ?? '').toLowerCase();

    for (const rule of FILE_TYPE_RULES) {
        if (rule.test(mime, ext)) {
            const raw =
                typeof rule.result === 'function' ? rule.result(ext) : rule.result;
            return {
                ...raw,
                className: styles[raw.className] ?? raw.className,
            };
        }
    }

    return {
        label: ext || 'FILE',
        icon: FileGenericIcon,
        className: styles.typeDefault ?? 'typeDefault',
    };
}
