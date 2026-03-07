import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { OnboardingBanner } from '../OnboardingBanner';

describe('OnboardingBanner', () => {
  it('renders heading and code snippet', () => {
    render(
      <MemoryRouter>
        <OnboardingBanner />
      </MemoryRouter>,
    );

    expect(screen.getByText('Get started with Trace')).toBeInTheDocument();
    expect(screen.getByText(/from usetrace import Trace/)).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();
  });
});
