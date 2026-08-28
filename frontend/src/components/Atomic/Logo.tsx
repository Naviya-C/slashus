import { useState } from "react";

import Logo3D from "../Brand/Logo3D";
import { useTween } from "../../Hooks/useScrollDrive";
import { useTheme } from "../../context/ThemeContext";

type Props = {
    /** Force a variant. Omit to follow the active colour theme. */
    theme?: "light" | "dark";
    /** Height of the 3D mark in px. */
    size?: number;
};

/**
 * Brand lockup: the 3D mark plus the wordmark.
 * Hovering eases the mark into a spin and pulls the two pieces apart;
 * moving away unwinds it along the same path.
 */
const Logo = ({ theme, size = 40 }: Props) => {
    const { resolvedTheme } = useTheme();
    const active = theme ?? resolvedTheme;
    const [hovered, setHovered] = useState(false);

    // Eased hover position drives the same animation the scroll does.
    const progress = useTween(hovered ? 1 : 0, 0.16);

    return (
        <div
            className="group flex items-center gap-2.5"
            onPointerEnter={() => setHovered(true)}
            onPointerLeave={() => setHovered(false)}
        >
            <div
                className="relative shrink-0 transition-transform duration-300 group-hover:scale-105"
                style={{ width: size * 0.8, height: size }}
            >
                <Logo3D
                    progress={progress}
                    velocity={progress * 0.35}
                    size={size}
                    depth={7}
                    spread={0.28}
                    ambient={false}
                    interactive={false}
                    float={false}
                    variant={active}
                />
            </div>

            <h3
                className={`text-lg font-bold transition-[letter-spacing] duration-300 group-hover:tracking-wide sm:text-xl ${
                    active === "dark" ? "text-white" : "text-neutral-950"
                }`}
            >
                SLASH
                <span className="text-blue-500 transition-colors duration-300 group-hover:text-cyan-400">
                    US
                </span>
            </h3>
        </div>
    );
};

export default Logo;
