import getRouterBasename from '@/lib/router';
import App from 'App';
import { useContext, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  ChainlitContext,
  useApi,
  useAuth,
  useChatInteract,
  useConfig
} from '@chainlit/react-client';

import { ExtendedChainlitAPI } from '@/api';
import { Loader } from '@/components/Loader';

export default function AppWrapper() {
  const [translationLoaded, setTranslationLoaded] = useState(false);
  const [guestAuthError, setGuestAuthError] = useState(false);
  const guestAuthStarted = useRef(false);
  const { isAuthenticated, isReady, setUserFromAPI } = useAuth();
  const { language: languageInUse } = useConfig();
  const { i18n } = useTranslation();
  const { windowMessage } = useChatInteract();
  const apiClient = useContext(ChainlitContext) as ExtendedChainlitAPI;

  const loginPath = getRouterBasename() + '/login';
  const callbackPath = getRouterBasename() + '/login/callback';
  const isAuthRoute =
    window.location.pathname === loginPath ||
    window.location.pathname === callbackPath;
  const shouldBootstrapGuest = isReady && !isAuthenticated && !isAuthRoute;

  function handleChangeLanguage(languageBundle: any): void {
    i18n.addResourceBundle(languageInUse, 'translation', languageBundle);
    i18n.changeLanguage(languageInUse);
  }

  const { data: translations } = useApi<any>(
    `/project/translations?language=${languageInUse}`
  );

  useEffect(() => {
    if (!translations) return;
    handleChangeLanguage(translations.translation);
    setTranslationLoaded(true);
  }, [translations]);

  useEffect(() => {
    const handleWindowMessage = (event: MessageEvent) => {
      windowMessage(event.data);
    };
    window.addEventListener('message', handleWindowMessage);
    return () => window.removeEventListener('message', handleWindowMessage);
  }, [windowMessage]);

  useEffect(() => {
    if (!shouldBootstrapGuest || guestAuthStarted.current) return;

    guestAuthStarted.current = true;
    apiClient
      .guestAuth()
      .then(async () => {
        await setUserFromAPI();
      })
      .catch((error) => {
        console.error('Unable to start guest session', error);
        setGuestAuthError(true);
      });
  }, [apiClient, setUserFromAPI, shouldBootstrapGuest]);

  if (guestAuthError) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        Unable to start guest session.
      </div>
    );
  }

  if (!translationLoaded || shouldBootstrapGuest) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader className="!size-6" />
      </div>
    );
  }

  return <App />;
}
