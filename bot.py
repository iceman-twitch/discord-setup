import discord
import json
import asyncio
from discord.ext import commands
from typing import List, Dict, Optional

class SetupBot(commands.Bot):
    def __init__(self):
        self.token = self._load_token()
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        self.client = commands.Bot(command_prefix="#", intents = self.intents)
        self.admins_file = "admins.json"
        self.channels_file = "channels.json"
        self.roles_file = "roles.json"
        
        self.admin_ids = self._load_json(self.admins_file, "admin_ids")
        
    def _load_token(self) -> str:
        """Load bot token from token.json"""
        try:
            with open("token.json") as f:
                return json.load(f)["token"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"❌ Failed to load token: {e}")
            print("ℹ️ Create token.json with format: {\"token\": \"YOUR_BOT_TOKEN\"}")
            exit(1)
            
    def _load_json(self, filename: str, key: str) -> List:
        try:
            with open(filename) as f:
                return json.load(f).get(key, [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    async def _create_roles(self, guild: discord.Guild):
        roles_data = self._load_json(self.roles_file, "roles")
        created_roles = []
        
        for role_data in roles_data:
            try:
                role = await guild.create_role(
                    name=role_data["name"],
                    permissions=discord.Permissions(**role_data["permissions"]),
                    color=discord.Color(int(role_data.get("color", "0x000000"), 16))
                created_roles.append(role)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Failed to create role {role_data.get('name')}: {e}")
        return created_roles

    async def _create_channels(self, guild: discord.Guild):
        try:
            with open(self.channels_file) as f:
                channels_data = json.load(f)
                
                # First create non-category channels
                for channel_data in channels_data.get("non_category_channels", []):
                    await self._create_single_channel(guild, None, channel_data)
                
                # Then create categories and their channels
                for category_data in channels_data.get("categories", []):
                    category = await self._create_category(guild, category_data)
                    for channel_data in category_data.get("channels", []):
                        await self._create_single_channel(guild, category, channel_data)
                        
        except Exception as e:
            print(f"Channel creation error: {e}")

    async def _create_category(self, guild: discord.Guild, category_data: Dict):
        try:
            category = await guild.create_category(
                name=category_data["name"],
                position=category_data.get("position", 0)
            )
            
            # Set category permissions
            await self._set_permissions(category, category_data.get("permissions", []))
            return category
        except Exception as e:
            print(f"Failed to create category {category_data.get('name')}: {e}")
            return None

    async def _create_single_channel(self, guild: discord.Guild, category: Optional[discord.CategoryChannel], channel_data: Dict):
        try:
            channel_type = channel_data.get("type", "text")
            if channel_type == "voice":
                channel = await guild.create_voice_channel(
                    name=channel_data["name"],
                    category=category,
                    position=channel_data.get("position", 0)
                )
            else:
                channel = await guild.create_text_channel(
                    name=channel_data["name"],
                    category=category,
                    position=channel_data.get("position", 0)
                )
            
            await self._set_permissions(channel, channel_data.get("permissions", []))
            await asyncio.sleep(0.5)
            return channel
        except Exception as e:
            print(f"Failed to create channel {channel_data.get('name')}: {e}")
            return None

    async def _set_permissions(self, target, permissions_data: List):
        for perm_data in permissions_data:
            try:
                role = discord.utils.get(target.guild.roles, id=int(perm_data["role_id"]))
                if not role:
                    continue
                    
                overwrites = discord.PermissionOverwrite()
                for perm, value in perm_data["permissions"].items():
                    setattr(overwrites, perm, value)
                    
                await target.set_permissions(role, overwrite=overwrites)
            except Exception as e:
                print(f"Failed to set permissions: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
        
    def run_bot(self):
        """Start the bot with loaded token"""
        try:
            self.client.run(self.token)
        except discord.LoginError:
            print("❌ Invalid token - check token.json")
        except Exception as e:
            print(f"❌ Bot crashed: {e}")

    @commands.command()
    async def setup(self, ctx):
        if str(ctx.author.id) not in self.admin_ids:
            await ctx.send("❌ You don't have permission to use this command!")
            return
            
        await ctx.send("🛠️ Starting server setup...")
        
        try:
            # Create roles first
            await ctx.send("🔨 Creating roles...")
            await self._create_roles(ctx.guild)
            
            # Then create channels
            await ctx.send("📁 Creating channels...")
            await self._create_channels(ctx.guild)
            
            await ctx.send("✅ Server setup completed!")
        except Exception as e:
            await ctx.send(f"❌ Setup failed: {str(e)}")
            print(f"Setup error: {e}")

if __name__ == "__main__":
    bot = SetupBot()
    bot.run_bot()