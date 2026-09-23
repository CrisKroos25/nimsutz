import { useEffect, useRef } from 'react';

export default function useProductMotion() {
    const root = useRef(null);
    useEffect(() => {
        const section = root.current;
        let frame = 0;
        function update() {
            const bounds = section.getBoundingClientRect();
            const progress = Math.min(1, Math.max(0,
                (window.innerHeight - bounds.top) / (window.innerHeight + bounds.height)));
            section.style.setProperty('--preview-shift', (0.5 - progress) * 90 + 'px');
            section.style.setProperty('--preview-scale', 0.94 + progress * 0.06);
            frame = 0;
        }
        function schedule() {
            if (!frame) frame = requestAnimationFrame(update);
        }
        update();
        window.addEventListener('scroll', schedule, { passive: true });
        window.addEventListener('resize', schedule);
        return () => {
            window.removeEventListener('scroll', schedule);
            window.removeEventListener('resize', schedule);
            cancelAnimationFrame(frame);
        };
    }, []);
    return root;
}
