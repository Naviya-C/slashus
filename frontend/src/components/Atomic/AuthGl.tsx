import { FcGoogle } from "react-icons/fc";

function AuthGl(){
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
            <FcGoogle size={28} />
        </button>
    );
}

export default AuthGl;