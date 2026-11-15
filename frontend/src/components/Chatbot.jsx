import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { apiUrl } from '../api/config';

export default function Chatbot() {
  const { pathname } = useLocation();
  const isAdmin = pathname.startsWith('/admin');
  useEffect(() => {
    if (isAdmin) return;
    const script = document.createElement('script');
    script.src = apiUrl('widget.js');
    script.dataset.botId = 'fify-demo';
    script.defer = true;
    document.body.appendChild(script);
    return () => {
      script.remove();
      document.getElementById('fify-assistant-widget')?.dispatchEvent(new Event('fify:remove'));
    };
  }, [isAdmin]);
  return null;
}
