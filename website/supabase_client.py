from supabase import create_client, Client

SUPABASE_URL = "https://ltvqpcocsivhtnvkaagl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx0dnFwY29jc2l2aHRudmthYWdsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTc4OTMxMywiZXhwIjoyMDY1MzY1MzEzfQ.fUT6pYpkGRXu0GtvUuWLN_fm7p4DJtAtbLKonm0c-7g"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
