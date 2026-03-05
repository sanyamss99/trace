import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorMessage } from '../ErrorMessage';
import { ApiError } from '../../api/client';

describe('ErrorMessage', () => {
  it('renders the error message with alert role', () => {
    render(<ErrorMessage error={new Error('Something failed')} />);

    expect(screen.getByText('Something failed')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    const onRetry = vi.fn();
    render(<ErrorMessage error={new Error('fail')} onRetry={onRetry} />);

    fireEvent.click(screen.getByText('Retry'));

    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('shows auth hint for 401 errors', () => {
    const error = new ApiError(401, 'Unauthorized', null);
    render(<ErrorMessage error={error} />);

    expect(screen.getByText(/check your api key/i)).toBeInTheDocument();
  });
});
