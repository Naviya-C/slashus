import { FaFacebookF } from "react-icons/fa";

function AuthFB(){
    return(
        <button
            className="
                w-14
                h-14
                border
                border-slate-300
                rounded-xl
                flex
                items-center
                justify-center
                hover:bg-slate-50
                transition
                cursor-pointer
            "
        >
            <FaFacebookF
                size={24}
                className="text-blue-600"
            />
        </button>
    );
}

export default AuthFB;