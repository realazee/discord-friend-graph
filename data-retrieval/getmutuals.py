"""
Script based on original by https://github.com/TheRockettek
Edited by https://github.com/realazee
"""
import json
import random
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
user_token = os.getenv("USER_TOKEN", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "mutuals_output.json")

DISCORD_API = "https://discord.com/api/v9"


async def fetch_super_properties(session):
    """Fetch super properties from cordapi. Returns the encoded header and user agent."""
    async with session.post("https://cordapi.dolfi.es/api/v2/properties/web") as resp:
        data = await resp.json()

    props = data["properties"]
    encoded = data["encoded"]
    user_agent = props["browser_user_agent"]

    print(f"Super properties loaded (build {props['client_build_number']})")
    return encoded, user_agent


def build_headers(super_props, user_agent):
    """Build the standard headers for Discord API requests."""
    return {
        "Authorization": user_token,
        "User-Agent": user_agent,
        "X-Super-Properties": super_props,
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "America/New_York",
    }


async def get_all_friends(session, headers):
    async with session.get(f"{DISCORD_API}/users/@me/relationships", headers=headers) as resp:
        if resp.status != 200:
            raise Exception(f"{resp.status} {await resp.text()}")
        data = await resp.json()

    friends = {}
    for friend in data:
        friends[friend["id"]] = {
            "id": friend["id"],
            "username": friend.get("user", {}).get("username"),
            "discriminator": friend.get("user", {}).get("discriminator"),
            "avatar": friend.get("user", {}).get("avatar"),
            "global_name": friend.get("user", {}).get("global_name"),
        }
    return friends


async def get_mutuals(session, user_id, headers):
    url = f"{DISCORD_API}/users/{user_id}/profile"
    params = {
        "type": "popout",
        "with_mutual_friends": "true",
        "with_mutual_friends_count": "false",
    }
    async with session.get(url, headers=headers, params=params) as resp:
        if resp.status != 200:
            raise Exception(f"{resp.status} {await resp.text()}")
        data = await resp.json()

    return [m["id"] for m in data.get("mutual_friends", [])]


async def main():
    async with aiohttp.ClientSession() as session:
        super_props, user_agent = await fetch_super_properties(session)
        headers = build_headers(super_props, user_agent)

        print("Fetching friends list...")
        current_friends = await get_all_friends(session, headers)
        
        # Load existing data
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                friends = json.load(f)
                print(f"Loaded existing data with {len(friends)} records.")
        except (FileNotFoundError, json.JSONDecodeError):
            friends = {}

        # Merge current_friends into friends
        for friend_id, friend_data in current_friends.items():
            if friend_id not in friends:
                friends[friend_id] = friend_data
            else:
                # Update basic info but keep mutual_friends if it exists
                for k, v in friend_data.items():
                    if k != "mutual_friends":
                        friends[friend_id][k] = v

        total = len(friends)
        print(f"Total friends: {total}\n")

        i = 0
        for friend_id, friend_data in friends.items():
            i += 1
            
            # Skip if we already have their mutual friends
            if "mutual_friends" in friend_data:
                print(f"{i} / {total} - Skipping (already got mutuals for: {friend_data.get('username')})")
                continue

            print(f"{i} / {total} - Getting mutuals for: {friend_data.get('username')}")

            while True:
                try:
                    mutuals = await get_mutuals(session, friend_id, headers)
                    friends[friend_id]["mutual_friends"] = mutuals
                    break
                except Exception as e:
                    error_msg = str(e)
                    if "Unknown User" in error_msg or "10013" in error_msg or error_msg.startswith("404"):
                        print(f"  Skipping (unknown user)")
                        friends[friend_id]["mutual_friends"] = []
                        break
                    else:
                        print(f"  oops! {e}")
                        print("  Rate limited! Waiting 60 seconds before retrying...")
                        await asyncio.sleep(60)
                        print("  Resuming...")

            delay = random.uniform(0.5, 2)
            await asyncio.sleep(delay)

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(json.dumps(friends, indent=4))

        print(f"\nDone! Results saved to {OUTPUT_FILE}")


asyncio.run(main())