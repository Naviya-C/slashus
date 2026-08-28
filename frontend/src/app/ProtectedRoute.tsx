import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children }: { children: ReactNode }) {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return (
            <main className="grid min-h-dvh place-items-center bg-[var(--bg)] text-[var(--tx2)]">
                <div className="flex items-center gap-3 text-sm" role="status">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--bd)] border-t-blue-600" />
                    Loading your workspace…
                </div>
            </main>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace state={{ from: location }} />;
    }

    return children;
}
