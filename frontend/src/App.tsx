import { lazy, Suspense } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";

import GuestRoute from "./app/GuestRoute";
import ProtectedRoute from "./app/ProtectedRoute";
import ScrollToTop from "./app/ScrollToTop";

const Home = lazy(() => import("./pages/Home"));
const Login = lazy(() => import("./pages/LogIn"));
const SignUp = lazy(() => import("./pages/SignUp"));
const Chat = lazy(() => import("./pages/Chat"));
const ProfilePage = lazy(() => import("./features/profile/ProfilePage"));

export default function App() {
    return (
        <>
            <ScrollToTop />
            <Suspense fallback={<RouteLoader />}>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route
                        path="/login"
                        element={
                            <GuestRoute>
                                <Login />
                            </GuestRoute>
                        }
                    />
                    <Route
                        path="/register"
                        element={
                            <GuestRoute>
                                <SignUp />
                            </GuestRoute>
                        }
                    />
                    <Route
                        path="/chat"
                        element={
                            <ProtectedRoute>
                                <Chat />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/profile"
                        element={
                            <ProtectedRoute>
                                <ProfilePage />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="/home" element={<Navigate to="/" replace />} />
                    <Route path="*" element={<NotFound />} />
                </Routes>
            </Suspense>
        </>
    );
}

function RouteLoader() {
    return (
        <main className="grid min-h-dvh place-items-center bg-[var(--bg)] text-[var(--tx)]">
            <span className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        </main>
    );
}

function NotFound() {
    return (
        <main className="grid min-h-dvh place-items-center bg-white px-6 text-center text-neutral-950 dark:bg-neutral-950 dark:text-white">
            <div>
                <p className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                    404
                </p>
                <h1 className="mt-2 text-4xl font-bold">Page not found</h1>
                <Link className="mt-6 inline-block text-sm underline" to="/">
                    Return home
                </Link>
            </div>
        </main>
    );
}
