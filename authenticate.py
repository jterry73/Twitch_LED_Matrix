import asyncio
import os
import json
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope

# Load configuration from environment variables
from dotenv import load_dotenv
load_dotenv()

TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.environ.get("TWITCH_USERNAME")
TOKEN_FILE = f"./twitch_tokens/{TWITCH_USERNAME}_tokens.json"

async def authenticate():
    """Handles the one-time manual user authentication process."""
    print("Starting Twitch authentication...")
    twitch = await Twitch(TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET)

    target_scope = [AuthScope.CHANNEL_READ_SUBSCRIPTIONS, AuthScope.MODERATOR_READ_FOLLOWERS]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)

    print("\n1. Please open the following URL in a browser on your local computer to authorize the application:")
    print(f"   {auth.return_auth_url()}\n")
    
    print("2. After authorizing, your browser will redirect to a 'localhost' page.")
    print("3. Copy the FULL redirected URL from your browser's address bar.")
    print("   (It will look like 'http://localhost:17563/?code=...&scope=...')\n")
    
    redirected_url = input("4. Please paste the full redirected URL here: ")

    try:
        token, refresh_token = await auth.authenticate(user_token=redirected_url)
        
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        
        # Save the tokens to the file
        with open(TOKEN_FILE, 'w') as f:
            json.dump({'token': token, 'refresh_token': refresh_token}, f)
        
        print(f"\n✅ Success! Tokens have been saved to {TOKEN_FILE}")
        print("You can now start your application with 'docker compose up --build'")

    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
    finally:
        await twitch.close()

if __name__ == '__main__':
    asyncio.run(authenticate())
