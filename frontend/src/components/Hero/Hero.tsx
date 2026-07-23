import { Sparkles, ArrowRight, Play } from "lucide-react";

import { useNav } from "../../Hooks/useNav";

function Hero() {

  const { goToLogin } = useNav();

  return (
    <section className="
                    relative 
                    overflow-hidden 
                    flex min-h-[85vh] 
                    flex-col items-center 
                    justify-center 
                    px-6 py-20
                "
    >

      {/* Ambient Background */}
      <div className="
                absolute 
                left-[-10rem] 
                top-[-10rem] 
                h-96 w-96 
                rounded-full 
                bg-cyan-400/20 
                blur-3xl
            " 
        />
      <div className="
                absolute 
                right-[-8rem] 
                bottom-[-8rem] 
                h-96 w-96 
                rounded-full 
                bg-blue-500/20 
                blur-3xl
            "
        />


      {/* Headline */}
      <h1 className="
                max-w-5xl 
                text-center 
                font-bold 
                leading-tight
            "
        >
            <span className="
                        block 
                        text-5xl 
                        md:text-7xl 
                        text-gray-900
                    "
            >
                Generate Questions
            </span>

        <span className="mt-2 block bg-gradient-to-r from-green-500 to-emerald-400 bg-clip-text text-5xl text-transparent md:text-7xl">
          Mark Instantly
        </span>

        <span className="mt-2 block bg-gradient-to-r from-yellow-500 to-orange-400 bg-clip-text text-5xl text-transparent md:text-7xl">
          Evaluate Your Self & Learn
        </span>
      </h1>

      {/* Description */}
      <p className="mt-8 max-w-4xl text-center text-lg leading-8 text-gray-600 md:text-xl">
        Slashus is an AI-powered Q&amp;A and auto-marking platform that
        understands your documents, generates intelligent assessments, and
        grades with human-level accuracy.
      </p>

      {/* Actions */}
      <div className="
                mt-10 
                flex 
                flex-col 
                gap-6 
                sm:flex-row
            "
        >
        <button 
              onClick={goToLogin}
              className="
                    flex 
                    items-center 
                    justify-center 
                    gap-2 
                    rounded-full 
                    bg-gradient-to-r 
                    from-blue-600 to-cyan-500 
                    px-7 py-4 
                    font-semibold 
                    text-white 
                    shadow-lg 
                    transition 
                    hover:scale-105
                    hover:cursor-pointer
                "
              >
          <Sparkles size={18} />
          Try Slash Free
          <ArrowRight size={18} />
        </button>

        <button className="
                    flex 
                    items-center 
                    justify-center 
                    gap-2 
                    rounded-full 
                    border 
                    border-gray-200 
                    bg-white 
                    px-7 py-4 
                    font-semibold 
                    text-gray-700 
                    shadow-sm 
                    transition 
                    hover:bg-gray-50
                    hover:scale-105
                    hover:cursor-pointer
                "
        >
          <Play size={18} />
          See How It Works
        </button>
      </div>
    </section>
  );
}

export default Hero;