interface AuthButtonProp {
    name: string;
    type?: "button" | "submit";
    disabled?: boolean;
}

const AuthButton = (props: AuthButtonProp) => {
    return (
        <button
            type={props.type}
            disabled={props.disabled}
            className="
                w-full
                h-14
                rounded-full
                bg-slate-950
                text-white
                font-semibold
                transition
                cursor-pointer
                hover:bg-slate-800
                disabled:opacity-50
                disabled:cursor-not-allowed
                dark:bg-white
                dark:text-neutral-950
                dark:hover:bg-neutral-200
            "
        >
            {props.name}
        </button>
    );
};

export default AuthButton;
