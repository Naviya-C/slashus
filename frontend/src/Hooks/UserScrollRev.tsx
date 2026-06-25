import { useEffect, useRef, useState } from "react";

/* ---------------------------------- */
/* useInView                          */
/* ---------------------------------- */

export function useInView(
  threshold = 0.2
): [React.RefObject<HTMLDivElement | null>, boolean] {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
        }
      },
      {
        threshold,
      }
    );

    observer.observe(el);

    return () => observer.disconnect();
  }, [threshold]);

  return [ref, inView];
}

/* ---------------------------------- */
/* useCountUp                         */
/* ---------------------------------- */

export function useCountUp(
  target: number,
  duration = 1200,
  started = true
): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!started) {
      setValue(0);
      return;
    }

    let startTime: number | null = null;
    let frameId: number;

    const animate = (timestamp: number) => {
      if (!startTime) {
        startTime = timestamp;
      }

      const progress = Math.min(
        (timestamp - startTime) / duration,
        1
      );

      setValue(Math.floor(progress * target));

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      }
    };

    frameId = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(frameId);
  }, [target, duration, started]);

  return value;
}

/* ---------------------------------- */
/* useScrollReveal                    */
/* ---------------------------------- */

export function useScrollReveal() {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;

    const elements =
      root.querySelectorAll<HTMLElement>(".reveal");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.15,
      }
    );

    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return ref;
}

/* ---------------------------------- */
/* useTypewriter                      */
/* ---------------------------------- */

export function useTypewriter(
  lines: string[],
  typingSpeed = 50,
  deletingSpeed = 30,
  pause = 2000
): string {
  const [lineIndex, setLineIndex] = useState(0);
  const [text, setText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = lines[lineIndex];

    let timeout: ReturnType<typeof setTimeout>;

    if (!deleting && text.length < current.length) {
      timeout = setTimeout(() => {
        setText(current.slice(0, text.length + 1));
      }, typingSpeed);
    } else if (!deleting && text === current) {
      timeout = setTimeout(() => {
        setDeleting(true);
      }, pause);
    } else if (deleting && text.length > 0) {
      timeout = setTimeout(() => {
        setText(current.slice(0, text.length - 1));
      }, deletingSpeed);
    } else if (deleting && text.length === 0) {
      setDeleting(false);
      setLineIndex((prev) => (prev + 1) % lines.length);
    }

    return () => clearTimeout(timeout);
  }, [
    text,
    deleting,
    lineIndex,
    lines,
    typingSpeed,
    deletingSpeed,
    pause,
  ]);

  return text;
}