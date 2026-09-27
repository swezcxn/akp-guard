import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
from collections import defaultdict
import re

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
TOKEN = "MTU1MzY4ODI1NDc0MDcwMTE4NA.GIyutQ.KbYxBxbLdxHjfjhdUqfKenGU4VCOvUoCEnLeRI"
PREFIX = "."

# Yetkili rol(ler)in ID'si — sunucudan sağ tık → ID'yi kopyala
# Birden fazla ekleyebilirsin: [123, 456, 789]
YETKILI_ROLLER = [
    1541512285288275988,  # ← Buraya yetkili rolün ID'sini yaz
]

# ─────────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.all()

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.remove_command("help")  # Varsayılan help'i kaldır, kendimiz yazacağız

# Spam takibi: {user_id: [timestamp1, timestamp2, ...]}
spam_tracker = defaultdict(list)
# Uyarı sayacı: {user_id: warn_count}
warn_counts = defaultdict(int)


# ─────────────────────────────────────────────
# YETKİ KONTROLÜ (rol bazlı)
# ─────────────────────────────────────────────
def yetkili_mi(ctx: commands.Context) -> bool:
    """Kullanıcının yetkili rollerden birine sahip olup olmadığını kontrol eder."""
    if not ctx.guild:
        return False

    kullanici_rolleri = [role.id for role in ctx.author.roles]
    return any(rol_id in kullanici_rolleri for rol_id in YETKILI_ROLLER)


async def yetki_kontrol(ctx: commands.Context) -> bool:
    """Yetki yoksa mesaj atar ve False döner."""
    if not yetkili_mi(ctx):
        await ctx.send(
            f"❌ {ctx.author.mention} bu komutu kullanma yetkiniz yok. Yetkili role sahip olmalısınız.",
            delete_after=10
        )
        return False
    return True


# ─────────────────────────────────────────────
# .ban @kullanıcı [sebep]
# ─────────────────────────────────────────────
@bot.command(name="ban")
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = "Belirtilmedi"):
    if not await yetki_kontrol(ctx):
        return

    if member.id == ctx.author.id:
        await ctx.send("❌ Kendini banlayamazsın.", delete_after=10)
        return

    if member.id == bot.user.id:
        await ctx.send("❌ Beni banlayamazsın.", delete_after=10)
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ Bu kullanıcıyı banlayamam. Botun rolü kullanıcınınkinden yüksek olmalı.", delete_after=10)
        return

    try:
        # DM gönder
        try:
            await member.send(
                f"🔨 **{ctx.guild.name}** sunucusundan banlandınız.\n"
                f"**Sebep:** {reason}\n"
                f"**Yetkili:** {ctx.author}"
            )
        except:
            pass

        await member.ban(reason=f"{ctx.author} tarafından: {reason}")

        embed = discord.Embed(
            title="🔨 Kullanıcı Banlandı",
            color=discord.Color.red()
        )
        embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        embed.add_field(name="Sebep", value=reason, inline=True)

        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ Yetkim yetersiz.", delete_after=10)


# ─────────────────────────────────────────────
# .kick @kullanıcı [sebep]
# ─────────────────────────────────────────────
@bot.command(name="kick")
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = "Belirtilmedi"):
    if not await yetki_kontrol(ctx):
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ Bu kullanıcıyı atamam.", delete_after=10)
        return

    try:
        try:
            await member.send(
                f"👢 **{ctx.guild.name}** sunucusundan atıldınız.\n**Sebep:** {reason}"
            )
        except:
            pass

        await member.kick(reason=f"{ctx.author} tarafından: {reason}")

        embed = discord.Embed(
            title="👢 Kullanıcı Atıldı",
            color=discord.Color.orange()
        )
        embed.add_field(name="Kullanıcı", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        embed.add_field(name="Sebep", value=reason, inline=True)

        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ Yetkim yetersiz.", delete_after=10)


# ─────────────────────────────────────────────
# .mute @kullanıcı [süre] [sebep]
# ─────────────────────────────────────────────
@bot.command(name="mute")
async def mute(ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "Belirtilmedi"):
    if not await yetki_kontrol(ctx):
        return

    seconds = parse_duration(duration)
    if seconds is None:
        await ctx.send("❌ Geçersiz süre formatı. Örnek: `10s`, `5m`, `2h`, `1d`", delete_after=10)
        return

    if member.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ Bu kullanıcıyı susturamam.", delete_after=10)
        return

    try:
        await member.timeout(
            timedelta(seconds=seconds),
            reason=f"{ctx.author} tarafından: {reason}"
        )

        embed = discord.Embed(
            title="🔇 Kullanıcı Susturuldu",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
        embed.add_field(name="Süre", value=duration, inline=True)
        embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
        embed.add_field(name="Sebep", value=reason, inline=False)

        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("❌ Yetkim yetersiz.", delete_after=10)


# ─────────────────────────────────────────────
# .unmute @kullanıcı
# ─────────────────────────────────────────────
@bot.command(name="unmute")
async def unmute(ctx: commands.Context, member: discord.Member):
    if not await yetki_kontrol(ctx):
        return

    try:
        await member.timeout(None, reason=f"{ctx.author} tarafından kaldırıldı")
        await ctx.send(f"🔊 {member.mention} kullanıcısının susturması kaldırıldı.")
    except discord.Forbidden:
        await ctx.send("❌ Yetkim yetersiz.", delete_after=10)


# ─────────────────────────────────────────────
# .uyarı @kullanıcı [sebep]
# ─────────────────────────────────────────────
@bot.command(name="uyarı", aliases=["uyari", "warn"])
async def uyari(ctx: commands.Context, member: discord.Member, *, reason: str = "Sebep belirtilmedi"):
    if not await yetki_kontrol(ctx):
        return

    warn_counts[member.id] += 1
    count = warn_counts[member.id]

    embed = discord.Embed(
        title="⚠️ Uyarı Verildi",
        color=discord.Color.orange()
    )
    embed.add_field(name="Kullanıcı", value=member.mention, inline=True)
    embed.add_field(name="Toplam Uyarı", value=f"{count}/3", inline=True)
    embed.add_field(name="Yetkili", value=ctx.author.mention, inline=True)
    embed.add_field(name="Sebep", value=reason, inline=False)

    await ctx.send(embed=embed)

    # Kullanıcıya DM
    try:
        await member.send(
            f"⚠️ **{ctx.guild.name}** sunucusunda uyarı aldınız.\n"
            f"**Sebep:** {reason}\n"
            f"**Toplam Uyarı:** {count}"
        )
    except:
        pass


# ─────────────────────────────────────────────
# .uyarısil @kullanıcı
# ─────────────────────────────────────────────
@bot.command(name="uyarısil", aliases=["uyarisil", "warnclear"])
async def uyari_sil(ctx: commands.Context, member: discord.Member):
    if not await yetki_kontrol(ctx):
        return

    warn_counts[member.id] = 0
    await ctx.send(f"✅ {member.mention} kullanıcısının uyarıları sıfırlandı.")


# ─────────────────────────────────────────────
# .rolver @kullanıcı @rol
# ─────────────────────────────────────────────
@bot.command(name="rolver")
async def rolver(ctx: commands.Context, member: discord.Member, role: discord.Role):
    if not await yetki_kontrol(ctx):
        return

    if role >= ctx.guild.me.top_role:
        await ctx.send("❌ Bu rolü veremem. Botun rolü bu rolden düşük.", delete_after=10)
        return

    if role in member.roles:
        await ctx.send(f"❌ {member.mention} zaten **{role.name}** rolüne sahip.", delete_after=10)
        return

    try:
        await member.add_roles(role, reason=f"{ctx.author} tarafından")
        await ctx.send(f"✅ {member.mention} kullanıcısına **{role.name}** rolü verildi.")
    except discord.Forbidden:
        await ctx.send("❌ Yetkim yetersiz.", delete_after=10)


# ─────────────────────────────────────────────
# .rolal @kullanıcı @rol
# ─────────────────────────────────────────────
@bot.command(name="rolal")
async def rolal(ctx: commands.Context, member: discord.Member, role: discord.Role):
    if not await yetki_kontrol(ctx):
        return

    if role >= ctx.guild.me.top_role:
        await ctx.send("❌ Bu rolü alamam. Botun rolü bu rolden düşük.", delete_after=10)
        return

    if role not in member.roles:
        await ctx.send(f"❌ {member.mention} zaten **{role.name}** rolüne sahip değil.", delete_after=10)
        return

    try:
        await member.remove_roles(role, reason=f"{ctx.author} tarafından")
        await ctx.send(f"✅ {member.mention} kullanıcısından **{role.name}** rolü alındı.")
    except discord.Forbidden:
        await ctx.send("❌ Yetkim yetersiz.", delete_after=10)


# ─────────────────────────────────────────────
# .temizle [sayı]
# ─────────────────────────────────────────────
@bot.command(name="temizle", aliases=["clear", "purge"])
async def temizle(ctx: commands.Context, amount: int):
    if not await yetki_kontrol(ctx):
        return

    if amount < 1 or amount > 100:
        await ctx.send("❌ 1 ile 100 arasında bir sayı gir.", delete_after=10)
        return

    try:
        await ctx.message.delete()
    except:
        pass

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 **{len(deleted)}** mesaj silindi.", delete_after=5)


# ─────────────────────────────────────────────
# .yetkililer
# ─────────────────────────────────────────────
@bot.command(name="yetkililer")
async def yetkililer(ctx: commands.Context):
    if not ctx.guild:
        return

    yetkililer_listesi = []

    for rol_id in YETKILI_ROLLER:
        rol = ctx.guild.get_role(rol_id)
        if rol:
            for uye in rol.members:
                if uye not in yetkililer_listesi:
                    yetkililer_listesi.append(uye)

    if not yetkililer_listesi:
        await ctx.send("❌ Hiç yetkili bulunamadı.")
        return

    embed = discord.Embed(
        title="🛡️ Yetkililer",
        description="\n".join([f"• {u.mention}" for u in yetkililer_listesi]),
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed)


# ─────────────────────────────────────────────
# .yardım
# ─────────────────────────────────────────────
@bot.command(name="yardım", aliases=["yardim", "help"])
async def yardim(ctx: commands.Context):
    embed = discord.Embed(
        title="🛡️ Guard Bot Komutları",
        description=f"Prefix: `{PREFIX}` — Sadece **yetkili rol** kullanabilir.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🔨 Moderasyon",
        value=(
            f"`{PREFIX}ban @kişi [sebep]` — Banlar\n"
            f"`{PREFIX}kick @kişi [sebep]` — Sunucudan atar\n"
            f"`{PREFIX}mute @kişi [süre] [sebep]` — Susturur\n"
            f"`{PREFIX}unmute @kişi` — Susturmayı kaldırır\n"
            f"`{PREFIX}uyarı @kişi [sebep]` — Uyarı verir\n"
            f"`{PREFIX}uyarısil @kişi` — Uyarıları sıfırlar"
        ),
        inline=False
    )

    embed.add_field(
        name="🎭 Rol Yönetimi",
        value=(
            f"`{PREFIX}rolver @kişi @rol` — Rol verir\n"
            f"`{PREFIX}rolal @kişi @rol` — Rol alır"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Kanal Yönetimi",
        value=f"`{PREFIX}temizle [1-100]` — Mesaj siler",
        inline=False
    )

    embed.add_field(
        name="ℹ️ Bilgi",
        value=(
            f"`{PREFIX}yetkililer` — Yetkili listesi\n"
            f"`{PREFIX}yardım` — Bu mesaj"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Otomatik Koruma",
        value=(
            "• Davet linki engelleme\n"
            "• Spam engelleme (5sn/5 mesaj)\n"
            "• 3 uyarı = otomatik mute"
        ),
        inline=False
    )

    await ctx.send(embed=embed)


# ─────────────────────────────────────────────
# .ping — Bot gecikmesi
# ─────────────────────────────────────────────
@bot.command(name="ping")
async def ping(ctx: commands.Context):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! **{latency}ms**")


# ─────────────────────────────────────────────
# OTOMATİK KORUMA: Davet Linki Engelleyici
# ─────────────────────────────────────────────
INVITE_PATTERN = re.compile(
    r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+",
    re.IGNORECASE
)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # Yetkilileri ve komutları muaf tut
    kullanici_rolleri = [role.id for role in message.author.roles]
    if any(rol_id in kullanici_rolleri for rol_id in YETKILI_ROLLER):
        await bot.process_commands(message)
        return

    # Komut kullanımıysa dokunma
    if message.content.startswith(PREFIX):
        await bot.process_commands(message)
        return

    # Davet linki kontrolü
    if INVITE_PATTERN.search(message.content):
        try:
            await message.delete()
        except:
            pass

        warn_counts[message.author.id] += 1
        count = warn_counts[message.author.id]

        embed = discord.Embed(
            title="🚫 Davet Linki Engellendi",
            description=f"{message.author.mention} davet linki paylaşamaz.",
            color=discord.Color.red()
        )
        embed.add_field(name="Uyarı Sayısı", value=f"{count}/3", inline=True)

        await message.channel.send(embed=embed, delete_after=10)

        if count >= 3:
            try:
                await message.author.timeout(
                    timedelta(minutes=10),
                    reason="3 uyarı limiti - davet linki spamı"
                )
                await message.channel.send(
                    f"🔇 {message.author.mention} 3 uyarıya ulaştığı için 10 dakika susturuldu.",
                    delete_after=10
                )
                warn_counts[message.author.id] = 0
            except:
                pass

        return

    # Spam kontrolü
    await check_spam(message)

    await bot.process_commands(message)


# ─────────────────────────────────────────────
# OTOMATİK KORUMA: Spam Engelleyici
# ─────────────────────────────────────────────
async def check_spam(message: discord.Message):
    user_id = message.author.id
    current_time = asyncio.get_event_loop().time()

    # Son 5 saniyeyi tut
    spam_tracker[user_id] = [
        t for t in spam_tracker[user_id]
        if current_time - t < 5
    ]

    spam_tracker[user_id].append(current_time)

    if len(spam_tracker[user_id]) >= 5:
        try:
            await message.author.timeout(
                timedelta(minutes=5),
                reason="Spam tespit edildi"
            )
            await message.channel.send(
                f"🔇 {message.author.mention} spam nedeniyle 5 dakika susturuldu.",
                delete_after=10
            )
            spam_tracker[user_id].clear()
        except:
            pass


# ─────────────────────────────────────────────
# HATA YAKALAMA
# ─────────────────────────────────────────────
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Eksik argüman: `{error.param.name}`. `{PREFIX}yardım` yaz.", delete_after=10)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Kullanıcı bulunamadı.", delete_after=10)
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ Rol bulunamadı.", delete_after=10)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Geçersiz argüman.", delete_after=10)
    elif isinstance(error, commands.CommandNotFound):
        pass  # Sessizce geç
    else:
        print(f"Hata: {error}")


def parse_duration(duration: str):
    """10s, 5m, 2h, 1d formatını saniyeye çevirir."""
    match = re.match(r"^(\d+)([smhd])$", duration.lower())
    if not match:
        return None

    value, unit = int(match.group(1)), match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return value * multipliers[unit]


# ─────────────────────────────────────────────
# BOT HAZIR
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ {bot.user} aktif!")
    print(f"📌 Prefix: {PREFIX}")
    print(f"🛡️ Yetkili roller: {YETKILI_ROLLER}")


# ─────────────────────────────────────────────
# ÇALIŞTIR
# ─────────────────────────────────────────────
bot.run(TOKEN)
