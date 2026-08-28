import { FaFacebookF } from "react-icons/fa";

const AuthFB = () => {
    return (
        <button
            disabled
            className="
                w-14
                h-14
                border
                border-slate-300
                dark:border-neutral-700
                rounded-xl
                flex
                items-center
                justify-center
                transition
                disabled:opacity-50
                disabled:cursor-not-allowed
                disabled:hover:bg-transparent
            "
        >
            <FaFacebookF size={24} className="text-blue-600" />
        </button>
    );
};

export default AuthFB;
