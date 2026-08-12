import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function ScrollToTop() {
    const { pathname, hash } = useLocation();

    useEffect(() => {
        if (hash) {
            requestAnimationFrame(() => {
                document.getElementById(hash.slice(1))?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            });
            return;
        }

        window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }, [pathname, hash]);

    return null;
}
