import illo from "../../assets/auth-illustration.svg";

const AuthFooter = () => {
    return(
        <div
            className="
                relative
                h-[300px]
                rounded-3xl
                bg-gradient-to-br
                from-indigo-600
                via-violet-500
                to-cyan-500
            "
        >
            <img
                src={illo}
                alt=""
                className="
                    absolute
                    -bottom-16
                    left-1/2
                    -translate-x-1/2
                    w-[175%]
                    max-w-none
                    pointer-events-none
                    opacity-70
                "
            />
        </div>
    );
}

export default AuthFooter;