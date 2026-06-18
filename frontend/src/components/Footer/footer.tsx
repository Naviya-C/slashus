function Footer() {
    return (
        <footer
            className="
                bg-teal-600
                w-full
                h-28
                rounded-t-4xl
                mt-8
            "
        >
            <div
                className="
                    flex
                    flex-col
                    justify-center
                    items-center
                    h-full
                "
            >
                <p className="text-white">
                    Powered By
                </p>

                <p
                    className="
                        ml-60
                        font-bold
                        text-blue-900
                        font-poppins
                        text-3xl
                        leading-none
                    "
                >
                    Apeir
                    <span className="text-white">o</span>
                    naut
                </p>
            </div>
        </footer>
    );
}

export default Footer;