/* Componentes que solo usa este modulo. */
import { useState } from 'react';
import Modal from '@shared/components/Modal/Modal';
import Button from '@shared/components/Button/Button';

/** Modal de confirmacion generico, usado para borrar carpeta/eliminar definitivo. */
export default function ConfirmDialog({ open, onClose, title, description, onConfirm }) {
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    async function handleConfirm() {
        setSubmitting(true);
        setError('');
        try {
            await onConfirm();
            onClose();
        } catch (err) {
            setError(err.message || 'No se pudo completar la accion.');
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <Modal open={open} onClose={onClose} title={title} description={description}>
            {error && (
                <p role="alert" style={{ color: 'var(--color-danger)' }}>
                    {error}
                </p>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
                <Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>
                    Cancelar
                </Button>
                <Button
                    type="button"
                    variant="danger"
                    onClick={handleConfirm}
                    loading={submitting}
                    loadingLabel="Procesando..."
                >
                    Confirmar
                </Button>
            </div>
        </Modal>
    );
}
