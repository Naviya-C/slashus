import styles from "./DemoWindow.module.css";

export default function DemoWindow() {
  return (
    <div className="mx-auto mt-14 max-w-[1260px] px-6">
      <div className="relative">
        <div className="overflow-hidden rounded-3xl border border-white/5 bg-[#0c0c14] shadow-2xl">

          {/* Title Bar */}
          <div className="flex items-center gap-2 border-b border-white/5 bg-white/[0.015] h-25 px-5 py-3">
            <span className="h-[10px] w-[10px] rounded-full bg-[#ff5f57]" />
            <span className="h-[10px] w-[10px] rounded-full bg-[#ffbd2e]" />
            <span className="h-[10px] w-[10px] rounded-full bg-[#28c840]" />

            <span className="ml-3 flex-1 text-[11px] text-white/20">
              slashus.com/dashboard · biology_exam_2025.session
            </span>
          </div>

          {/* Body */}
          <div
            className="
              grid
              min-h-[430px]
              grid-cols-1
              md:grid-cols-[1fr_1fr]
              lg:grid-cols-[190px_1fr_1fr]
            "
          >
            {/* ================================= */}
            {/* Workspace */}
            {/* ================================= */}
            <div
              className="
                hidden
                lg:flex
                flex-col
                border-r
                border-white/5
                bg-black/20
              "
            >
              <div className="border-b border-white/5 px-4 py-3">
                <span className="text-[9px] font-bold uppercase tracking-[0.12em] text-white/20">
                  workspace
                </span>
              </div>

              {/* Local */}
              <div className="flex items-center gap-2 px-4 py-2">
                <div className="h-[5px] w-[5px] rounded-full bg-emerald-500" />
                <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-emerald-500">
                  local
                </span>
              </div>

              <div className="px-4 py-1 text-[11px] text-white/40">
                📁 biology_2025/
              </div>

              <div className="mx-1 flex items-center rounded bg-emerald-500/15 px-4 py-1 text-[11px] text-white/90">
                💬 local_chat
                <span className="ml-auto rounded-full bg-emerald-500 px-1.5 text-[8px] text-white">
                  2
                </span>
              </div>

              <div className="mx-1 px-4 py-1 text-[11px] text-white/40">
                📄 resources_(4)
              </div>

              <div className="mt-3 px-4 py-1 text-[11px] text-white/40">
                📁 chemistry_2024/
              </div>

              <div className="mx-1 px-4 py-1 text-[11px] text-white/40">
                💬 local_chat
              </div>

              {/* Global */}
              <div className="mt-auto border-t border-white/5 pt-3">
                <div className="flex items-center gap-2 px-4 py-2">
                  <div className="h-[5px] w-[5px] rounded-full bg-yellow-500" />
                  <span className="text-[9px] font-bold uppercase tracking-[0.1em] text-yellow-500">
                    global
                  </span>
                </div>

                <div className="mx-1 flex items-center rounded bg-yellow-500/10 px-4 py-1 text-[11px] text-white/80">
                  🌎 all_resources
                  <span className="ml-auto rounded-full bg-yellow-500 px-1.5 text-[8px] text-black">
                    5
                  </span>
                </div>

                <div className="mx-1 px-4 py-1 text-[11px] text-white/40">
                  📊 auto_marking
                </div>

                <div className="mx-1 px-4 py-1 text-[11px] text-white/40">
                  🗂 analytics
                </div>
              </div>
            </div>

            {/* ================================= */}
            {/* Chat */}
            {/* ================================= */}
            <div className="flex flex-col border-r border-white/5">
              <div className="flex items-center justify-between border-b border-white/5 bg-white/[0.012] px-4 py-3">
                <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-emerald-500">
                  local_chat — biology_2025/
                </span>

                <span className="text-[10px] text-white/20">
                  folder-scoped · 4 resources
                </span>
              </div>

              <div className="flex flex-1 flex-col gap-3 p-4">

                {/* AI */}
                <div className="flex gap-2">
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-[9px] font-bold text-emerald-500">
                    AI
                  </div>

                  <div className="max-w-[80%] rounded-lg rounded-bl-sm bg-white/5 px-3 py-2 text-[12px] text-white/70">
                    Hello. I have access to 4 resources in biology_2025/.
                  </div>
                </div>

                {/* User */}
                <div className="flex flex-row-reverse gap-2">
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-yellow-500/20 text-[9px] font-bold text-yellow-500">
                    U
                  </div>

                  <div className="max-w-[80%] rounded-lg rounded-br-sm bg-emerald-500/20 px-3 py-2 text-[12px] text-white/85">
                    Explain cellular respiration briefly
                  </div>
                </div>

                {/* AI */}
                <div className="flex gap-2">
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-[9px] font-bold text-emerald-500">
                    AI
                  </div>

                  <div className="max-w-[80%] rounded-lg rounded-bl-sm bg-white/5 px-3 py-2 text-[12px] text-white/70">
                    Cellular respiration converts glucose into ATP via glycolysis,
                    Krebs cycle, and oxidative phosphorylation.
                  </div>
                </div>
              </div>

              {/* Input */}
              <div className="flex items-center gap-2 border-t border-white/5 bg-black/20 px-3 py-2">
                <div className="flex-1 text-[12px] text-white/40">
                  Ask about biology_2025 resources
                  <span className={styles.cursorBlink} />
                </div>

                <button className="flex h-[22px] w-[22px] items-center justify-center rounded bg-emerald-500 text-white">
                  →
                </button>
              </div>
            </div>

            {/* ================================= */}
            {/* Assessment */}
            {/* ================================= */}
            <div className="flex flex-col">
              <div className="flex items-center justify-between border-b border-white/5 bg-white/[0.012] px-4 py-3">
                <span className="text-[11px] font-bold uppercase tracking-[0.08em] text-yellow-500">
                  assessment — q&a
                </span>

                <span className="text-[10px] text-white/20">
                  3 questions · auto-mark on
                </span>
              </div>

              <div className="flex flex-1 flex-col gap-3 p-4">
                <div className="rounded-lg border border-white/5 bg-white/[0.03] p-3">
                  <div className="mb-2 text-[9px] font-bold uppercase tracking-[0.08em] text-yellow-500/70">
                    question_01
                  </div>

                  <div className="mb-3 text-[12px] text-white/60">
                    What is the primary function of mitochondria?
                  </div>

                  <div className="rounded border border-white/10 bg-white/5 p-2 text-[11px] text-white/70">
                    ATP production through oxidative phosphorylation...
                  </div>

                  <div className="mt-3 flex items-center gap-2">
                    <div className="h-[3px] flex-1 overflow-hidden rounded bg-white/5">
                      <div className="h-full w-[91%] rounded bg-emerald-500" />
                    </div>

                    <span className="text-[10px] font-bold text-emerald-500">
                      91%
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-white/5 bg-black/20 px-4 py-3">
                <span className="text-[11px] text-white/20">
                  1_of_3 answered
                </span>

                <button className="rounded bg-emerald-500 px-3 py-1 text-[11px] font-bold text-[#0c0c14]">
                  submit_&_mark →
                </button>
              </div>
            </div>
          </div>

          <div className={styles.scanLine} />
        </div>
      </div>
    </div>
  );
}