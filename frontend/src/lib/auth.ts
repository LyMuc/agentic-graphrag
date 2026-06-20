import type { IChainlitConfig, IUser } from '@chainlit/react-client';

export function isGuestUser(user: IUser | null | undefined): boolean {
  return user?.metadata?.auth_mode === 'guest';
}

export function canManageConversations(
  config: Pick<IChainlitConfig, 'dataPersistence'> | null | undefined,
  user: IUser | null | undefined
): boolean {
  return Boolean(config?.dataPersistence && user && !isGuestUser(user));
}
