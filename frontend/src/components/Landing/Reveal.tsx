import { useEffect, useRef, useState, type ReactNode } from "react";

type Props = {
    children: ReactNode;
    /** Stagger in ms. */
    delay?: number;
    /** Distance travelled on the way in, in px. */
    y?: number;
    className?: string;
};

/**
 * Reveals its children when they enter the viewport — and hides them again
 * when they leave. Because the observer *toggles* rather than unobserving,
 * the animation replays every time, scrolling down or back up.
 */
export default function Reveal({
    children,
    delay = 0,
    y = 26,
    className,
}: Props) {
    const ref = useRef<HTMLDivElement>(null);
    const [shown, setShown] = useState(false);

    useEffect(() => {
        const element = ref.current;
        if (!element) return;

        const observer = new IntersectionObserver(
            ([entry]) => setShown(entry.isIntersecting),
            { threshold: 0.12, rootMargin: "0px 0px -6% 0px" },
        );

        observer.observe(element);
        return () => observer.disconnect();
    }, []);

    return (
        <div
            ref={ref}
            className={className}
            style={{
                opacity: shown ? 1 : 0,
                transform: shown ? "none" : `translate3d(0, ${y}px, 0)`,
                transition: `opacity 620ms cubic-bezier(0.22,1,0.36,1) ${delay}ms, transform 620ms cubic-bezier(0.22,1,0.36,1) ${delay}ms`,
                willChange: "opacity, transform",
            }}
        >
            {children}
        </div>
    );
}
