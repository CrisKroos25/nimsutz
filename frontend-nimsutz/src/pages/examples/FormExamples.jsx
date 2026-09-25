import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import Input from '../../shared/components/Input/Input';
import Button from '../../shared/components/Button/Button';
import Modal from '../../shared/components/Modal/Modal';
import styles from './FormExamples.module.css';
import pageStyles from '../DesignSystemPage.module.css';

export default function FormExamples() {
    const [activeModal, setActiveModal] = useState(null);
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [result, setResult] = useState(
        'Los ejemplos no modifican archivos reales.',
    );
    const editing = activeModal === 'rename';

    function openNameModal(mode) {
        setName(mode === 'rename' ? 'Informes 2026' : '');
        setError('');
        setActiveModal(mode);
    }

    function submitName(event) {
        event.preventDefault();
        if (!name.trim()) {
            setError('Escribe un nombre para la carpeta.');
            return;
        }
        setResult(
            `Simulación: carpeta ${editing ? 'renombrada' : 'creada'} como «${name.trim()}».`,
        );
        setActiveModal(null);
    }

    return (
        <>
            <section aria-labelledby="fields-title">
                <h2 id="fields-title" className={pageStyles.sectionTitle}>
                    Campos de texto
                </h2>
                <div className={pageStyles.panel}>
                    <div className={styles.fields}>
                        <Input
                            label="Nombre de carpeta"
                            placeholder="Ej. Informes 2027"
                            hint="Selecciona el campo para ver su estado activo."
                        />
                        <Input
                            label="Nombre con error"
                            defaultValue=""
                            error="El nombre de la carpeta es obligatorio."
                        />
                        <Input
                            label="Campo deshabilitado"
                            value="Mis archivos"
                            disabled
                            readOnly
                        />
                    </div>
                </div>
            </section>
            <section aria-labelledby="modals-title">
                <h2 id="modals-title" className={pageStyles.sectionTitle}>
                    Ventanas modales
                </h2>
                <div className={pageStyles.panel}>
                    <p className={pageStyles.muted}>
                        Ejemplos basados en M15 y M16. Puedes cerrar con
                        Cancelar o Escape.
                    </p>
                    <div className={pageStyles.row}>
                        <Button onClick={() => openNameModal('create')}>
                            Nueva carpeta
                        </Button>
                        <Button
                            variant="secondary"
                            onClick={() => openNameModal('rename')}
                        >
                            Renombrar carpeta
                        </Button>
                        <Button
                            variant="danger"
                            onClick={() => setActiveModal('delete')}
                        >
                            Confirmar eliminación
                        </Button>
                    </div>
                    <p role="status">{result}</p>
                </div>
            </section>
            <Modal
                open={activeModal === 'create' || editing}
                onClose={() => setActiveModal(null)}
                title={editing ? 'Renombrar carpeta' : 'Nueva carpeta'}
            >
                <form onSubmit={submitName} noValidate className={styles.form}>
                    <Input
                        label="Nombre de la carpeta"
                        name="folderName"
                        required
                        placeholder="Ej. Informes 2027"
                        value={name}
                        error={error}
                        onChange={(event) => {
                            setName(event.target.value);
                            setError('');
                        }}
                    />
                    <div className={styles.actions}>
                        <Button
                            variant="ghost"
                            onClick={() => setActiveModal(null)}
                        >
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={!name.trim()}>
                            {editing ? 'Guardar nombre' : 'Crear carpeta'}
                        </Button>
                    </div>
                </form>
            </Modal>
            <Modal
                open={activeModal === 'delete'}
                onClose={() => setActiveModal(null)}
                title="Eliminar definitivamente"
                icon={<Trash2 strokeWidth={2} />}
                description={
                    <>
                        <strong>Propuesta_Rechazada_Mayo.pdf</strong> se
                        eliminará de forma permanente. Esta acción no puede
                        revertirse y el archivo no podrá recuperarse bajo ningún
                        concepto.
                    </>
                }
            >
                <div className={styles.actions}>
                    <Button
                        variant="ghost"
                        onClick={() => setActiveModal(null)}
                    >
                        Cancelar
                    </Button>
                    <Button
                        variant="danger"
                        onClick={() => {
                            setResult(
                                'Simulación: eliminación confirmada. No se modificó ningún archivo.',
                            );
                            setActiveModal(null);
                        }}
                    >
                        Eliminar definitivamente
                    </Button>
                </div>
            </Modal>
        </>
    );
}
