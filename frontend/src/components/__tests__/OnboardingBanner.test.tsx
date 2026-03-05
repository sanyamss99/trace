import { render, screen } from '@testing-library/react';
import { OnboardingBanner } from '../OnboardingBanner';

describe('OnboardingBanner', () => {
  it('renders heading and code snippet', () => {
    render(<OnboardingBanner />);

    expect(screen.getByText('Get started with Trace')).toBeInTheDocument();
    expect(screen.getByText(/from usetrace import trace/)).toBeInTheDocument();
    expect(screen.getByText('Copy')).toBeInTheDocument();
  });
});
