// supabaseClient.js — cliente Supabase para el frontend (Project Hub)
// Solo usa la ANON key (pública) — seguro de exponer en el cliente
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL  = 'https://sciorfjvdqxvcwgvnmbv.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNjaW9yZmp2ZHF4dmN3Z3ZubWJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0Mzk2NjYsImV4cCI6MjA5NjAxNTY2Nn0.yO9F0gVl3DqCrrrvY-UAMcTuz_s-KsYYTXooDIBIyLk';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);
export { SUPABASE_URL };
