import { useId, useState } from 'react';
import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import Input from './Input';
import styles from './Input.module.css';

export default function PasswordInput({ id, label, visibilityLabel = 'contraseña', ...props }) {
    const generatedId = useId();
    const inputId = id || generatedId;
    const [visible, setVisible] = useState(false);
    const Icon = visible ? EyeOff : Eye;
    return (
        <Input {...props} id={inputId} label={label} type={visible ? 'text' : 'password'}
            leadingIcon={<LockKeyhole size={18} />}
            trailingAction={
                <button type="button" className={styles.reveal} disabled={props.disabled}
                    aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${visibilityLabel}`}
                    aria-controls={inputId} onClick={() => setVisible((value) => !value)}>
                    <Icon size={18} aria-hidden="true" />
                </button>
            }
        />
    );
}
