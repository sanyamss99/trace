import { useState } from 'react';
import { Link } from 'react-router-dom';

export function OnboardingBanner() {
  const [copied, setCopied] = useState(false);

  const snippet = `from usetrace import Trace

tracer = Trace(api_key="your-key", base_url="https://api.use-trace.com")

@tracer.observe(span_type="llm", model="gpt-4o")
def my_llm_function(prompt: str) -> str:
    return openai.chat.completions.create(...)`;

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
        Three steps to start capturing traces from your LLM application:
      </p>

      <div className="space-y-3 mb-4">
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent/20 text-accent text-xs font-semibold flex items-center justify-center mt-0.5">1</span>
          <p className="text-text-secondary text-sm">
            <Link to="/settings" className="text-accent hover:text-accent/80 font-medium transition-colors">
              Create an API key
            </Link>
            {' '}in Settings
          </p>
        </div>
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent/20 text-accent text-xs font-semibold flex items-center justify-center mt-0.5">2</span>
          <p className="text-text-secondary text-sm">
            Install the SDK:{' '}
            <code className="text-accent bg-surface-primary px-1.5 py-0.5 rounded text-xs">pip install usetrace</code>
          </p>
        </div>
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent/20 text-accent text-xs font-semibold flex items-center justify-center mt-0.5">3</span>
          <p className="text-text-secondary text-sm">
            Add the decorator to your LLM functions:
          </p>
        </div>
      </div>

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
