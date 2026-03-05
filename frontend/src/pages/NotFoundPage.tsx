import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <h1 className="text-text-primary text-5xl font-bold mb-2">404</h1>
      <p className="text-text-secondary text-sm mb-6">
        This page doesn't exist.
      </p>
      <Link
        to="/"
        className="px-4 py-2 text-sm rounded-md bg-accent text-white hover:bg-accent/90 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}
