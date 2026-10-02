import { useEffect, useState } from 'react';
import { FileText, X } from 'lucide-react';
import { transfersApi } from '../api/transfersApi';
import FileActions from './FileActions/FileActions';
import Badge from '@shared/components/Badge/Badge';
import styles from '../pages/FilePages.module.css';

export default function FileDetails({ file, folderName, owner, formatBytes, formatDate, onClose, onChanged }) {
    const [preview, setPreview] = useState(null);
    const [previewFailed, setPreviewFailed] = useState(false);
    useEffect(() => {
        let active = true;
        if (['image/png', 'image/jpeg'].includes(file.content_type)) {
            transfersApi.solicitarDescarga(file.id).then(data => {
                if (active) setPreview(data.download_url);
            }).catch(() => { if (active) setPreviewFailed(true); });
        }
        return () => { active = false; };
    }, [file.id, file.content_type]);
    return <aside className={styles.details} aria-label={'Detalle de ' + file.original_name}>
        <div className={styles.detailHeading}><h2>Detalle</h2><button onClick={onClose} aria-label="Cerrar detalles"><X size={18} /></button></div>
        <div className={styles.preview}>{preview && !previewFailed ? <img src={preview} alt={file.original_name} onError={() => setPreviewFailed(true)} /> : <FileText size={56} aria-hidden="true" />}</div>
        {previewFailed && <p role="status" className={styles.muted}>No se pudo cargar la vista previa.</p>}
        <h3 className={styles.detailName}>{file.original_name}</h3>
        <Badge tone="success">Disponible</Badge>
        <FileActions file={file} onChanged={onChanged} expanded />
        <h3 className={styles.sectionTitle}>Información</h3>
        <dl className={styles.metadata}>
            <dt>Tipo</dt><dd>{file.content_type}</dd>
            <dt>Tamaño</dt><dd>{formatBytes(file.size_bytes)}</dd>
            <dt>Propietario</dt><dd>{owner || 'Tú'}</dd>
            <dt>Carpeta</dt><dd>{folderName || '—'}</dd>
            <dt>Creación</dt><dd>{formatDate(file.created_at)}</dd>
            <dt>Modificación</dt><dd>{formatDate(file.updated_at)}</dd>
        </dl>
    </aside>;
}
