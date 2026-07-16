import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

if not url or not key:
    print("Warning: SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")

# Using the service role key is recommended for the bot so it can bypass RLS for token validation
supabase: Client = create_client(url, key)

def link_account(token: str, telegram_id: int) -> bool:
    """
    Attempts to link a Telegram account using a token.
    Returns True if successful, False otherwise.
    """
    try:
        # 1. Fetch the token
        response = supabase.table("bot_auth_tokens").select("*").eq("token", token).eq("used", False).execute()
        tokens = response.data
        
        if not tokens:
            return False
            
        token_data = tokens[0]
        profile_id = token_data['profile_id']
        
        # 2. Update the profile with the telegram_id
        update_response = supabase.table("profiles").update({"telegram_id": telegram_id}).eq("id", profile_id).execute()
        
        if not update_response.data:
            return False
            
        # 3. Mark the token as used
        supabase.table("bot_auth_tokens").update({"used": True}).eq("token", token).execute()
        
        return True
    except Exception as e:
        print(f"Error linking account: {e}")
        return False

def get_profile_by_telegram_id(telegram_id: int):
    """
    Fetches the user's profile based on their telegram_id.
    """
    try:
        response = supabase.table("profiles").select("*").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None
