import "./App.css";
import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/LogIn";
import SignUp from "./pages/SignUp";
import Chat from "./pages/Chat";
import ProtectedRoute from "./app/ProtectedRoute";
import ScrollToTop from "./app/ScrollToTop";
import GuestRoute from "./app/GuestRoute";

function App() {
    return (
        <>
            <ScrollToTop />
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
                    path="*"
                    element={
                        <main className="grid min-h-dvh place-items-center px-6 text-center">
                            <div>
                                <p className="text-sm font-semibold text-blue-600">
                                    404
                                </p>
                                <h1 className="mt-2 text-4xl font-bold">
                                    Page not found
                                </h1>
                                <a
                                    className="mt-6 inline-block text-sm underline"
                                    href="/"
                                >
                                    Return home
                                </a>
                            </div>
                        </main>
                    }
                />
            </Routes>
        </>
    );
}

export default App;
