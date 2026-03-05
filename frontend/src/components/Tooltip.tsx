interface TooltipProps {
  text: string;
  children: React.ReactNode;
}

export function Tooltip({ text, children }: TooltipProps) {
  return (
    <span className="relative group inline-flex">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 rounded bg-surface-tertiary border border-border text-text-secondary text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-20">
        {text}
      </span>
    </span>
  );
}
