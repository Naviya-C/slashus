import './App.css'
import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/LogIn";
import SignUp from './pages/SignUp';
import Chat from './pages/Chat';
import HowItWorks from './pages/HowItWork';


function App() {
    return (
        <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<SignUp />} />
            <Route path='/chat' element={<Chat />} />
            <Route path='/how' element={<HowItWorks />} />
            <Route path="*" element={<div className="p-100 font-bold text-6xl text-center">404 - Page not found</div>} />
        </Routes>
    );
}

export default App;