import {
	Upload,
	Database,
	MessageSquare,
	Sparkles,
	Clock,
	PanelLeft,
} from "lucide-react";

import upload from "../../assets/upload.png"
import chat from "../../assets/chat.png"
import qgen from "../../assets/qGen.png"
import load from "../../assets/load.gif"

type Step = {
	number: string;
	title: string;
	description: string;
	detail?: string;
	icon: React.ReactNode;
	/** Put screenshot path here" */
	imageSrc?: string;
	imageAlt: string;
};

const steps: Step[] = [
  {
    number: "01",
    title: "Upload your document",
    description:
      "Drop a PDF, DOCX, or text file into the chat dashboard. The system reads the full content and prepares it for understanding.",
    detail: "Supported: PDF, DOCX, TXT, and more.",
    icon: <Upload className="h-5 w-5" />,
    imageSrc: upload, 
    imageAlt: "Upload file screen",
  },
  {
    number: "02",
    title: "Read, embed & store",
    description:
      "Your file is split into chunks, converted into embeddings, and stored in a vector database. This is what lets the chatbot answer from your content — not generic web knowledge.",
    detail: "Usually takes about 3 minutes depending on file size.",
    icon: <Database className="h-5 w-5" />,
    imageSrc: load, 
    imageAlt: "Embedding and indexing progress",
  },
  {
    number: "03",
    title: "Ask anything about the file",
    description:
      "Once indexing is done, type a question in the chat. The system retrieves the most relevant passages (RAG) and generates an answer grounded in your document.",
    icon: <MessageSquare className="h-5 w-5" />,
    imageSrc: chat,
    imageAlt: "Chat asking questions about the document",
  },
  {
    number: "04",
    title: "Generate questions",
    description:
      "Need ideas? One click generates relevant questions from your document. They appear in the left vertical sidebar so you can pick one and jump straight into an answer.",
    icon: <Sparkles className="h-5 w-5" />,
    imageSrc: qgen,
    imageAlt: "Generated questions in the left sidebar",
  },
];

function ImageSlot({
  src,
  alt,
  caption,
}: {
  src?: string;
  alt: string;
  caption?: string;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-gray-50 shadow-sm">
      {src ? (
        <img
          src={src}
          alt={alt}
          className="h-full w-full object-cover object-top"
        />
      ) : (
        <div className="flex aspect-[16/10] flex-col items-center justify-center gap-2 bg-gradient-to-br from-gray-50 to-gray-100 px-6 text-center">
          <PanelLeft className="h-8 w-8 text-gray-300" />
          <p className="text-sm font-medium text-gray-400">Screenshot placeholder</p>
          <p className="text-xs text-gray-400">{alt}</p>
        </div>
      )}
      {caption && (
        <p className="border-t border-gray-100 bg-white px-4 py-2 text-center text-xs text-gray-500">
          {caption}
        </p>
      )}
    </div>
  );
}

export default function HowIt() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 md:px-8 md:py-50">
      {/* Header */}
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-semibold uppercase tracking-wider text-gray-500">
          How it works
        </p>
        <h2 className="mt-3 text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
          From upload to answers in minutes
        </h2>
        <p className="mt-4 text-base text-gray-600 md:text-lg">
          A RAG chatbot that reads your files, builds a private knowledge base,
          and lets you ask or generate questions grounded in your content.
        </p>
      </div>

      {/* Time callout */}
      <div className="mx-auto mt-8 flex max-w-xl items-center justify-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
        <Clock className="h-4 w-4 shrink-0" />
        <span>
          Indexing usually takes <strong>~3 minutes</strong> after you upload a
          file. After that, chat is instant.
        </span>
      </div>

      {/* Steps */}
      <div className="mt-16 space-y-20 md:space-y-28">
        {steps.map((step, i) => {
          const reverse = i % 2 === 1;
          return (
            <div
              key={step.number}
              className={`
                grid items-center gap-10
                md:grid-cols-2 md:gap-14
              `}
            >
              {/* Text */}
              <div className={reverse ? "md:order-2" : undefined}>
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-900 text-sm font-bold text-white">
                    {step.number}
                  </span>
                  <span className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700">
                    {step.icon}
                  </span>
                </div>

                <h3 className="mt-5 text-2xl font-bold text-gray-900">
                  {step.title}
                </h3>
                <p className="mt-3 text-base leading-relaxed text-gray-600">
                  {step.description}
                </p>
                {step.detail && (
                  <p className="mt-3 text-sm font-medium text-gray-500">
                    {step.detail}
                  </p>
                )}
              </div>

              {/* Image / screenshot slot */}
              <div className={reverse ? "md:order-1" : undefined}>
                <ImageSlot
                  src={step.imageSrc}
                  alt={step.imageAlt}
                  caption={step.imageAlt}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Mini flow strip */}
      <div className="mt-20 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm md:p-10">
        <h3 className="text-center text-lg font-semibold text-gray-900">
          	The full loop
        </h3>
        <div className="mt-8 flex flex-col items-stretch justify-between gap-4 md:flex-row md:items-center">
          {[
            { icon: <Upload className="h-5 w-5" />, label: "Upload file" },
            { icon: <Database className="h-5 w-5" />, label: "Embed & store (~3 min)" },
            { icon: <MessageSquare className="h-5 w-5" />, label: "Ask questions" },
            { icon: <Sparkles className="h-5 w-5" />, label: "Generate questions → left bar" },
          ].map((item) => (
            <div key={item.label} className="flex flex-1 items-center gap-3 md:flex-col md:text-center">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-gray-200 bg-gray-50 text-gray-800">
                {item.icon}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{item.label}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-15 text-center text-sm text-gray-500">
          Generated questions show up in the <strong>left vertical sidebar</strong> of
          the chat dashboard — click any one to run it instantly.
        </p>
      </div>
    </section>
  );
}