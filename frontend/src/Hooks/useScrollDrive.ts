import { useEffect, useRef, useState, type RefObject } from "react";

export type ScrollDrive = {
    /** 0 -> 1 position along the scrollable range. Goes back down when you scroll up. */
    progress: number;
    /** -1 -> 1 smoothed scroll velocity. Negative = scrolling up. */
    velocity: number;
    /** 1 = down, -1 = up, 0 = idle. */
    direction: number;
};

const clamp = (value: number, min: number, max: number) =>
    Math.min(max, Math.max(min, value));

const lerp = (from: number, to: number, amount: number) =>
    from + (to - from) * amount;

/**
 * Produces a continuous, *reversible* scroll signal.
 *
 * It reads the scroll position of `ref` when that element actually
 * overflows, and also accumulates raw wheel / touch deltas so the effect
 * still responds on short pages where nothing can scroll. Because the
 * output is a position (not a one-shot trigger), scrolling back up plays
 * the animation in reverse — every time, in both directions.
 */
export function useScrollDrive(
    ref: RefObject<HTMLElement | null>,
    options: {
        wheelDivisor?: number;
        smoothing?: number;
        minRange?: number;
    } = {},
): ScrollDrive {
    const { wheelDivisor = 900, smoothing = 0.12, minRange = 120 } = options;

    const [drive, setDrive] = useState<ScrollDrive>({
        progress: 0,
        velocity: 0,
        direction: 0,
    });

    const target = useRef(0);
    const current = useRef(0);
    const velocity = useRef(0);
    const lastEmitted = useRef({ progress: -1, velocity: -1 });

    useEffect(() => {
        const element = ref.current;
        if (!element) return;

        // Below this the real scroll range is too short to map to 0..1
        // smoothly, so we fall back to accumulating wheel deltas instead.
        const isScrollable = () =>
            element.scrollHeight - element.clientHeight > minRange;

        const readScroll = () => {
            const range = element.scrollHeight - element.clientHeight;
            if (range <= minRange) return;
            target.current = clamp(element.scrollTop / range, 0, 1);
        };

        const onScroll = () => readScroll();

        const onWheel = (event: WheelEvent) => {
            // When the panel can scroll, `scroll` already covers it.
            if (isScrollable()) return;
            target.current = clamp(
                target.current + event.deltaY / wheelDivisor,
                0,
                1,
            );
        };

        let touchY: number | null = null;
        const onTouchStart = (event: TouchEvent) => {
            touchY = event.touches[0]?.clientY ?? null;
        };
        const onTouchMove = (event: TouchEvent) => {
            if (isScrollable() || touchY === null) return;
            const y = event.touches[0]?.clientY ?? touchY;
            target.current = clamp(
                target.current + (touchY - y) / (wheelDivisor / 3),
                0,
                1,
            );
            touchY = y;
        };

        readScroll();

        element.addEventListener("scroll", onScroll, { passive: true });
        window.addEventListener("wheel", onWheel, { passive: true });
        window.addEventListener("touchstart", onTouchStart, { passive: true });
        window.addEventListener("touchmove", onTouchMove, { passive: true });

        let frame = 0;
        const tick = () => {
            const previous = current.current;
            current.current = lerp(current.current, target.current, smoothing);

            const delta = current.current - previous;
            velocity.current = clamp(
                lerp(velocity.current, delta * 26, 0.2),
                -1,
                1,
            );

            const progress = Number(current.current.toFixed(4));
            const speed = Number(velocity.current.toFixed(4));

            if (
                Math.abs(progress - lastEmitted.current.progress) > 0.0008 ||
                Math.abs(speed - lastEmitted.current.velocity) > 0.0008
            ) {
                lastEmitted.current = { progress, velocity: speed };
                setDrive({
                    progress,
                    velocity: speed,
                    direction: speed > 0.02 ? 1 : speed < -0.02 ? -1 : 0,
                });
            }

            frame = requestAnimationFrame(tick);
        };

        frame = requestAnimationFrame(tick);

        return () => {
            cancelAnimationFrame(frame);
            element.removeEventListener("scroll", onScroll);
            window.removeEventListener("wheel", onWheel);
            window.removeEventListener("touchstart", onTouchStart);
            window.removeEventListener("touchmove", onTouchMove);
        };
    }, [ref, wheelDivisor, smoothing, minRange]);

    return drive;
}

/**
 * Same signal as useScrollDrive, but bound to the window scroll.
 * Used by the landing page, where the document itself is the scroller.
 */
export function useWindowScrollDrive(
    options: { smoothing?: number } = {},
): ScrollDrive {
    const { smoothing = 0.12 } = options;

    const [drive, setDrive] = useState<ScrollDrive>({
        progress: 0,
        velocity: 0,
        direction: 0,
    });

    const target = useRef(0);
    const current = useRef(0);
    const velocity = useRef(0);
    const lastEmitted = useRef({ progress: -1, velocity: -1 });

    useEffect(() => {
        const read = () => {
            const doc = document.documentElement;
            const range = doc.scrollHeight - window.innerHeight;
            target.current = range > 0 ? clamp(window.scrollY / range, 0, 1) : 0;
        };

        read();
        window.addEventListener("scroll", read, { passive: true });
        window.addEventListener("resize", read);

        let frame = 0;
        const tick = () => {
            const previous = current.current;
            current.current = lerp(current.current, target.current, smoothing);

            const delta = current.current - previous;
            velocity.current = clamp(
                lerp(velocity.current, delta * 26, 0.2),
                -1,
                1,
            );

            const progress = Number(current.current.toFixed(4));
            const speed = Number(velocity.current.toFixed(4));

            if (
                Math.abs(progress - lastEmitted.current.progress) > 0.0008 ||
                Math.abs(speed - lastEmitted.current.velocity) > 0.0008
            ) {
                lastEmitted.current = { progress, velocity: speed };
                setDrive({
                    progress,
                    velocity: speed,
                    direction: speed > 0.02 ? 1 : speed < -0.02 ? -1 : 0,
                });
            }

            frame = requestAnimationFrame(tick);
        };

        frame = requestAnimationFrame(tick);

        return () => {
            cancelAnimationFrame(frame);
            window.removeEventListener("scroll", read);
            window.removeEventListener("resize", read);
        };
    }, [smoothing]);

    return drive;
}

/**
 * Eases a value towards `target` on every frame and stops once it arrives.
 * Used for hover states that should glide rather than snap.
 */
export function useTween(target: number, smoothing = 0.14): number {
    const [value, setValue] = useState(target);
    const current = useRef(target);

    useEffect(() => {
        let frame = 0;

        const tick = () => {
            const distance = target - current.current;

            if (Math.abs(distance) < 0.0015) {
                current.current = target;
                setValue(target);
                return;
            }

            current.current += distance * smoothing;
            setValue(Number(current.current.toFixed(4)));
            frame = requestAnimationFrame(tick);
        };

        frame = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(frame);
    }, [target, smoothing]);

    return value;
}
