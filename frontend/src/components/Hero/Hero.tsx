import { Sparkles } from "lucide-react";

function Hero() {
    return (
        <section 
            className = 
                "flex min-h-[50vh] \
                flex-col \
                items-center \
                justify-center"
        >
            <h1 
                className=
                    "text-center \
                    text-7xl \
                    font-bold \
                    bg-gradient-to-r \
                    from-blue-500 \
                    to-cyan-400 \
                    bg-clip-text \
                    text-transparent"
            >
                Learning Made Easy
            </h1>

            <p 
                className=
                    "mt-4 \
                    max-w-4xl \
                    text-center \
                    text-lg \
                    text-gray-600"
                >
                Transform educational resources into interactive quizzes and practice questions instantly. 
                Enhance knowledge retention and assessment through automated, personalized learning experiences.
            </p>

            <button 
                className="flex mt-8 \
                    items-center \
                    gap-2 \
                    rounded-full \
                    bg-gray-100 \
                    px-5 \
                    py-3 \
                    text-sm \
                    font-medium \
                    text-purple-700 \
                    shadow-md \
                    hover:shadow-lg \
                    cursor-pointer"
            >
                <Sparkles size={16} />
                <span>Try Slash</span>
            </button>
        </section>
    );
}

export default Hero;