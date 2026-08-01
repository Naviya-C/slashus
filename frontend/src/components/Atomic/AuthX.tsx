import { FaXTwitter } from "react-icons/fa6";

function AuthX(){
    return(  
        <button
            disabled
            className="
                w-14
                h-14
                border
                border-slate-300
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
            <FaXTwitter
                size={22}
                className="text-black"
            />
        </button>
    );
}

export default AuthX;