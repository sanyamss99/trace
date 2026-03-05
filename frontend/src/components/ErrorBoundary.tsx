import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Intentional: Trace is a developer debugging tool — surfacing errors
    // in the browser console is useful, not noisy.
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-surface-primary flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-surface-secondary border border-border rounded-lg p-8 text-center">
            <h1 className="text-text-primary text-lg font-semibold mb-2">
              Something went wrong
            </h1>
            <p className="text-text-secondary text-sm mb-6">
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => this.setState({ hasError: false, error: null })}
                className="px-4 py-2 text-sm rounded-md bg-accent text-white hover:bg-accent/90 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
              >
                Try again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 text-sm rounded-md border border-border text-text-secondary hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
              >
                Reload page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
