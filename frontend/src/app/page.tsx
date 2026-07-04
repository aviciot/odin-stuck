'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem('them_access_token');
    router.replace(token ? '/dashboard' : '/login');
  }, [router]);
  return null;
}
