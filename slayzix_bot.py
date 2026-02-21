import discord
from discord.ext import commands
import json
import os

TOKEN = os.getenv("TOKEN")  # Mets ton token en variable d'environnement

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "shop_data.json"

# ------------------------
# Système de sauvegarde
# ------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ------------------------
# Configuration du shop
# ------------------------

SHOP_ITEMS = {
    "vip": 500,
    "sword": 300,
    "shield": 250,
    "potion": 100
}

# ------------------------
# Events
# ------------------------

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")

# ------------------------
# Commandes
# ------------------------

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data:
        data[user_id] = {"money": 0, "inventory": []}
        save_data(data)

    await ctx.send(f"💰 {ctx.author.mention} a {data[user_id]['money']} coins.")

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Boutique", color=discord.Color.green())

    for item, price in SHOP_ITEMS.items():
        embed.add_field(name=item.capitalize(), value=f"{price} coins", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    user_id = str(ctx.author.id)
    item = item.lower()

    if item not in SHOP_ITEMS:
        await ctx.send("❌ Cet objet n'existe pas.")
        return

    if user_id not in data:
        data[user_id] = {"money": 0, "inventory": []}

    price = SHOP_ITEMS[item]

    if data[user_id]["money"] < price:
        await ctx.send("❌ Tu n'as pas assez d'argent.")
        return

    data[user_id]["money"] -= price
    data[user_id]["inventory"].append(item)
    save_data(data)

    await ctx.send(f"✅ {ctx.author.mention} a acheté **{item}** pour {price} coins.")

@bot.command()
@commands.has_permissions(administrator=True)
async def addmoney(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)

    if user_id not in data:
        data[user_id] = {"money": 0, "inventory": []}

    data[user_id]["money"] += amount
    save_data(data)

    await ctx.send(f"💸 {member.mention} reçoit {amount} coins.")

@bot.command()
async def inventory(ctx):
    user_id = str(ctx.author.id)

    if user_id not in data or not data[user_id]["inventory"]:
        await ctx.send("📦 Ton inventaire est vide.")
        return

    items = "\n".join(data[user_id]["inventory"])
    await ctx.send(f"📦 Inventaire de {ctx.author.mention} :\n{items}")

# ------------------------

bot.run(TOKEN)
