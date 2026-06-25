import { useEffect, useState } from "react";

// ─── useNavScroll ───────────────────────────────────────────

export function useNavScroll(
    offset: number = 20
): boolean {
    const [scrolled, setScrolled] =
        useState<boolean>(false);

    useEffect(() => {
        const handler = () => {
            setScrolled(
                window.scrollY > offset
            );
        };

        window.addEventListener(
            "scroll",
            handler,
            { passive: true }
        );

        // Run once on mount
        handler();

        return () => {
            window.removeEventListener(
                "scroll",
                handler
            );
        };
    }, [offset]);

    return scrolled;
}