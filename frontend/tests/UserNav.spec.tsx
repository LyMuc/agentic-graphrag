import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UserNav from '@/components/header/UserNav';

const mockUseAuth = vi.fn();

vi.mock('@chainlit/react-client', () => ({
  useAuth: () => mockUseAuth()
}));

vi.mock('@/components/i18n', () => ({
  Translator: ({ path }: { path: string }) => <span>{path}</span>
}));

describe('UserNav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows a login link for guest users', () => {
    mockUseAuth.mockReturnValue({
      user: {
        identifier: 'guest:test',
        metadata: { auth_mode: 'guest', name: 'Guest' }
      },
      logout: vi.fn()
    });

    render(<UserNav />);

    expect(screen.getByRole('link', { name: /login/i })).toHaveAttribute(
      'href',
      '/login'
    );
  });
});
