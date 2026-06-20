interface AuthButtonProp{
    name: string
}

function AuthButton({name}: AuthButtonProp){
    return(
        <button
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
            "
        >
            {name}
        </button>
    );
}

export default AuthButton;