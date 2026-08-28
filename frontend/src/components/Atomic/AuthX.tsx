import { FaXTwitter } from "react-icons/fa6";

const AuthX = () => {
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
            <FaXTwitter size={22} className="text-black dark:text-white" />
        </button>
    );
};

export default AuthX;
