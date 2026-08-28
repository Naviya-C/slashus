import { GripVertical } from "lucide-react";

type Props = {
    label: string;
    value: number;
    min: number;
    max: number;
    onChange: (value: number) => void;
    side: "left" | "right";
    resetValue: number;
};

export default function PanelResizer({
    label,
    value,
    min,
    max,
    onChange,
    side,
    resetValue,
}: Props) {
    const clamp = (next: number) => Math.min(max, Math.max(min, next));

    function startResize(event: React.PointerEvent<HTMLDivElement>) {
        event.preventDefault();
        const handle = event.currentTarget;
        handle.setPointerCapture(event.pointerId);
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";

        const move = (moveEvent: PointerEvent) => {
            const next =
                side === "left"
                    ? moveEvent.clientX
                    : window.innerWidth - moveEvent.clientX;
            onChange(clamp(next));
        };
        const finish = () => {
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            handle.removeEventListener("pointermove", move);
            handle.removeEventListener("pointerup", finish);
            handle.removeEventListener("pointercancel", finish);
        };

        handle.addEventListener("pointermove", move);
        handle.addEventListener("pointerup", finish);
        handle.addEventListener("pointercancel", finish);
    }

    function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const direction = event.key === "ArrowRight" ? 1 : -1;
        onChange(clamp(value + direction * 16 * (side === "left" ? 1 : -1)));
    }

    return (
        <div
            role="separator"
            aria-label={label}
            aria-orientation="vertical"
            aria-valuemin={min}
            aria-valuemax={max}
            aria-valuenow={Math.round(value)}
            tabIndex={0}
            onPointerDown={startResize}
            onDoubleClick={() => onChange(resetValue)}
            onKeyDown={handleKeyDown}
            className="group relative hidden w-2 shrink-0 cursor-col-resize touch-none items-center justify-center bg-[var(--bg)] outline-none hover:bg-blue-500/10 focus-visible:bg-blue-500/10 lg:flex"
            title="Drag to resize · double-click to reset"
        >
            <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-[var(--sf3)] transition-colors group-hover:bg-blue-500/60 group-focus-visible:bg-blue-500/60" />
            <span className="relative grid h-9 w-4 place-items-center rounded-full border border-[var(--bd)] bg-[var(--sf)] text-[var(--tx3)] opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                <GripVertical size={11} />
            </span>
        </div>
    );
}
