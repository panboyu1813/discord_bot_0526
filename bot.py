import sys
import os
import discord
import requests
import random
import json
from datetime import datetime, timedelta
import pytz
import time
import re
import asyncio
from discord.ext import commands
from discord.ui import View, Button, Select
from discord import SelectOption, Option

# --- 初始化 Bot ---
bot = discord.Bot(intents=discord.Intents.all())
state_change_enabled = True

# --- 讀取設定檔 ---
with open('setting.json', 'r') as jsonFile:
    settings = json.load(jsonFile)
    aabb = settings["aabb"]

# --- 台灣時區 ---
tz = pytz.timezone('Asia/Taipei')
    
@bot.event
async def on_ready():
    print("✅ Bot is on and ready!")
    activity = discord.Activity(
        type=discord.ActivityType.playing,  # 你也可以改成 .watching 或 .listening
        name="荒野亂鬥"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
       
    content = message.content
    author_id = message.author.id

    if bot.user in message.mentions:
        await message.channel.send("沒事幹嘛戳我")

    # 關鍵字回覆
    keywords = {
        #亂回
        "早安": "你好",
        "草酸鈉": "喵~",
        "已讀不回": "我驕傲",
        "Ms. Wang": "密絲王\n🍚🦢",
        "電龍": "https://c.tenor.com/wRIS2RHzE-MAAAAC/tenor.gif",
        "小班": "風雨澆熄了赤熱的心房，思緒被捆綁~"
    }

    for kw, reply in keywords.items():
        if kw in content:
            await message.channel.send(reply)

# --- 更改狀態 ---
@bot.slash_command(name="change_state", description="更改系統的狀態")
async def change_state(
    ctx,
    new_state: discord.Option(str, choices=["🎞️", "🎮", "🎧"]),
    new_activity: str
):
    if (new_state=="🎞"):
        activity = discord.Activity(
            type=discord.ActivityType.watching,  # 你也可以改成 .playing 或 .listening
            name=new_activity
        )
    elif (new_state=="🎮"):
        activity = discord.Activity(
            type=discord.ActivityType.playing,  # 你也可以改成 .watching 或 .listening
            name=new_activity
        )
    elif (new_state=="🎧"):
        activity = discord.Activity(
            type=discord.ActivityType.listening,  # 你也可以改成 .watching 或 .playing
            name=new_activity
        )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    await ctx.respond(f"已更正狀態為{new_state}-{new_activity}")

# --- 每日充電功能 ---
@bot.slash_command(name="charge", description="每日充電！")
async def charge(ctx):
    if str(ctx.channel.id) != "1361716567536042266":
        await ctx.respond("⚠️ 這裡似乎離無線充電座太遠了，到「充電站」頻道試試吧！", ephemeral=True)
        return
    global settings
    user_id = str(ctx.author.id)
    today = datetime.now(tz).date()

    # 初始化 charge 與 user
    if "charge" not in settings:
        settings["charge"] = {}
    if user_id not in settings["charge"]:
        settings["charge"][user_id] = {
            "last_date": "",
            "streak": 0,
            "points": 0,
            "cooldown": 0,
            "vip": 0,
            "bad_luck_streak": 0
        }
    user_charge = settings["charge"].get(user_id, {"last_date": "", "streak": 0, "points": 0})
    last_date_str = user_charge.get("last_date", "")
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date() if last_date_str else None

    # 已經充過電
    if last_date == today:
        embed = discord.Embed(title="⚠️ 您今天已經充過電了！")
        embed.add_field(
            name="您夠電了，明天再來!",
            value=":zap::zap::zap::place_of_worship::place_of_worship::place_of_worship:",
            inline=False
        )
        await ctx.respond(embed=embed)
        return

    # 判斷連續天數
    if last_date == today - timedelta(days=1):
        streak = user_charge.get("streak", 0) + 1
    else:
        streak = 1

    # 計算獎勵
    if streak % 7 == 0:
        charge_amount = 200
    else:
        charge_amount = 100

    # 累加點數
    points = user_charge.get("points", 0) + charge_amount
    vip = user_charge.get("vip", 0) 
    # 更新資料
    user_data = settings["charge"].get(user_id, {
        "last_date": "",
        "streak": 0,
        "points": 0,
        "cooldown": 0,
        "vip": 0,
        "bad_luck_streak": 0
    })
    
    # 更新必要欄位
    user_data.update({
        "last_date": today.strftime("%Y-%m-%d"),
        "streak": streak,
        "points": points
    })
    settings["charge"][user_id] = user_data

    with open("setting.json", "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    embed = discord.Embed(title="⚡ 充電成功！")
    embed.add_field(name="🔋 電量增加", value=f"+{charge_amount} 點", inline=False)
    embed.add_field(name="💰 目前總點數", value=f"{points} 點", inline=False)
    embed.add_field(name="📅 連續充電天數", value=f"{streak} 天", inline=False)
    await ctx.respond(embed=embed)
    
# --- 查詢點數資訊 ---
@bot.slash_command(name="check_points", description="查看你目前的點數與連續充電天數")
async def check_points(ctx):
    if str(ctx.channel.id) != "1361716567536042266":
        await ctx.respond("⚠️ 請在指定頻道使用這個指令！", ephemeral=True)
        return
    global settings
    user_id = str(ctx.author.id)

    if "charge" not in settings or user_id not in settings["charge"]:
        await ctx.respond("你還沒開始累積點數，快去 `/charge` 一下！⚡")
        return

    user_data = settings["charge"][user_id]
    points = user_data.get("points", 0)
    streak = user_data.get("streak", 0)
    vip_days = user_data.get("vip", 0)

    embed = discord.Embed(title="🔋 你的電電資訊")
    embed.add_field(name="🪪 使用者", value=f"{ctx.author}", inline=False)
    embed.add_field(name="🔋 點數", value=f"{points} 點", inline=True)
    embed.add_field(name="📅 連續充電", value=f"{streak} 天", inline=True)
    embed.add_field(name="👑 VIP 剩餘天數", value=f"{vip_days} 天", inline=False)

    await ctx.respond(embed=embed)

@bot.slash_command(name="rank", description="查看點數排行榜")
async def rank(ctx):
    if str(ctx.channel.id) != "1361716567536042266":
        await ctx.respond("⚠️ 請在指定頻道使用這個指令！", ephemeral=True)
        return

    global settings
    charge_data = settings.get("charge", {})
    
    # 排序點數前五名
    sorted_users = sorted(charge_data.items(), key=lambda x: x[1].get("points", 0), reverse=True)
    
    embed = discord.Embed(title="🏆 點數排行榜")
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    for i in range(5):
        if i < len(sorted_users):
            user_id, data = sorted_users[i]
            member = await ctx.guild.fetch_member(int(user_id))
            name = member.display_name if member else f"未知使用者 ({user_id})"
            points = data.get("points", 0)
            embed.add_field(name=f"{medals[i]} {name}", value=f"{points} 點", inline=False)
        else:
            embed.add_field(name=f"{medals[i]} 從缺", value="無資料", inline=False)

    await ctx.respond(embed=embed)

# --- 1A2B 猜數字 ---
@bot.slash_command(name="ab", description="Play the 1A2B game")
async def ab(ctx, xxx: str):
    global aabb, settings
    user_id = str(ctx.author.id)
    # 初始化 charge 與 user
    if "charge" not in settings:
        settings["charge"] = {}
    if user_id not in settings["charge"]:
        settings["charge"][user_id] = {
            "last_date": "",
            "streak": 0,
            "points": 0,
            "cooldown": 0,
            "vip": 0,
            "bad_luck_streak": 0
        }
    user_data = settings["charge"][user_id]
    point = user_data.get("points", 0)
    if len(xxx) != 4 or not xxx.isdigit() or len(set(xxx)) != 4:
        await ctx.respond("❌ 請輸入四個不重複的數字！")
        return

    exact_match = sum(1 for i in range(4) if xxx[i] == aabb[i])
    number_match = sum(1 for digit in xxx if digit in aabb) - exact_match

    settings["aabb_guess"] += 1

    if exact_match == 4:
        aabb_guess = settings['aabb_guess'] 
        add = 200 // aabb_guess
        await ctx.respond(f"🎉 恭喜你！猜對了！共猜了 {settings['aabb_guess']} 次！，已獲得{add}點")
        point = settings["charge"][user_id]["points"]
        point += add
        settings["charge"][user_id]["points"] = point
        aabb = ''.join(map(str, random.sample(range(10), 4)))
        settings["aabb"] = aabb
        settings["aabb_guess"] = 0

    else:
        await ctx.respond(f"{xxx}\n{exact_match}A{number_match}B（已猜 {settings['aabb_guess']} 次）")

    with open('setting.json', 'w') as jsonFile:
        json.dump(settings, jsonFile, ensure_ascii=False, indent=2)

# --- 1~100 終極密碼 ---
@bot.slash_command(name="number", description="終極密碼(範圍:1~100)")
async def number(ctx, guess: int):
    global settings
    user_id = str(ctx.author.id)
    if guess < 1 or guess > 100:
        await ctx.respond("❌ 請輸入 1 到 100 之間的整數！")
        return
    # 初始化 charge 與 user
    if "charge" not in settings:
        settings["charge"] = {}
    if user_id not in settings["charge"]:
        settings["charge"][user_id] = {
            "last_date": "",
            "streak": 0,
            "points": 0,
            "cooldown": 0,
            "vip": 0,
            "bad_luck_streak": 0
        }
    settings["number_guess"] += 1
    target = int(settings["number"])

    if guess < target:
        msg = f"{guess} 太小了！（已猜 {settings['number_guess']} 次）"
    elif guess > target:
        msg = f"{guess} 太大了！（已猜 {settings['number_guess']} 次）"
    else:
        number_guess = settings['number_guess'] 
        add = 100 // number_guess
        point = settings["charge"][user_id]["points"]
        point += add
        settings["charge"][user_id]["points"] = point

        msg = f"🎯 答對了！答案是 {target}！共猜了 {settings['number_guess']} 次！，已獲得{add}點"
        settings["number"] = str(random.randint(1, 100))
        settings["number_guess"] = 0

    with open('setting.json', 'w') as jsonFile:
        json.dump(settings, jsonFile, ensure_ascii=False, indent=2)

    await ctx.respond(msg)

# --- 默契遊戲 ---
@bot.slash_command(name="tacit", description="默契遊戲(範圍1~100)")
async def tacit(ctx, guess: int):
    global settings
    user_id = str(ctx.author.id)
    if guess < 1 or guess > 100:
        await ctx.respond("❌ 請輸入 1 到 100 之間的整數！")
        return
    # 初始化 charge 與 user
    if "charge" not in settings:
        settings["charge"] = {}
    if user_id not in settings["charge"]:
        settings["charge"][user_id] = {
            "last_date": "",
            "streak": 0,
            "points": 0,
            "cooldown": 0,
            "vip": 0,
            "bad_luck_streak": 0
        }
    target = random.randint(1, 100)

    if guess == target:
        point = settings["charge"][user_id]["points"]
        point += 80
        settings["charge"][user_id]["points"] = point
        msg = f"🎯 答對了！答案是 {target}！已獲得80點"
    else:
        msg = f"❌ 你跟系統沒有默契。答案是 {target}！"

    with open('setting.json', 'w') as jsonFile:
        json.dump(settings, jsonFile, ensure_ascii=False, indent=2)

    await ctx.respond(msg)

# --- 天氣查詢 ---
@bot.slash_command(name="www", description="現在新竹市東區天氣")
async def www(interaction: discord.Interaction):
    if str(interaction.channel.id) != "1361716635039436980":
        await interaction.response.send_message("⚠️ 請在指定頻道使用這個指令！", ephemeral=True)
        return
    url = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization=CWA-738D32B2-4392-4D65-835A-3A4E972C60AA'
    data = requests.get(url)
    data_json = data.json()
    location = data_json['records']['Station']

    weather = {}

    for i in location:
        name = i['StationName']
        city = i['GeoInfo']['CountyName']
        area = i['GeoInfo']['TownName']
        temp = i['WeatherElement']['AirTemperature']
        humd = i['WeatherElement']['RelativeHumidity']
        wtt = i['WeatherElement']['Weather']
        msg = f'📍{city} {area} - {name}\n🌤️ 天氣：{wtt}\n🌡️ 溫度：{temp}°C\n💧 濕度：{humd}%'

        if city not in weather:
            weather[city] = {}
        weather[city][name] = msg

    await interaction.response.send_message(weather["新竹市"]["新竹市東區"])

@bot.slash_command(name="lottery", description="來抽獎一下吧~")
async def lottery(ctx):
    if str(ctx.channel.id) != "1362360573882404994":
        await ctx.respond("⚠️ 請在指定頻道使用這個指令！", ephemeral=True)
        return

    global settings
    user_id = str(ctx.author.id)

    # 初始化
    settings.setdefault("charge", {})
    settings.setdefault("is_drawing", {})
    user_data = settings["charge"].setdefault(user_id, {
        "last_date": "",
        "streak": 0,
        "points": 0,
        "cooldown": 0,
        "vip": 0,
        "bad_luck_streak": 0
    })

    # 檢查是否在抽獎中
    if settings["is_drawing"].get(user_id, False):
        await ctx.respond("⏳你已經在抽獎了喔，請等等結果出來再試一次！", ephemeral=True)
        return

    # 抽獎需要至少 50 點
    if user_data["points"] < 50:
        await ctx.respond("⚠️你太敗家了，趕快去「猜1A2B」或是「終極密碼」。")
        return

    settings["is_drawing"][user_id] = True
    await ctx.respond(embed=discord.Embed(title="🎲 系統轉盤抽獎中...", description="請稍候...", color=0xFFD700))
    initial_response = await ctx.interaction.original_response()

    # 抽獎獎池
    prizes = [
        (1000, 0.03),
        (100, 3),
        (50, 11),
        (20, 17),
        (0, 20),
        (-10, 20),
        (-20, 16),
        (-50, 13),
        (-100, 0.7),
        (-500, 0.27)
    ]
    values = [p for p, _ in prizes]
    weights = [w for _, w in prizes]
    apt_messages = {
        1000: "🦄哇靠你是作弊嗎！？1000點爆擊！系統已經在偷偷觀察你了…",
        100: "📈100點GET！你今天運氣真好。",
        50: "🧃50點不嫌少，系統誠意十足的微笑回饋。",
        20: "🐣20點～雖然不是宇宙大爆炸，但至少有小賺一波～",
        0: "🟡 0點，這好像是個沒意義的系統bug阿，系統努力改進中…",
        -10: "🕳️啊……掉了10點。別擔心，可能只是系統在你背後偷打了個噴嚏。",
        -20: "❌ -20點？沒關係。\n There are always ups and downs in life.",
        -50: "🧟-50點？你是不是剛剛嘲笑別人抽負分？報應來得比快遞還快。",
        -100: "🔥-100點重擊！這波是全身命中，推薦你泡杯茶、深呼吸、當作沒發生過。\n一定是你剛剛偷說系統壞話",
        -500: "🤯啊?是不是有人說敗家拜的不夠快，系統來幫你。\n相信這波可以直接幫你歸0了吧~ \n -500大爆擊"
    }

    # 模擬轉盤（減少編輯次數，10次內）
    for i in range(10):
        temp = random.randrange(-500, 1000, 5)
        rolling_embed = discord.Embed(
            title="🎰 系統轉盤抽獎中...",
            description=f"🎯 目前轉到：**{temp:+}** 點",
            color=0x00BFFF
        )
        await initial_response.edit(embed=rolling_embed)
        await asyncio.sleep(0.1 + i * 0.03)

    # 抽出最終結果
    final_draw = random.choices(values, weights=weights, k=1)[0]

    # 更新 user_data
    user_data["bad_luck_streak"] = user_data.get("bad_luck_streak", 0)
    if final_draw < -10:
        user_data["bad_luck_streak"] += 1
    else:
        user_data["bad_luck_streak"] = 0

    # bonus: 連續 3 次衰運
    bonus_text = ""
    if user_data["bad_luck_streak"] >= 3:
        bonus_text = "\n\n🍀你已連續 3 次抽到悲劇結果，系統偷偷幫你補血 +30！"
        user_data["points"] += 30
        user_data["bad_luck_streak"] = 0

    # 更新點數
    user_data["points"] = max(0, user_data["points"] + final_draw)
    result_text = apt_messages.get(final_draw, "未知結果，但系統也很驚訝。")

    result_embed = discord.Embed(
        title="🎉 抽獎結果出爐！",
        description=f"{result_text}{bonus_text}\n\n💰 當前點數：{user_data['points']} 點",
        color=0x90EE90
    )
    await initial_response.edit(embed=result_embed)

    # 結束狀態並寫回檔案
    settings["is_drawing"][user_id] = False
    with open("setting.json", "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# --- 猜拳 ---
@bot.slash_command(name="rock_paper_scissors", description="玩剪刀石頭布！")
async def rock_paper_scissors(
    ctx,
    choice: discord.Option(str, choices=["✊", "🤚", "✌️","🖖","🫳","🖕"])
):
    if str(ctx.channel.id) != "1361716779503587398":
        await ctx.respond("⚠️ 請在指定頻道使用這個指令！", ephemeral=True)
        return
    global settings
    user_id = str(ctx.author.id)

    # 初始化 charge 與 user
    if "charge" not in settings:
        settings["charge"] = {}
    if user_id not in settings["charge"]:
        settings["charge"][user_id] = {
            "last_date": "",
            "streak": 0,
            "points": 0,
            "cooldown": 0,
            "vip": 0,
            "bad_luck_streak": 0
        }

    user_data = settings["charge"][user_id]
    point = user_data.get("points", 0)

    if point < 50:
        await ctx.respond("⚠️ 你的點數不足以玩這個遊戲！（至少需要 50 點）")
        return

    bot_choice = random.choice(["✊", "🤚", "✌️","🖖","🫳","✊", "🤚", "✌️","🖖","🫳","✊", "🤚", "✌️","🖖","🫳"])
    outcome_map = {
        ("✌️", "✊"): 30,
        ("✌️", "🖖"): 30,
        ("✌️", "🫳"): -50,
        ("✌️", "🤚"): -50,
        ("✊", "✌️"): -50,
        ("✊", "🖖"): 30,
        ("✊", "🫳"): -50,
        ("✊", "🤚"): 30,
        ("🤚", "✌️"): 30,
        ("🤚", "🖖"): -50,
        ("🤚", "🫳"): 30,
        ("🤚", "✊"): -50,
        ("🖖", "✌️"): -50,
        ("🖖", "🤚"): 30,
        ("🖖", "🫳"): 30,
        ("🖖", "✊"): -50,
        ("🫳", "✌️"): 30,
        ("🫳", "🖖"): -50,
        ("🫳", "🤚"): -50,
        ("🫳", "✊"): 30,
    }

    stickers = "⚡" * (point // 1000)  # 根據點數送一些 emoji
    if choice == "🖕":
        result_text = f"你竟然對系統比中指😡😡"
        point -= 100
        settings["charge"][user_id]["points"] = point
    elif bot_choice == choice:
        point += 10
        settings["charge"][user_id]["points"] = point        
        result_text = f"我出 {bot_choice}，平手 🤝\n你獲得10點\n你還有 {point} 點 {stickers}"
    else:
        delta = outcome_map[(bot_choice, choice)]
        point += delta
        settings["charge"][user_id]["points"] = point
        result = "你贏了 🎉" if delta > 0 else "你輸了 💔"
        result_text = (
            f"我出 {bot_choice}，{result}\n"
            f"{'獲得' if delta > 0 else '失去'} {abs(delta)} 點\n"
            f"你現在有 {point} 點 {stickers}"
        )

    # 儲存更新後資料
    with open("setting.json", "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    await ctx.respond(result_text)
    
# --- 啟動 Bot ---
bot.run("DISCORD_BOT_TOKEN")
