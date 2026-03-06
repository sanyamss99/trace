import { useState, useEffect, useRef } from 'react';
import { useInView } from '../hooks/useInView';
import { useTheme } from '../hooks/useTheme';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

// ─── Shared ───────────────────────────────────────────────────────

function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button
      onClick={toggle}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      className="flex items-center justify-center w-9 h-9 rounded-lg bg-surface-secondary/60 backdrop-blur-sm border border-border text-text-secondary hover:text-text-primary hover:bg-surface-tertiary transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
    >
      {theme === 'light' ? (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  );
}

function GoogleButton() {
  function handleGoogleLogin() {
    window.location.href = `${API_BASE}/auth/google`;
  }

  return (
    <button
      type="button"
      onClick={handleGoogleLogin}
      className="flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-800 border border-gray-300 rounded-md px-6 py-2.5 text-sm font-medium transition-colors cursor-pointer"
    >
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
      </svg>
      Sign in with Google
    </button>
  );
}

function AnimatedBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
      {/* Base */}
      <div
        className="absolute inset-0"
        style={{
          background: `radial-gradient(ellipse 90% 70% at 50% 35%, var(--raw-surface-secondary) 0%, var(--raw-surface-primary) 100%)`,
        }}
      />

      {/* ── Aurora bands ── */}
      <div
        className="absolute -inset-x-1/2 top-[5%] h-[700px]"
        style={{
          background: `linear-gradient(90deg, transparent 0%, rgba(var(--raw-accent-rgb), 0.2) 10%, rgba(var(--raw-accent-rgb), 0.35) 30%, rgba(var(--raw-warning-rgb), 0.15) 50%, rgba(var(--raw-accent-rgb), 0.3) 70%, rgba(var(--raw-accent-rgb), 0.15) 90%, transparent 100%)`,
          filter: 'blur(50px)',
          animation: 'landing-aurora 18s ease-in-out infinite',
        }}
      />
      <div
        className="absolute -inset-x-1/2 top-[45%] h-[600px]"
        style={{
          background: `linear-gradient(90deg, transparent 0%, rgba(var(--raw-warning-rgb), 0.15) 15%, rgba(var(--raw-accent-rgb), 0.25) 40%, rgba(var(--raw-warning-rgb), 0.18) 65%, rgba(var(--raw-accent-rgb), 0.12) 85%, transparent 100%)`,
          filter: 'blur(55px)',
          animation: 'landing-aurora 24s ease-in-out infinite reverse',
        }}
      />
      <div
        className="absolute -inset-x-1/3 -top-[3%] h-[350px]"
        style={{
          background: `linear-gradient(100deg, transparent 0%, rgba(var(--raw-accent-rgb), 0.15) 35%, rgba(var(--raw-accent-rgb), 0.25) 55%, rgba(var(--raw-warning-rgb), 0.1) 75%, transparent 100%)`,
          filter: 'blur(40px)',
          animation: 'landing-aurora 14s ease-in-out infinite',
          animationDelay: '-5s',
        }}
      />
      <div
        className="absolute -inset-x-1/2 bottom-[0%] h-[400px]"
        style={{
          background: `linear-gradient(90deg, transparent 0%, rgba(var(--raw-accent-rgb), 0.12) 30%, rgba(var(--raw-accent-rgb), 0.2) 50%, rgba(var(--raw-accent-rgb), 0.12) 70%, transparent 100%)`,
          filter: 'blur(60px)',
          animation: 'landing-aurora 20s ease-in-out infinite',
          animationDelay: '-10s',
        }}
      />

      {/* ── Gradient orbs ── */}
      <div className="absolute rounded-full" style={{ width: '1000px', height: '1000px', top: '-5%', left: '0%', background: 'radial-gradient(circle, rgba(var(--raw-accent-rgb), 0.3) 0%, rgba(var(--raw-accent-rgb), 0.1) 30%, transparent 60%)', animation: 'landing-orb-drift-1 20s ease-in-out infinite' }} />
      <div className="absolute rounded-full" style={{ width: '800px', height: '800px', top: '30%', right: '-5%', background: 'radial-gradient(circle, rgba(var(--raw-warning-rgb), 0.2) 0%, rgba(var(--raw-warning-rgb), 0.06) 30%, transparent 60%)', animation: 'landing-orb-drift-2 26s ease-in-out infinite' }} />
      <div className="absolute rounded-full" style={{ width: '900px', height: '900px', bottom: '0%', left: '25%', background: 'radial-gradient(circle, rgba(var(--raw-accent-rgb), 0.22) 0%, rgba(var(--raw-accent-rgb), 0.06) 30%, transparent 60%)', animation: 'landing-orb-drift-3 22s ease-in-out infinite' }} />
      <div className="absolute rounded-full" style={{ width: '600px', height: '600px', top: '10%', right: '20%', background: 'radial-gradient(circle, rgba(var(--raw-accent-rgb), 0.35) 0%, rgba(var(--raw-accent-rgb), 0.12) 25%, transparent 50%)', animation: 'landing-orb-drift-2 16s ease-in-out infinite reverse' }} />
      <div className="absolute rounded-full" style={{ width: '450px', height: '450px', top: '55%', left: '8%', background: 'radial-gradient(circle, rgba(var(--raw-warning-rgb), 0.18) 0%, rgba(var(--raw-warning-rgb), 0.05) 30%, transparent 55%)', animation: 'landing-orb-drift-1 12s ease-in-out infinite reverse' }} />
      <div className="absolute rounded-full" style={{ width: '500px', height: '500px', top: '75%', right: '15%', background: 'radial-gradient(circle, rgba(var(--raw-accent-rgb), 0.18) 0%, rgba(var(--raw-accent-rgb), 0.05) 30%, transparent 55%)', animation: 'landing-orb-drift-3 15s ease-in-out infinite reverse' }} />

      {/* ── Grid ── */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `linear-gradient(rgba(var(--raw-accent-rgb), 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(var(--raw-accent-rgb), 0.05) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(var(--raw-accent-rgb), 0.18) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          animation: 'landing-dot-pulse 5s ease-in-out infinite',
        }}
      />

      {/* Top edge glow */}
      <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ background: 'linear-gradient(90deg, transparent 0%, rgba(var(--raw-accent-rgb), 0.6) 25%, rgba(var(--raw-warning-rgb), 0.4) 50%, rgba(var(--raw-accent-rgb), 0.6) 75%, transparent 100%)' }} />
      <div className="absolute top-0 left-0 right-0 h-[40px]" style={{ background: 'linear-gradient(180deg, rgba(var(--raw-accent-rgb), 0.15) 0%, transparent 100%)' }} />

      {/* Vignette */}
      <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 80% 60% at 50% 45%, transparent 0%, rgba(0,0,0,0.12) 100%)' }} />
    </div>
  );
}

function EditorWindow({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface-secondary/80 backdrop-blur-md border border-border rounded-lg overflow-hidden shadow-lg">
      <div className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-2.5 border-b border-border">
        <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-red-500/70" />
        <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-yellow-500/70" />
        <span className="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-green-500/70" />
        <span className="text-text-muted text-[10px] sm:text-xs ml-1.5 sm:ml-2 font-mono">{title}</span>
      </div>
      <div className="p-3 sm:p-4 overflow-x-auto">{children}</div>
    </div>
  );
}

// ─── Section 1: Hero ──────────────────────────────────────────────

const CODE_LINES = [
  { text: 'from usetrace import tracer', color: 'default' as const },
  { text: '', color: 'default' as const },
  { text: '@tracer.observe()', color: 'decorator' as const },
  { text: 'async def answer(question: str):', color: 'default' as const },
  { text: '    docs = retrieve(question)', color: 'default' as const },
  { text: '    context = "\\n".join(docs)', color: 'default' as const },
  { text: '    prompt = f"Answer: {context}"', color: 'default' as const },
  { text: '    return await llm(prompt)', color: 'default' as const },
];

function colorize(text: string, lineColor: string): React.ReactNode[] {
  if (lineColor === 'decorator') {
    return [<span key="d" className="text-warning">{text}</span>];
  }

  const keywords = ['from', 'import', 'async', 'def', 'return', 'await'];
  const tokens: { text: string; type: 'keyword' | 'string' | 'plain' }[] = [];
  let i = 0;

  while (i < text.length) {
    if (text[i] === '"' || text[i] === "'" || (text[i] === 'f' && text[i + 1] === '"')) {
      const isF = text[i] === 'f';
      const quote = isF ? text[i + 1] : text[i];
      const start = i;
      i = isF ? i + 2 : i + 1;
      while (i < text.length && text[i] !== quote) i++;
      i++;
      tokens.push({ text: text.slice(start, i), type: 'string' });
      continue;
    }

    const wordMatch = text.slice(i).match(/^[a-zA-Z_]\w*/);
    if (wordMatch) {
      tokens.push({
        text: wordMatch[0],
        type: keywords.includes(wordMatch[0]) ? 'keyword' : 'plain',
      });
      i += wordMatch[0].length;
      continue;
    }

    const plainStart = i;
    i++;
    tokens.push({ text: text.slice(plainStart, i), type: 'plain' });
  }

  return tokens.map((tok, idx) => {
    const cls =
      tok.type === 'keyword' ? 'text-accent' :
      tok.type === 'string' ? 'text-success' :
      'text-text-primary';
    return <span key={idx} className={cls}>{tok.text}</span>;
  });
}

function HeroCode() {
  const [charCount, setCharCount] = useState(0);
  const totalChars = CODE_LINES.reduce((sum, l) => sum + l.text.length + 1, 0);

  useEffect(() => {
    if (charCount >= totalChars) return;
    const timer = setInterval(() => {
      setCharCount((c) => Math.min(c + 1, totalChars));
    }, 30);
    return () => clearInterval(timer);
  }, [charCount, totalChars]);

  let remaining = charCount;
  const visibleLines: { text: string; color: string }[] = [];

  for (const line of CODE_LINES) {
    const lineLen = line.text.length + 1;
    if (remaining <= 0) break;
    const chars = Math.min(remaining, line.text.length);
    visibleLines.push({ text: line.text.slice(0, chars), color: line.color });
    remaining -= lineLen;
  }

  const isDecoratorVisible = visibleLines.length > 2 && visibleLines[2].text.length > 0;

  return (
    <EditorWindow title="answer.py">
      <pre className="font-mono text-[10px] sm:text-xs leading-5 sm:leading-6 min-h-[160px] sm:min-h-[200px]">
        {visibleLines.map((line, i) => (
          <div
            key={i}
            className="transition-all duration-400"
            style={
              i === 2 && isDecoratorVisible
                ? {
                    backgroundColor: 'rgba(var(--raw-accent-rgb), 0.08)',
                    borderLeft: '2px solid var(--raw-accent)',
                    paddingLeft: '8px',
                    marginLeft: '-10px',
                  }
                : {}
            }
          >
            {colorize(line.text, line.color)}
            {i === visibleLines.length - 1 && (
              <span
                className="inline-block w-[2px] h-4 bg-text-primary align-middle ml-px"
                style={{ animation: 'landing-cursor-blink 500ms step-end infinite' }}
              />
            )}
          </div>
        ))}
      </pre>
    </EditorWindow>
  );
}

const TRACE_SPANS = [
  { name: 'answer', type: 'generic', width: 90, duration: '2.4s', depth: 0, delay: 800 },
  { name: 'retrieve', type: 'retrieval', width: 35, duration: '0.8s', depth: 1, delay: 1200 },
  { name: 'llm', type: 'llm', width: 50, duration: '1.2s', depth: 1, delay: 1600 },
  { name: 'format_output', type: 'generic', width: 15, duration: '0.3s', depth: 1, delay: 2000 },
];

const SPAN_COLORS: Record<string, string> = {
  llm: 'var(--raw-accent)',
  retrieval: '#0ea5e9',
  generic: 'var(--raw-influence-low)',
};

function HeroTrace() {
  return (
    <EditorWindow title="trace">
      <div className="min-h-[160px] sm:min-h-[200px] space-y-1">
        {TRACE_SPANS.map((span) => (
          <div
            key={span.name}
            className="flex items-center gap-3 py-1.5 opacity-0"
            style={{
              paddingLeft: `${span.depth * 20}px`,
              animation: `fadeSlideIn 500ms ease-out ${span.delay}ms forwards`,
            }}
          >
            <div
              className="w-1 h-6 rounded-full shrink-0"
              style={{ backgroundColor: SPAN_COLORS[span.type] }}
            />
            <span className="font-mono text-xs text-text-primary w-28 truncate">
              {span.name}
              {span.type === 'llm' && (
                <span className="text-accent ml-1">&#9671;</span>
              )}
            </span>
            <div className="flex-1 h-3 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  backgroundColor: SPAN_COLORS[span.type],
                  opacity: 0.7,
                  ['--bar-width' as string]: `${span.width}%`,
                  animation: `landing-bar-grow 800ms ease-out ${span.delay + 200}ms forwards`,
                  width: 0,
                }}
              />
            </div>
            <span className="font-mono text-xs text-text-secondary w-10 text-right shrink-0">
              {span.duration}
            </span>
          </div>
        ))}

        <div className="relative mt-2">
          {[1, 2, 3].map((_, i) => (
            <div
              key={i}
              className="absolute left-[9px] w-px bg-border opacity-0"
              style={{
                top: `${-140 + i * 34}px`,
                ['--line-height' as string]: '20px',
                animation: `landing-line-draw 400ms ease-out ${1200 + i * 400}ms forwards, fadeIn 400ms ease-out ${1200 + i * 400}ms forwards`,
                height: 0,
              }}
            />
          ))}
        </div>

        <div
          className="flex justify-end mt-3 opacity-0"
          style={{ animation: 'fadeSlideIn 500ms ease-out 2800ms forwards' }}
        >
          <span className="font-mono text-xs text-text-muted bg-surface-tertiary px-2.5 py-1 rounded-full">
            Total: $0.003
          </span>
        </div>
      </div>
    </EditorWindow>
  );
}

function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 pt-20 pb-12 overflow-hidden">
      {/* Top nav — logo left, theme toggle right */}
      <div className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-4 sm:px-8 py-4">
        <div
          className="flex items-center gap-3"
          style={{ animation: 'landing-logo-entrance 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}
        >
        <div className="relative flex items-center justify-center w-14 h-14">
          {/* Outer glow ring */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(var(--raw-accent-rgb), 0.2) 0%, transparent 70%)',
              animation: 'landing-diamond-glow 3s ease-in-out infinite',
            }}
          />
          {/* Pulsing ring 1 */}
          <div
            className="absolute inset-0 rounded-full border border-accent/30"
            style={{ animation: 'landing-ring-expand 3s ease-out infinite' }}
          />
          {/* Pulsing ring 2 — offset */}
          <div
            className="absolute inset-0 rounded-full border border-accent/20"
            style={{ animation: 'landing-ring-expand 3s ease-out infinite 1.5s' }}
          />
          {/* Slow rotating border */}
          <div
            className="absolute -inset-1 rounded-full"
            style={{
              background: `conic-gradient(from 0deg, transparent 0%, rgba(var(--raw-accent-rgb), 0.3) 25%, transparent 50%, rgba(var(--raw-accent-rgb), 0.2) 75%, transparent 100%)`,
              animation: 'landing-rotate-slow 8s linear infinite',
              mask: 'radial-gradient(circle, transparent 55%, black 56%, black 100%)',
              WebkitMask: 'radial-gradient(circle, transparent 55%, black 56%, black 100%)',
            }}
          />
          {/* Diamond SVG — proper geometric shape */}
          <svg viewBox="0 0 40 40" className="w-9 h-9 relative z-10">
            <defs>
              <linearGradient id="diamond-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="var(--raw-accent)" stopOpacity="1" />
                <stop offset="100%" stopColor="var(--raw-accent)" stopOpacity="0.6" />
              </linearGradient>
              <filter id="diamond-glow">
                <feGaussianBlur stdDeviation="2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <path
              d="M20 2 L38 20 L20 38 L2 20 Z"
              fill="none"
              stroke="url(#diamond-gradient)"
              strokeWidth="2"
              filter="url(#diamond-glow)"
            />
            <path
              d="M20 8 L32 20 L20 32 L8 20 Z"
              fill="rgba(var(--raw-accent-rgb), 0.08)"
              stroke="url(#diamond-gradient)"
              strokeWidth="1"
              opacity="0.6"
            />
          </svg>
        </div>
        <span
          className="text-2xl font-bold tracking-tight"
          style={{
            backgroundImage: 'linear-gradient(135deg, var(--raw-text-primary) 0%, var(--raw-accent) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Trace
        </span>
        </div>
        <ThemeToggle />
      </div>

      <div
        className="relative z-10 w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 mb-10 sm:mb-16"
        style={{ animation: 'landing-float 8s ease-in-out infinite' }}
      >
        <HeroCode />
        <HeroTrace />
      </div>

      <div className="relative z-10 flex flex-col items-center text-center max-w-2xl px-2">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4">
          <span
            style={{
              backgroundImage: 'linear-gradient(135deg, var(--raw-text-primary), var(--raw-accent))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Debug and track your LLM application
          </span>
        </h1>
        <p className="text-text-secondary text-base sm:text-lg mb-8">
          One decorator gives you full visibility — traces, costs, attribution, and reliability.
        </p>
        <GoogleButton />
      </div>
    </section>
  );
}

// ─── Section 2: The Problem ───────────────────────────────────────

function TextReveal({ text, delayOffset = 0 }: { text: string; delayOffset?: number }) {
  const { ref, inView } = useInView({ threshold: 0.3 });

  return (
    <span ref={ref}>
      {text.split('').map((char, i) => (
        <span
          key={i}
          className="inline-block transition-all duration-500"
          style={{
            opacity: inView ? 1 : 0,
            filter: inView ? 'blur(0px)' : 'blur(4px)',
            transitionDelay: `${delayOffset + i * 15}ms`,
          }}
        >
          {char === ' ' ? '\u00A0' : char}
        </span>
      ))}
    </span>
  );
}

const PAIN_POINTS = [
  {
    question: 'Why did the model hallucinate?',
    detail: 'You shipped a RAG pipeline. A user reports a wrong answer. You check logs — all you see is the final string. Which document caused it? Was the retriever even relevant? You have no idea.',
  },
  {
    question: 'Which call is burning money?',
    detail: 'Your monthly bill doubled. Is it the summarizer? The classifier? The embedding calls? Without per-function cost tracking, you\'re guessing.',
  },
  {
    question: 'What broke after the last deploy?',
    detail: 'Latency spiked 3x. Success rate dropped. But your LLM code looks the same. Was it a prompt change? A model update? A retriever regression? Logs won\'t tell you.',
  },
];

const REVEAL_SPANS = [
  { name: 'my_pipeline', type: 'generic', width: 85 },
  { name: 'embed_query', type: 'retrieval', width: 25 },
  { name: 'chat_completion', type: 'llm', width: 55 },
];

function ProblemSection() {
  const { ref: revealRef, inView: revealInView } = useInView({ threshold: 0.3 });

  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto">
        {/* Headline */}
        <div className="text-center mb-16 sm:mb-20">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-3">
            <TextReveal text="Your LLM is a black box." />
          </h2>
          <p className="text-text-secondary text-base sm:text-lg max-w-2xl mx-auto mt-4">
            You shipped the pipeline. It works... mostly. Then things go wrong, and you realize you can&apos;t see inside any of it.
          </p>
        </div>

        {/* Pain point cards */}
        <div className="space-y-6 sm:space-y-8 mb-16 sm:mb-20">
          {PAIN_POINTS.map((point, i) => {
            const { ref, inView } = useInView({ threshold: 0.2 });
            return (
              <div
                key={i}
                ref={ref}
                className="bg-surface-secondary/60 backdrop-blur-sm border border-border rounded-xl p-5 sm:p-8 transition-all duration-700 ease-out"
                style={{
                  opacity: inView ? 1 : 0,
                  transform: inView ? 'translateY(0)' : 'translateY(20px)',
                  transitionDelay: `${i * 100}ms`,
                }}
              >
                <h3 className="text-text-primary text-base sm:text-lg font-semibold mb-2 flex items-start gap-2">
                  <span className="text-error shrink-0 mt-0.5">?</span>
                  <span>&ldquo;{point.question}&rdquo;</span>
                </h3>
                <p className="text-text-secondary text-sm sm:text-[15px] leading-relaxed ml-5">
                  {point.detail}
                </p>
              </div>
            );
          })}
        </div>

        {/* The reveal */}
        <div className="text-center mb-10">
          <p className="text-accent text-xl sm:text-2xl md:text-3xl font-semibold">
            <TextReveal text="Until now." delayOffset={200} />
          </p>
        </div>

        {/* Trace visualization — blur to clear */}
        <div
          ref={revealRef}
          className="max-w-lg mx-auto transition-all ease-out"
          style={{
            filter: revealInView ? 'blur(0px)' : 'blur(8px)',
            opacity: revealInView ? 1 : 0.3,
            transitionDuration: '1200ms',
          }}
        >
          <div className="bg-surface-secondary/80 backdrop-blur-md border border-border rounded-lg p-4 sm:p-6 text-left space-y-2 shadow-lg">
            {REVEAL_SPANS.map((span) => (
              <div key={span.name} className="flex items-center gap-2 sm:gap-3">
                <div
                  className="w-1 h-5 rounded-full shrink-0"
                  style={{ backgroundColor: SPAN_COLORS[span.type] }}
                />
                <span className="font-mono text-[11px] sm:text-xs text-text-primary w-24 sm:w-32 truncate">{span.name}</span>
                <div className="flex-1 h-2 sm:h-2.5 bg-surface-tertiary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      backgroundColor: SPAN_COLORS[span.type],
                      opacity: 0.7,
                      width: `${span.width}%`,
                    }}
                  />
                </div>
                {span.type === 'llm' && (
                  <span className="text-accent text-xs">&#9671;</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Section 3: Features (5 cards) ───────────────────────────────

// Categorical segment dot colors (matches SEGMENT_DOT_COLORS in colors.ts)
const SEG_DOT_COLORS = ['#6366f1', '#10b981', '#f59e0b'];

const INFLUENCE_CHUNKS = [
  { name: 'Company FAQ', influence: 0.72, color: SEG_DOT_COLORS[0], barBg: 'var(--raw-segment-bg-warm)' },
  { name: 'Product docs', influence: 0.45, color: SEG_DOT_COLORS[1], barBg: 'var(--raw-segment-bg-mid)' },
  { name: 'Support logs', influence: 0.11, color: SEG_DOT_COLORS[2], barBg: 'var(--raw-segment-bg-cool)' },
];

function FeatureInfluence({ animate }: { animate: boolean }) {
  return (
    <div className="space-y-2.5">
      {/* Mini prompt preview with highlighted chunks */}
      <div className="text-xs leading-relaxed font-mono mb-3 p-2 rounded bg-surface-tertiary/60">
        <span style={{ backgroundColor: 'var(--raw-segment-bg-warm)', borderRadius: '2px', padding: '1px 3px' }}>
          Our refund policy allows
        </span>
        {' returns within '}
        <span style={{ backgroundColor: 'var(--raw-segment-bg-mid)', borderRadius: '2px', padding: '1px 3px' }}>
          30 days of purchase
        </span>
        {' for...'}
      </div>

      {/* Chunk influence bars */}
      {INFLUENCE_CHUNKS.map((chunk, i) => (
        <div key={chunk.name} className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: chunk.color }} />
          <span className="text-text-secondary text-[11px] w-20 truncate">{chunk.name}</span>
          <div className="flex-1 h-2 bg-surface-tertiary rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-1000 ease-out"
              style={{
                width: animate ? `${chunk.influence * 100}%` : '0%',
                backgroundColor: chunk.color,
                opacity: 0.7,
                transitionDelay: `${i * 150}ms`,
              }}
            />
          </div>
          <span className="font-mono text-[10px] text-text-muted w-8 text-right">
            {animate ? `${Math.round(chunk.influence * 100)}%` : '0%'}
          </span>
        </div>
      ))}

      <div className="flex items-center gap-1.5 pt-1">
        <span className="text-text-muted text-[10px]">low</span>
        <div className="w-12 h-1 rounded-full" style={{
          background: 'linear-gradient(to right, var(--raw-segment-bg-cool), var(--raw-segment-bg-mid), var(--raw-segment-bg-warm))',
        }} />
        <span className="text-text-muted text-[10px]">high</span>
      </div>
    </div>
  );
}

const HEATMAP_TOKENS = [
  { text: 'The', logprob: -0.02 },
  { text: ' capital', logprob: -0.05 },
  { text: ' of', logprob: -0.01 },
  { text: ' France', logprob: -0.8 },
  { text: ' is', logprob: -0.04 },
  { text: ' Paris', logprob: -2.1 },
  { text: '.', logprob: -0.01 },
];

function logprobToBg(lp: number): string {
  if (lp > -0.1) return 'rgba(253,231,37,0.12)';
  if (lp > -1.0) return 'rgba(253,231,37,0.25)';
  if (lp > -2.0) return 'rgba(245,158,11,0.25)';
  return 'rgba(239,68,68,0.2)';
}

function logprobToText(lp: number): string {
  if (lp > -0.1) return 'var(--raw-logprob-text-confident)';
  if (lp > -1.0) return 'var(--raw-logprob-text-confident)';
  if (lp > -2.0) return 'var(--raw-logprob-text-medium)';
  return 'var(--raw-logprob-text-uncertain)';
}

function FeatureConfidence() {
  return (
    <div>
      <div className="font-mono text-sm leading-relaxed mb-3">
        {HEATMAP_TOKENS.map((t, i) => (
          <span
            key={i}
            style={{ backgroundColor: logprobToBg(t.logprob), color: logprobToText(t.logprob), borderRadius: '2px', padding: '1px 0' }}
          >
            {t.text}
          </span>
        ))}
      </div>

      {/* Probability detail for highlighted token */}
      <div className="bg-surface-tertiary/60 rounded p-2 mb-3">
        <div className="flex items-center justify-between text-[11px] mb-1">
          <span className="font-mono text-text-primary">&ldquo;Paris&rdquo;</span>
          <span className="text-error font-mono">12.2% confident</span>
        </div>
        <div className="h-1.5 bg-surface-primary rounded-full overflow-hidden">
          <div className="h-full bg-error/60 rounded-full" style={{ width: '12.2%' }} />
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="text-text-muted text-[10px]">confident</span>
        <div className="w-14 h-1.5 rounded-full" style={{ background: 'linear-gradient(to right, #fde725, #f59e0b, #ef4444)' }} />
        <span className="text-text-muted text-[10px]">uncertain</span>
      </div>
    </div>
  );
}

function CostCounter({ animate }: { animate: boolean }) {
  const [value, setValue] = useState(0);
  const target = 0.003;
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!animate) return;
    const duration = 1500;
    const start = performance.now();

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(eased * target);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [animate]);

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="font-mono text-2xl text-text-primary">${value.toFixed(3)}</span>
        <span className="text-text-muted text-xs">/call</span>
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-text-muted font-mono">gpt-4o</span>
          <span className="text-text-secondary font-mono">847 tokens</span>
        </div>
        <div className="h-1.5 bg-surface-tertiary rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{ width: animate ? '70%' : '0%', backgroundColor: 'var(--raw-accent)', opacity: 0.6 }}
          />
        </div>
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-text-muted font-mono">embed-3</span>
          <span className="text-text-secondary font-mono">124 tokens</span>
        </div>
        <div className="h-1.5 bg-surface-tertiary rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{ width: animate ? '15%' : '0%', backgroundColor: '#0ea5e9', opacity: 0.6, transitionDelay: '200ms' }}
          />
        </div>
      </div>
    </div>
  );
}

function ReliabilityGauge({ animate }: { animate: boolean }) {
  const [rate, setRate] = useState(0);
  const target = 97.2;
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (!animate) return;
    const duration = 1500;
    const start = performance.now();

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setRate(eased * target);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [animate]);

  const calls = [
    { status: 'ok' }, { status: 'ok' }, { status: 'ok' },
    { status: 'err' }, { status: 'ok' }, { status: 'ok' },
    { status: 'ok' }, { status: 'ok' },
  ];

  return (
    <div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="font-mono text-2xl text-success">{rate.toFixed(1)}%</span>
        <span className="text-text-muted text-xs">success</span>
      </div>
      <div className="flex gap-1 mb-1.5">
        {calls.map((c, i) => (
          <div
            key={i}
            className="flex-1 h-5 rounded-sm transition-all duration-500"
            style={{
              backgroundColor: c.status === 'ok' ? 'var(--raw-success)' : 'var(--raw-error)',
              opacity: animate ? (c.status === 'ok' ? 0.5 : 0.8) : 0.08,
              transitionDelay: `${i * 60}ms`,
            }}
          />
        ))}
      </div>
      <div className="flex justify-between">
        <span className="text-text-muted text-[10px] font-mono">last 8 calls</span>
        <span className="text-error text-[10px] font-mono">1 failure</span>
      </div>
    </div>
  );
}

const LATENCY_BARS = [
  { label: 'p50', value: 1.2, max: 5, color: 'var(--raw-success)' },
  { label: 'p95', value: 2.8, max: 5, color: 'var(--raw-warning)' },
  { label: 'p99', value: 4.1, max: 5, color: 'var(--raw-error)' },
];

function PerformanceCard({ animate }: { animate: boolean }) {
  return (
    <div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="font-mono text-2xl text-text-primary">1.2s</span>
        <span className="text-text-muted text-xs">median</span>
      </div>
      <div className="space-y-2">
        {LATENCY_BARS.map((bar, i) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between text-[11px] mb-0.5">
              <span className="text-text-muted font-mono w-6">{bar.label}</span>
              <span className="text-text-secondary font-mono">{bar.value}s</span>
            </div>
            <div className="h-2 bg-surface-tertiary rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-1000 ease-out"
                style={{
                  width: animate ? `${(bar.value / bar.max) * 100}%` : '0%',
                  backgroundColor: bar.color,
                  opacity: 0.6,
                  transitionDelay: `${i * 150}ms`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FeatureCard({
  title,
  subtitle,
  delay,
  children,
}: {
  title: string;
  subtitle: string;
  delay: number;
  children: React.ReactNode;
}) {
  const { ref, inView } = useInView({ threshold: 0.15 });

  return (
    <div
      ref={ref}
      className="bg-surface-secondary/70 backdrop-blur-md border border-border rounded-xl p-6 transition-all duration-700 ease-out shadow-lg hover:shadow-xl hover:border-border-focus"
      style={{
        opacity: inView ? 1 : 0,
        transform: inView ? 'translateY(0)' : 'translateY(32px)',
        transitionDelay: `${delay}ms`,
      }}
    >
      <h3 className="text-text-primary text-sm font-semibold mb-1">{title}</h3>
      <p className="text-text-muted text-[11px] mb-4">{subtitle}</p>
      {children}
    </div>
  );
}

function FeaturesSection() {
  const { ref: infRef, inView: infInView } = useInView({ threshold: 0.15 });
  const { ref: costRef, inView: costInView } = useInView({ threshold: 0.15 });
  const { ref: relRef, inView: relInView } = useInView({ threshold: 0.15 });
  const { ref: perfRef, inView: perfInView } = useInView({ threshold: 0.15 });

  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-text-primary text-center mb-3">
          Everything you need to ship with confidence
        </h2>
        <p className="text-text-secondary text-center mb-12 sm:mb-16 max-w-xl mx-auto text-sm sm:text-base">
          Every function call, every token, every dollar — traced and visible.
        </p>

        {/* Row 1: 2 wider cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6">
          <div ref={infRef}>
            <FeatureCard
              title="What influenced the output"
              subtitle="See which retrieved chunks shaped the response and by how much"
              delay={0}
            >
              <FeatureInfluence animate={infInView} />
            </FeatureCard>
          </div>

          <FeatureCard
            title="Confidence in every token"
            subtitle="Token-level logprob heatmap shows where the model was guessing"
            delay={150}
          >
            <FeatureConfidence />
          </FeatureCard>
        </div>

        {/* Row 2: 3 metric cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
          <div ref={costRef}>
            <FeatureCard
              title="Cost per function"
              subtitle="Know which function burns tokens"
              delay={200}
            >
              <CostCounter animate={costInView} />
            </FeatureCard>
          </div>

          <div ref={relRef}>
            <FeatureCard
              title="Reliability per function"
              subtitle="Catch regressions before users do"
              delay={300}
            >
              <ReliabilityGauge animate={relInView} />
            </FeatureCard>
          </div>

          <div ref={perfRef} className="sm:col-span-2 md:col-span-1">
            <FeatureCard
              title="Latency per function"
              subtitle="Track p50, p95, p99 across every call"
              delay={400}
            >
              <PerformanceCard animate={perfInView} />
            </FeatureCard>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Section 4: Code Steps ────────────────────────────────────────

const STEPS = [
  { num: '01', title: 'Install', file: 'terminal', code: '$ pip install usetrace' },
  {
    num: '02',
    title: 'Decorate',
    file: 'app.py',
    code: `from usetrace import tracer

@tracer.observe()
def my_pipeline(query: str):
    return chain.invoke(query)`,
  },
  { num: '03', title: 'See everything', file: 'terminal', code: '\u2713 Trace captured: my_pipeline (2.4s, $0.003)' },
];

function StepBlock({ step, index }: { step: (typeof STEPS)[number]; index: number }) {
  const { ref, inView } = useInView({ threshold: 0.3 });
  const isDecorator = index === 1;

  return (
    <div
      ref={ref}
      className="transition-all duration-700 ease-out"
      style={{
        opacity: inView ? 1 : 0,
        transform: inView ? 'translateY(0)' : 'translateY(24px)',
        transitionDelay: `${index * 150}ms`,
      }}
    >
      <div className="flex items-baseline gap-3 mb-3">
        <span className="text-accent font-mono text-sm font-semibold">{step.num}</span>
        <span className="text-text-primary font-semibold">{step.title}</span>
      </div>
      <EditorWindow title={step.file}>
        <pre className="font-mono text-xs leading-6">
          {step.code.split('\n').map((line, i) => {
            const isDecLine = isDecorator && line.startsWith('@');
            return (
              <div
                key={i}
                className="transition-all duration-400"
                style={
                  isDecLine && inView
                    ? {
                        backgroundColor: 'rgba(var(--raw-accent-rgb), 0.08)',
                        borderLeft: '2px solid var(--raw-accent)',
                        paddingLeft: '8px',
                        marginLeft: '-10px',
                      }
                    : {}
                }
              >
                <span className="text-text-primary">{line}</span>
              </div>
            );
          })}
        </pre>
      </EditorWindow>
    </div>
  );
}

function CodeStepsSection() {
  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-text-primary text-center mb-4">
          30 seconds to first trace
        </h2>
        <p className="text-text-secondary text-center mb-12 sm:mb-16 text-sm sm:text-base">
          Three steps. No config files. No infrastructure.
        </p>
        <div className="space-y-10">
          {STEPS.map((step, i) => (
            <StepBlock key={step.num} step={step} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Section 5: CTA ───────────────────────────────────────────────

function CTASection() {
  return (
    <section className="relative py-24 sm:py-32 px-4 sm:px-6">
      <div className="max-w-md mx-auto flex flex-col items-center text-center">
        <div
          className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 rounded-2xl mb-6 sm:mb-8"
          style={{ animation: 'landing-diamond-glow 3s ease-in-out infinite' }}
        >
          <span
            className="text-5xl sm:text-6xl text-accent"
            style={{
              textShadow: '0 0 20px rgba(var(--raw-accent-rgb), 0.4), 0 0 40px rgba(var(--raw-accent-rgb), 0.2)',
            }}
          >
            &#9671;
          </span>
        </div>
        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-text-primary mb-4">
          Start tracing
        </h2>
        <p className="text-text-secondary mb-8 text-sm sm:text-base">
          Add one decorator. See everything.
        </p>
        <GoogleButton />
        <p className="text-text-muted text-xs mt-4">Free while in beta</p>
      </div>
    </section>
  );
}

// ─── Inline keyframes ─────────────────────────────────────────────

const inlineStyles = `
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
`;

// ─── Page ─────────────────────────────────────────────────────────

export function LandingPage() {
  return (
    <div className="min-h-screen bg-surface-primary text-text-primary">
      <style>{inlineStyles}</style>
      <AnimatedBackground />
      <div className="relative" style={{ zIndex: 1 }}>
        <HeroSection />
        <ProblemSection />
        <FeaturesSection />
        <CodeStepsSection />
        <CTASection />
      </div>
    </div>
  );
}
