import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NotFoundPage from '../../pages/NotFoundPage';

describe('NotFoundPage', () => {
  it('renders 404 heading and dashboard link', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByText("This page doesn't exist.")).toBeInTheDocument();

    const link = screen.getByRole('link', { name: 'Go to Dashboard' });
    expect(link).toHaveAttribute('href', '/');
  });
});
