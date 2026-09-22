import { useEffect, useRef } from 'react';

export default function useLandingMotion() {
    const root = useRef(null);
    useEffect(() => {
        const element = root.current;
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.dataset.visible = 'true';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08 });
        element.querySelectorAll('[data-reveal]').forEach((item) => observer.observe(item));
        element.dataset.motion = 'true';
        let frame = 0;
        function update() {
            const progress = Math.min(1, Math.max(0,
                -element.getBoundingClientRect().top / window.innerHeight));
            element.style.setProperty('--hero-scale', 1 - progress * 0.15);
            frame = 0;
        }
        function onScroll() {
            if (!frame) frame = requestAnimationFrame(update);
        }
        update();
        window.addEventListener('scroll', onScroll, { passive: true });
        return () => {
            observer.disconnect();
            window.removeEventListener('scroll', onScroll);
            cancelAnimationFrame(frame);
            delete element.dataset.motion;
            element.style.removeProperty('--hero-scale');
        };
    }, []);
    return root;
}
