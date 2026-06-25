import Logo from "../Atomic/Logo";

const LINKS = {
  product: [
    "features",
    "auto_marking",
    "document_qa",
    "analytics",
    "api",
  ],
  company: [
    "about",
    "blog",
    "careers",
    "contact",
  ],
  legal: [
    "privacy",
    "terms",
    "security",
  ],
};

export default function Footer() {
  return (
    <footer className="bg-[#09090f] px-8 py-14 text-white/35 mt-12">
      <div className="mx-auto max-w-7xl">

        {/* Top */}
        <div
          className="
            mb-10
            grid
            grid-cols-1
            gap-10
            border-b
            border-white/5
            pb-10
            sm:grid-cols-2
            lg:grid-cols-[1.4fr_1fr_1fr_1fr]
          "
        >
          {/* Brand */}
          <div>
            <Logo/>

            <p className="mt-3 max-w-sm text-sm leading-7 text-white/35">
              AI-powered Q&amp;A and auto marking for the modern educator.
              Built for Sri Lanka and the world.
            </p>
          </div>

          {/* Columns */}
          {Object.entries(LINKS).map(([col, items]) => (
            <div key={col}>
              <h4
                className="
                  mb-4
                  text-[11px]
                  font-bold
                  uppercase
                  tracking-[0.1em]
                  text-white/50
                "
              >
                {col}
              </h4>

              <ul className="flex flex-col gap-2">
                {items.map((item) => (
                  <li key={item}>
                    <a
                      href="#"
                      className="
                        text-sm
                        text-white/30
                        transition-colors
                        duration-200
                        hover:text-white/70
                      "
                    >
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div
          className="
            flex
            flex-col
            items-center
            justify-between
            gap-4
            text-center
            text-xs
            sm:flex-row
            sm:text-left
          "
        >
          <span>
            © 2026 slashus. all rights reserved.
          </span>

          <div className="flex gap-5">
            {["twitter", "linkedin", "github"].map((social) => (
              <a
                key={social}
                href="#"
                className="
                  text-white/30
                  transition-colors
                  duration-200
                  hover:text-white/60
                "
              >
                {social}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}