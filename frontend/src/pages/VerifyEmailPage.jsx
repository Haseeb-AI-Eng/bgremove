import React, { useEffect, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import axios from 'axios';
import { useLanguage } from '../contexts/LanguageContext';
import toast from 'react-hot-toast';

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

const VerifyEmailPage = () => {
  const query = useQuery();
  const token = query.get('token');
  const [status, setStatus] = useState('pending'); // pending, success, error
  const { t } = useLanguage();

  useEffect(() => {
    async function verify() {
      if (!token) {
        setStatus('error');
        return;
      }
      try {
        const resp = await axios.get(`/auth/verify-email?token=${encodeURIComponent(token)}`);
        setStatus('success');
        toast.success(resp.data.message || 'Email verified, you may now log in.');
      } catch (err) {
        // try alternate path with /api prefix
        try {
          const resp2 = await axios.get(`/api/auth/verify-email?token=${encodeURIComponent(token)}`);
          setStatus('success');
          toast.success(resp2.data.message || 'Email verified, you may now log in.');
        } catch (err2) {
          setStatus('error');
          const detail = err2.response?.data?.detail || err.response?.data?.detail;
          toast.error(detail || 'Verification failed or link expired.');
        }
      }
    }
    verify();
  }, [token]);

  let content;
  if (status === 'pending') {
    content = <p>{t('verifyingEmail') || 'Verifying your email...'}</p>;
  } else if (status === 'success') {
    content = (
      <div>
        <p>{t('emailVerified') || 'Your email has been verified!'}</p>
        <p>
          <Link to="/login">{t('clickToLogin') || 'Click here to login'}</Link>
        </p>
      </div>
    );
  } else {
    content = (
      <div>
        <p>{t('verificationFailed') || 'Verification failed or the link has expired.'}</p>
        <p>
          <Link to="/signup">{t('signUpAgain') || 'Sign up again'}</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
        {content}
      </div>
    </div>
  );
};

export default VerifyEmailPage;
