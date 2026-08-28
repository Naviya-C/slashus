import { useEffect, useMemo, useRef, useState } from "react";

import { useTheme } from "../../context/ThemeContext";

/**
 * A 3D version of the SLASHUS mark.
 *
 * The mark is two flat shapes (the slash bar and the triangle). Each one is
 * extruded by stacking N clipped slabs along the Z axis, then the whole group
 * is rotated inside a CSS `perspective` stage. No WebGL, no new dependency —
 * GPU-composited transforms only.
 *
 * `progress` (0..1) and `velocity` (-1..1) are a *position*, not a one-shot
 * trigger, so any driver works: scroll down and it opens up, scroll back up
 * and it plays in reverse; hover in and it spins, hover out and it unwinds.
 */

type Props = {
    /** 0..1 drive position (scroll, hover, anything). */
    progress?: number;
    /** -1..1 drive velocity. Feeds the glow and a little extra yaw. */
    velocity?: number;
    /** Height of the mark in px; width is 0.8 * height. */
    size?: number;
    /** Extrusion slabs. Lower it on small marks. */
    depth?: number;
    /** How far the pieces drift apart at progress = 1. */
    spread?: number;
    /** Orbit rings, sparks and glow. */
    ambient?: boolean;
    /** Tilt towards the pointer. */
    interactive?: boolean;
    /** Idle bobbing. */
    float?: boolean;
    /** Force the palette. Omit to follow the active colour theme. */
    variant?: "light" | "dark";
    className?: string;
};

/* Shape outlines, traced from assets/logo_black.svg (viewBox 60 x 75). */
const SLASH = "polygon(58% 4.5%, 95% 10.5%, 37% 95%, 0.6% 89%)";
const TRIANGLE = "polygon(76% 45%, 97% 78%, 55% 78%)";

type Face = { top: string; bottom: string; back: string };

const FACES_DARK: Record<"slash" | "triangle", Face> = {
    slash: { top: "#7dd3fc", bottom: "#2563eb", back: "#0b1a3a" },
    triangle: { top: "#67e8f9", bottom: "#0891b2", back: "#062a33" },
};

const FACES_LIGHT: Record<"slash" | "triangle", Face> = {
    slash: { top: "#3b82f6", bottom: "#1e3a8a", back: "#c7d7f5" },
    triangle: { top: "#06b6d4", bottom: "#0e5f75", back: "#bfe6ef" },
};

function mix(from: string, to: string, amount: number) {
    const parse = (hex: string) => [
        parseInt(hex.slice(1, 3), 16),
        parseInt(hex.slice(3, 5), 16),
        parseInt(hex.slice(5, 7), 16),
    ];
    const [r1, g1, b1] = parse(from);
    const [r2, g2, b2] = parse(to);
    const channel = (a: number, b: number) => Math.round(a + (b - a) * amount);
    return `rgb(${channel(r1, r2)}, ${channel(g1, g2)}, ${channel(b1, b2)})`;
}

type PieceProps = {
    clip: string;
    face: Face;
    depth: number;
    step: number;
    style?: React.CSSProperties;
};

function Piece({ clip, face, depth, step, style }: PieceProps) {
    const slabs = [];

    for (let index = depth - 1; index >= 0; index -= 1) {
        const t = depth === 1 ? 0 : index / (depth - 1);
        const isFront = index === 0;

        slabs.push(
            <span
                key={index}
                className="l3d-slab"
                style={{
                    clipPath: clip,
                    WebkitClipPath: clip,
                    transform: `translateZ(${-index * step}px)`,
                    background: isFront
                        ? `linear-gradient(150deg, ${face.top} 0%, ${face.bottom} 62%, ${mix(face.bottom, face.back, 0.45)} 100%)`
                        : mix(face.bottom, face.back, Math.min(1, t * 1.15)),
                    boxShadow: isFront
                        ? `0 22px 60px -18px ${face.bottom}`
                        : undefined,
                }}
            />,
        );
    }

    return (
        <div className="l3d-piece" style={{ inset: 0, ...style }}>
            {slabs}
        </div>
    );
}

export default function Logo3D({
    progress = 0,
    velocity = 0,
    size = 420,
    depth = 16,
    spread = 1,
    ambient = true,
    interactive = true,
    float = true,
    variant,
    className,
}: Props) {
    const { resolvedTheme } = useTheme();
    const palette = variant ?? resolvedTheme;
    const faces = palette === "dark" ? FACES_DARK : FACES_LIGHT;

    const stageRef = useRef<HTMLDivElement>(null);
    const [pointer, setPointer] = useState({ x: 0, y: 0 });

    useEffect(() => {
        if (!interactive) return;
        const element = stageRef.current;
        if (!element) return;

        const onMove = (event: PointerEvent) => {
            const rect = element.getBoundingClientRect();
            setPointer({
                x: (event.clientX - rect.left) / rect.width - 0.5,
                y: (event.clientY - rect.top) / rect.height - 0.5,
            });
        };
        const onLeave = () => setPointer({ x: 0, y: 0 });

        element.addEventListener("pointermove", onMove);
        element.addEventListener("pointerleave", onLeave);
        return () => {
            element.removeEventListener("pointermove", onMove);
            element.removeEventListener("pointerleave", onLeave);
        };
    }, [interactive]);

    const p = progress;
    const v = velocity;
    const step = Math.max(1.2, size / 190);
    const width = size * 0.8;
    const drift = spread * (size / 420);

    // Whole-group orientation. Everything is a function of `p`, so it is
    // fully reversible on the way back.
    const worldTransform = [
        `rotateX(${14 - p * 30 - pointer.y * 16}deg)`,
        `rotateY(${-24 + p * 74 + pointer.x * 22 + v * 9}deg)`,
        `rotateZ(${-4 + p * 12 + v * 4}deg)`,
        `translate3d(0, ${(0.5 - p) * 46 * drift}px, ${p * 60 * drift}px)`,
        `scale(${1 + Math.sin(p * Math.PI) * 0.07})`,
    ].join(" ");

    // The two shapes drift apart mid-drive and reassemble.
    const slashStyle = {
        transform: `translate3d(${-p * 16 * drift}px, 0, ${p * 34 * drift}px)`,
    };
    const triangleStyle = {
        transform: `translate3d(${p * 34 * drift}px, ${p * 18 * drift}px, ${-p * 46 * drift}px) rotateZ(${p * 20}deg)`,
    };

    const sparks = useMemo(
        () =>
            Array.from({ length: 16 }, (_, index) => {
                const angle = (index / 16) * Math.PI * 2;
                const radius = 0.34 + ((index * 37) % 100) / 320;
                return {
                    left: 50 + Math.cos(angle) * radius * 100,
                    top: 50 + Math.sin(angle) * radius * 92,
                    z: ((index * 53) % 100) - 50,
                    size: 2 + ((index * 17) % 4),
                    delay: (index % 7) * 0.45,
                };
            }),
        [],
    );

    const glow = 0.3 + Math.abs(v) * 0.55 + Math.sin(p * Math.PI) * 0.2;

    return (
        <div
            ref={stageRef}
            className={`l3d-stage ${className ?? ""}`}
            aria-hidden="true"
        >
            {ambient && (
                <div
                    className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl transition-opacity duration-300"
                    style={{
                        width: size * 1.5,
                        height: size * 1.5,
                        opacity: Math.min(0.95, glow),
                        background:
                            palette === "dark"
                                ? "radial-gradient(circle, rgba(56,132,255,0.42) 0%, rgba(34,211,238,0.16) 42%, transparent 68%)"
                                : "radial-gradient(circle, rgba(59,130,246,0.34) 0%, rgba(14,165,233,0.14) 44%, transparent 70%)",
                        transform: `translate(-50%, -50%) scale(${1 + p * 0.25})`,
                    }}
                />
            )}

            <div
                className={`l3d-world ${float ? "l3d-float" : ""}`}
                style={{ width, height: size }}
            >
                <div
                    style={{
                        position: "absolute",
                        inset: 0,
                        transformStyle: "preserve-3d",
                        transform: worldTransform,
                    }}
                >
                    {ambient &&
                        [0, 1, 2].map((index) => {
                            const ringSize = size * (1.08 + index * 0.24);
                            return (
                                <span
                                    key={index}
                                    className="l3d-ring"
                                    style={{
                                        width: ringSize,
                                        height: ringSize,
                                        marginLeft: -ringSize / 2,
                                        marginTop: -ringSize / 2,
                                        color:
                                            palette === "dark"
                                                ? "rgba(125,211,252,0.22)"
                                                : "rgba(37,99,235,0.20)",
                                        transform: `translateZ(${-70 - index * 55}px) rotateX(74deg) rotateZ(${p * (index % 2 === 0 ? 200 : -200) + index * 40}deg)`,
                                    }}
                                />
                            );
                        })}

                    <Piece
                        clip={SLASH}
                        face={faces.slash}
                        depth={depth}
                        step={step}
                        style={slashStyle}
                    />
                    <Piece
                        clip={TRIANGLE}
                        face={faces.triangle}
                        depth={depth}
                        step={step}
                        style={triangleStyle}
                    />

                    {ambient &&
                        sparks.map((spark, index) => (
                            <span
                                key={index}
                                className="l3d-spark"
                                style={{
                                    left: `${spark.left}%`,
                                    top: `${spark.top}%`,
                                    width: spark.size,
                                    height: spark.size,
                                    opacity: 0.25 + Math.abs(v) * 0.6,
                                    background:
                                        palette === "dark"
                                            ? "rgba(186,230,253,0.9)"
                                            : "rgba(37,99,235,0.65)",
                                    transform: `translateZ(${spark.z + p * 120}px) scale(${1 + Math.abs(v) * 1.6})`,
                                    animation: `l3d-twinkle ${5 + spark.delay}s ease-in-out ${spark.delay}s infinite`,
                                }}
                            />
                        ))}
                </div>
            </div>
        </div>
    );
}
