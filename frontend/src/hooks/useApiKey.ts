import { use } from 'react';
import { AuthContext } from '../context/AuthContext';

export function useApiKey() {
  return use(AuthContext);
}
