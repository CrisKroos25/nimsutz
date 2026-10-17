// @features/files/fileTypes.js
// Única fuente de presentación de tipos de archivo. El backend decide qué se permite;
// aquí solo se define cómo se llama, qué icono y qué color tiene cada tipo.
import { FileText, Image as ImageIcon, File as FileGenericIcon } from 'lucide-react';
import styles from './fileTypes.module.css';

export const FILE_TYPES = {
    'application/pdf': { label: 'PDF', extensions: ['pdf'], icon: FileText, className: styles.typePdf },
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
        label: 'DOCX', extensions: ['docx'], icon: FileText, className: styles.typeDoc,
    },
    'text/plain': { label: 'TXT', extensions: ['txt'], icon: FileText, className: styles.typeDefault },
    'image/png': { label: 'PNG', extensions: ['png'], icon: ImageIcon, className: styles.typeImage },
    'image/jpeg': { label: 'JPG', extensions: ['jpg', 'jpeg'], icon: ImageIcon, className: styles.typeImage },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {
    label: 'XLSX', extensions: ['xlsx'], icon: FileText, className: styles.typeExcel,
    },
    'application/vnd.ms-excel': {
        label: 'XLS', extensions: ['xls'], icon: FileText, className: styles.typeExcel,
    },
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': {
        label: 'PPTX', extensions: ['pptx'], icon: FileText, className: styles.typePowerPoint,
    },
};

const FALLBACK_TYPE = { label: 'FILE', icon: FileGenericIcon, className: styles.typeDefault };

export function getFileTypeInfo(contentType, fileName = '') {
    const ext = String(fileName).split('.').pop()?.toLowerCase();
    const byMime = FILE_TYPES[String(contentType).toLowerCase()];
    const byExt = Object.values(FILE_TYPES).find((info) => info.extensions.includes(ext));
    return byMime || byExt || { ...FALLBACK_TYPE, label: ext?.toUpperCase() || FALLBACK_TYPE.label };
}