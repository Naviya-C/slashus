import darkLogo from "../../assets/logo_black.svg";
import lightLogo from "../../assets/logo_white.svg";

type Props = {
    theme?: "light" | "dark";
};

const Logo = ({ theme = "light" }: Props) => {
    return (
        <div className="flex items-center gap-2">
            <img
                src={theme === "dark" ? lightLogo : darkLogo}
                alt=""
                className="h-10 rounded-xl sm:h-11"
            />
            <h3
                className={`text-lg font-bold sm:text-xl ${theme === "dark" ? "text-white" : "text-neutral-950"}`}
            >
                SLASH<span className="text-blue-500">US</span>
            </h3>
        </div>
    );
};

export default Logo;
