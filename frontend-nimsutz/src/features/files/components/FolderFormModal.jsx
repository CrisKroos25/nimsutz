/* Componentes que solo usa este modulo. */
import { useEffect, useState } from 'react';
import Modal from '@shared/components/Modal/Modal';
import Input from '@shared/components/Input/Input';
import Button from '@shared/components/Button/Button';

/**
 * Formulario dentro de un Modal para crear o renombrar una carpeta.
 * Si "folder" viene definido, es modo renombrar; si no, es modo crear.
 */
export default function FolderFormModal({ open, onClose, folder, onSubmit }) {
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const isRename = Boolean(folder);

    useEffect(() => {
        if (open) {
            setName(folder?.name || '');
            setError('');
        }
    }, [open, folder]);

    async function handleSubmit(event) {
        event.preventDefault();
        const trimmed = name.trim();
        if (!trimmed) {
            setError('El nombre no puede estar vacío.');
            return;
        }
        setSubmitting(true);
        setError('');
        try {
            await onSubmit(trimmed);
            onClose();
        } catch (err) {
            setError(err.message || 'No se pudo guardar la carpeta.');
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <Modal
            open={open}
            onClose={onClose}
            title={isRename ? 'Renombrar carpeta' : 'Nueva carpeta'}
            description={
                isRename
                    ? 'Escribe el nuevo nombre de la carpeta.'
                    : 'Se creara dentro de la carpeta actual.'
            }
        >
            <form onSubmit={handleSubmit}>
                <Input
                    label="Nombre de la carpeta"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    error={error}
                    autoFocus
                />
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
                    <Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>
                        Cancelar
                    </Button>
                    <Button type="submit" loading={submitting} loadingLabel="Guardando...">
                        {isRename ? 'Guardar' : 'Crear'}
                    </Button>
                </div>
            </form>
        </Modal>
    );
}
