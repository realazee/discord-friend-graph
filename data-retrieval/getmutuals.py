"""
Script based on original by https://github.com/TheRockettek
Edited by https://github.com/realazee
"""
import json
import random
import asyncio
from playwright.async_api import async_playwright

user_token = ""


async def get_all_friends(page):
    result = await page.evaluate("""async (token) => {
        try {
            const resp = await fetch("https://discord.com/api/v9/users/@me/relationships", {
                headers: { "Authorization": token }
            });
            if (!resp.ok) return { error: resp.status + " " + (await resp.text()) };
            return { data: await resp.json() };
        } catch(e) {
            return { error: e.message };
        }
    }""", user_token)

    if "error" in result:
        raise Exception(result["error"])

    friends = {}
    for friend in result["data"]:
        friends[friend["id"]] = {
            "id": friend["id"],
            "username": friend.get("user", {}).get("username"),
            "discriminator": friend.get("user", {}).get("discriminator"),
            "avatar": friend.get("user", {}).get("avatar"),
            "global_name": friend.get("user", {}).get("global_name"),
        }
    return friends


async def get_mutuals(page, user_id):
    result = await page.evaluate("""async ({token, userId}) => {
        try {
            const resp = await fetch(
                `https://discord.com/api/v9/users/${userId}/profile?type=popout&with_mutual_friends=true&with_mutual_friends_count=false`,
                { headers: { "Authorization": token } }
            );
            if (!resp.ok) return { error: resp.status + " " + (await resp.text()) };
            return { data: await resp.json() };
        } catch(e) {
            return { error: e.message };
        }
    }""", {"token": user_token, "userId": user_id})

    if "error" in result:
        raise Exception(result["error"])

    return [m["id"] for m in result["data"].get("mutual_friends", [])]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()


        print("Navigating to Discord to pass Cloudflare...")
        await page.goto("https://discord.com/login", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        print("Ready!\n")

        friends = await get_all_friends(page)
        total = len(friends)
        print(f"Total friends: {total}\n")

        i = 0
        for friend_id, friend_data in friends.items():
            i += 1
            print(f"{i} / {total} - Getting mutuals for: {friend_data['username']}")

            while True:
                try:
                    mutuals = await get_mutuals(page, friend_id)
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

            with open("mutuals_output.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(friends, indent=4))

        print("\nDone! Results saved to mutuals_output.json")
        await browser.close()


asyncio.run(main())