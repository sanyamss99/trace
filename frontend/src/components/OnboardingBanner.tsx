import { useState } from 'react';

export function OnboardingBanner() {
  const [copied, setCopied] = useState(false);

  const snippet = `from usetrace import trace

@trace
def my_llm_function(prompt: str) -> str:
    return openai.chat(prompt)`;

  function handleCopy() {
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="bg-accent-subtle border border-accent/20 rounded-lg p-6 mb-8">
      <h2 className="text-text-primary text-sm font-semibold mb-1">
        Get started with Trace
      </h2>
      <p className="text-text-secondary text-sm mb-4">
        Add the <code className="text-accent">@trace</code> decorator to your
        LLM functions to start capturing traces.
      </p>
      <div className="relative">
        <pre className="font-mono text-xs text-text-secondary bg-surface-primary rounded-md p-4 overflow-x-auto whitespace-pre">
          {snippet}
        </pre>
        <button
          onClick={handleCopy}
          className="absolute top-2 right-2 px-2 py-1 text-xs rounded bg-surface-secondary border border-border text-text-secondary hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    </div>
  );
}
