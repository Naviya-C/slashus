import { FaXTwitter } from "react-icons/fa6";

function AuthX(){
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
            <FaXTwitter
                size={22}
                className="text-black"
            />
        </button>
    );
}

export default AuthX;