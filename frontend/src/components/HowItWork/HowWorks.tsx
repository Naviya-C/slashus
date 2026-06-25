import { useScrollReveal } from "../../Hooks/UserScrollRev";

const STEPS = [
  {
    num: "// 01",
    className: "text-emerald-500 bg-emerald-500/10",
    title: "upload.documents()",
    desc:
      "Drop in PDFs, textbooks, past papers, or notes. Handles legacy Sinhala fonts, scanned pages, and mixed-language content.",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
    ),
  },
  {
    num: "// 02",
    className: "text-cyan-500 bg-cyan-500/10",
    title: "rag.index()",
    desc:
      "Hybrid RAG pipeline chunks, embeds, and indexes content so answers are grounded in your documents — never hallucinated.",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
  },
  {
    num: "// 03",
    className: "text-blue-500 bg-blue-500/10",
    title: "chat.query()",
    desc:
      "Query locally (folder-scoped) or globally (all resources). Every response cites the exact page it came from.",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
  {
    num: "// 04",
    className: "text-yellow-500 bg-yellow-500/10",
    title: "mark.auto()",
    desc:
      "Submit answers and receive a composite score from three independent AI scorers — semantic, NLI, and LLM judge — in seconds.",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
    ),
  },
];

export default function HowItWorks() {
  const ref = useScrollReveal();

  return (
    <section
      id="how"
      ref={ref}
      className="px-6 py-28"
    >
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-500">
            how_it_works
          </div>

          <h2 className="text-4xl font-bold leading-tight text-gray-900 md:text-6xl">
            From document to insight
            <br />
            in minutes.
          </h2>

          <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-gray-600">
            Upload any PDF. Slashus indexes it, scopes it to a workspace
            folder, and lets you ask questions or run auto-marked assessments.
          </p>
        </div>

        {/* Cards */}
        <div className="mt-20 grid gap-8 md:grid-cols-2 xl:grid-cols-4">
          {STEPS.map((step) => (
            <div
              key={step.title}
              className="
                rounded-3xl
                border
                border-gray-200
                bg-white
                p-8
                shadow-sm
                transition-all
                duration-300
                hover:-translate-y-2
                hover:shadow-xl
              "
            >
              <div className="text-xs font-bold tracking-[0.2em] text-gray-400">
                {step.num}
              </div>

              <div
                className={`
                  mt-6
                  flex
                  h-14
                  w-14
                  items-center
                  justify-center
                  rounded-2xl
                  ${step.className}
                `}
              >
                <div className="h-6 w-6">
                  {step.icon}
                </div>
              </div>

              <h3 className="mt-6 text-lg font-semibold text-gray-900">
                {step.title}
              </h3>

              <p className="mt-4 text-sm leading-7 text-gray-600">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}