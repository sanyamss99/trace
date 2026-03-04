import { useState } from 'react';
import clsx from 'clsx';

interface Column<T> {
  key: string;
  label: string;
  render: (item: T) => React.ReactNode;
  sortable?: boolean;
  align?: 'left' | 'right';
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyFn: (item: T) => string;
  onRowClick?: (item: T) => void;
}

export function DataTable<T>({ columns, data, keyFn, onRowClick }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  'py-2 px-3 text-xs font-medium text-text-muted',
                  col.align === 'right' ? 'text-right' : 'text-left',
                  col.sortable && 'cursor-pointer hover:text-text-secondary',
                )}
                style={{ width: col.width }}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                {col.label}
                {sortKey === col.key && (
                  <span className="ml-1">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={keyFn(item)}
              onClick={onRowClick ? () => onRowClick(item) : undefined}
              className={clsx(
                'border-b border-border/50 last:border-0',
                onRowClick && 'cursor-pointer hover:bg-surface-tertiary',
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={clsx(
                    'py-2 px-3 text-sm',
                    col.align === 'right' ? 'text-right' : 'text-left',
                  )}
                >
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
