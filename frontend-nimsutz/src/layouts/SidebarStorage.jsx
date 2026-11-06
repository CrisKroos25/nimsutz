import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { HardDrive } from 'lucide-react';
import { useAuth } from '@shared/auth/AuthContext';
import { getAccountOverview } from '@shared/api/accountApi';
import { formatStorage } from '@shared/utils/planFormat';
import styles from './Layouts.module.css';

export default function SidebarStorage() {
    const { user } = useAuth();
    const { pathname } = useLocation();
    const [storage, setStorage] = useState(null);

    useEffect(() => {
        let active = true;
        getAccountOverview()
            .then((data) => { if (active) setStorage(data.storage ?? null); })
            .catch(() => { if (active) setStorage(null); });
        return () => { active = false; };
    }, [user.id, pathname]);

    if (!storage || !(storage.capacity_bytes > 0)) return null;

    const used = Math.min(storage.used_bytes, storage.capacity_bytes);
    const percent = Math.round(used / storage.capacity_bytes * 100);

    return (
        <section className={styles.storage} aria-label="Almacenamiento">
            <p className={styles.storageTitle}>
                <HardDrive size={16} aria-hidden="true" /> Almacenamiento
            </p>
            <progress
                max={storage.capacity_bytes}
                value={used}
                aria-label="Almacenamiento usado"
                className={styles.storageMeter}
            />
            <p className={styles.storageText}>
                {formatStorage(storage.used_bytes)} de {formatStorage(storage.capacity_bytes)} · {percent} %
            </p>
        </section>
    );
}