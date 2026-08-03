interface AuthButtonProp{
    name: string
    type?: "button" | "submit";
    disabled?:boolean
}

const AuthButton = (props: AuthButtonProp) => {
    return(
        <button
            type = {props.type}
            disabled = {props.disabled}
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
            {props.name}
        </button>
    );
}


export default AuthButton;