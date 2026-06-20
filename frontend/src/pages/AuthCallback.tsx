import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@chainlit/react-client';
import { isGuestUser } from '@/lib/auth';

export default function AuthCallback() {
  const { user, setUserFromAPI } = useAuth();
  const navigate = useNavigate();

  // Fetch user in cookie-based oauth.
  useEffect(() => {
    if (!user || isGuestUser(user)) setUserFromAPI();
  }, []);

  useEffect(() => {
    if (user && !isGuestUser(user)) {
      navigate('/');
    }
  }, [user]);

  return null;
}
