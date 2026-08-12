import AuthFB from "../Atomic/AuthFB";
import AuthGl from "../Atomic/AuthGl";
import AuthX from "../Atomic/AuthX";

type Props = {
    onSuccess?: () => void;
    compact?: boolean;
};

function OAuth({ onSuccess, compact = false }: Props) {
    return (
        <div
            className={`flex justify-center gap-4 ${compact ? "mb-4" : "mb-8"}`}
        >
            <AuthGl onSuccess={onSuccess} />
            <AuthFB />
            <AuthX />
        </div>
    );
}

export default OAuth;
