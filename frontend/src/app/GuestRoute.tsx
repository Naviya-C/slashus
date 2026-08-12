import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

type Props = {
    children: ReactNode;
};

export default function GuestRoute({ children }: Props) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <main className="grid min-h-dvh place-items-center bg-white text-neutral-500">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-blue-600" />
            </main>
        );
    }

    if (user) {
        return <Navigate to="/chat" replace />;
    }

    return children;
}
