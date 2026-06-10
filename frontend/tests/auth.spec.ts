import { describe, expect, it } from 'vitest';

import { canManageConversations, isGuestUser } from '../src/lib/auth';

const guest = {
  identifier: 'guest:test',
  metadata: { auth_mode: 'guest', name: 'Guest' }
};

const realUser = {
  identifier: 'user@example.test',
  metadata: { provider: 'google' }
};

describe('guest authorization helpers', () => {
  it('identifies guest users from auth metadata', () => {
    expect(isGuestUser(guest as any)).toBe(true);
    expect(isGuestUser(realUser as any)).toBe(false);
    expect(isGuestUser(undefined)).toBe(false);
  });

  it('only allows persisted conversation management for real users', () => {
    const config = { dataPersistence: true };

    expect(canManageConversations(config as any, guest as any)).toBe(false);
    expect(canManageConversations(config as any, realUser as any)).toBe(true);
    expect(
      canManageConversations(
        { dataPersistence: false } as any,
        realUser as any
      )
    ).toBe(false);
  });
});
