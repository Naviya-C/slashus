interface AuthButtonProp{
    name: string
    type?: "button" | "submit";
    disabled?:boolean
}

function AuthButton({name, type = "button", disabled = false}: AuthButtonProp){
    return(
        <button
            type = {type}
            disabled = {disabled}
            className="
                mt-8
                w-full
                h-14
                rounded-full
                bg-slate-950
                text-white
                font-semibold
                hover:bg-slate-800
                transition
                cursor-pointer
                disabled:opacity-50
                disabled:cursor-not-allowed
            "
        >
            {name}
        </button>
    );
}

export default AuthButton;