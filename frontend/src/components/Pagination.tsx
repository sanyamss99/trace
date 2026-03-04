interface PaginationProps {
  hasMore: boolean;
  loading?: boolean;
  onLoadMore: () => void;
}

export function Pagination({ hasMore, loading, onLoadMore }: PaginationProps) {
  if (!hasMore) return null;

  return (
    <div className="flex justify-center py-4">
      <button
        onClick={onLoadMore}
        disabled={loading}
        className="text-sm text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
      >
        {loading ? 'Loading...' : 'Load more'}
      </button>
    </div>
  );
}
