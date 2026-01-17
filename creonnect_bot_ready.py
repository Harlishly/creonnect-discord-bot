import discord
from discord.ext import commands
import anthropic
import re
from datetime import datetime
from collections import defaultdict

# Bot configuration with your credentials
DISCORD_TOKEN = "MTQ2MjIxMzM0NDAzNDQyMjc4NA.G_kkoo.d2GuSfv0RxMwsu7lzBOCLuz1A8KKQDA2lo0qvQ"
ANTHROPIC_API_KEY = "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"

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Configuration - will be set via commands
CONFIG = {
    'welcome_channel_id': None,
    'mod_log_channel_id': None,
    'monitored_channels': [],
    'auto_role_id': None,
    
    'content_rules': {
        'spam_threshold': 5,
        'caps_threshold': 0.7,
        'forbidden_words': ['buy followers', 'fake engagement', 'bot followers'],
        'link_whitelist': ['creonnect.com', 'youtube.com', 'youtu.be', 'instagram.com', 'twitter.com', 'x.com', 'linkedin.com', 'github.com', 'discord.gg'],
    },
    
    'server_knowledge': """
# CREONNECT COMMUNITY - SERVER INFORMATION

## About Creonnect
Creonnect is revolutionizing the creator economy by building the trust layer between creators and brands. 
Our platform enables fair, transparent, and data-driven collaboration worldwide.

**Website:** https://www.creonnect.com
**Mission:** Eliminate fake metrics, unclear partnerships, and unfair payouts through verified, insight-driven ecosystem
**Vision:** Become the trust layer of the creator economy
**Tagline:** "Where Creators innovate Brands"

## What We Do
- ✅ Verified Creator Profiles (no fake metrics)
- 📊 Real-time Performance Insights
- 🤝 Direct Creator-Brand Collaboration
- 💰 Fair & Transparent Payouts
- 🚫 No Middlemen, No Inflated Metrics

## For Creators
✅ Profile Verification - Prove your authenticity
📊 Real Analytics Dashboard - Honest performance data
🔍 Brand Discovery Tools - Find perfect partnerships
💼 Direct Collaboration - No middlemen
💰 Transparent Payment System - Fair compensation

## For Brands
✅ Verified Creator Discovery - Find authentic influencers
📊 Insight-Backed Decisions - Data you can trust
🎯 Target Audience Match - Find your perfect creators
🤝 Direct Partnership Tools - Streamlined collaboration
📈 Campaign Performance Tracking - Measure real ROI

## Getting Started

### New Creators
1. Visit https://www.creonnect.com to create profile
2. Complete verification for better visibility
3. Join creator community channels
4. Browse brand opportunities

### New Brands
1. Visit https://www.creonnect.com to explore creators
2. Use data-driven insights to find matches
3. Post opportunities directly
4. Build authentic partnerships

## Common Questions

**Q: What makes Creonnect different?**
A: We verify every creator, provide real analytics (not fake metrics), enable direct collaboration without middlemen, and ensure transparent, fair payouts.

**Q: How does verification work?**
A: We verify identity, authenticate social accounts, validate engagement metrics, and ensure all data is real and transparent.

**Q: Is Creonnect free?**
A: We offer both free and premium features. Basic creator profiles and brand discovery are free.

**Q: What size creators can join?**
A: All creators! From micro-influencers to macro creators. We believe in fair opportunities based on authentic engagement.

**Q: How do payments work?**
A: Direct, transparent payments between creators and brands with escrow services for security.

## Values
1. Authenticity First - Real metrics, real connections
2. Transparency - Open, honest communication
3. Fair Collaboration - Equal opportunities for all
4. Data-Driven - Decisions backed by insights
5. Creator-Centric - Putting creators first
"""
}

# Track message history for spam detection
message_history = defaultdict(list)

@bot.event
async def on_ready():
    print('=' * 50)
    print(f'✅ {bot.user} is now ONLINE!')
    print(f'📊 Connected to {len(bot.guilds)} server(s)')
    print('=' * 50)
    print('\n🎯 Bot is ready to use!')
    print('\n📋 Quick Setup Commands:')
    print('   !setwelcome #channel-name')
    print('   !setmodlog #channel-name')
    print('   !botstatus')
    print('\n💬 Ask me anything: @mention me or use !ask')
    print('=' * 50)

@bot.event
async def on_member_join(member):
    """Welcome new members"""
    welcome_channel = bot.get_channel(CONFIG['welcome_channel_id'])
    
    if not welcome_channel:
        return
    
    try:
        # Generate personalized welcome
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""Generate a warm, friendly welcome message for {member.name} joining the Creonnect Discord community.

Creonnect is a platform revolutionizing the creator economy with verified profiles and transparent collaborations.

Keep it brief (2-3 sentences), welcoming, and encourage them to:
- Introduce themselves
- Visit creonnect.com
- Ask questions

Be enthusiastic and authentic!"""
            }]
        )
        
        welcome_text = message.content[0].text
        
        embed = discord.Embed(
            title=f"Welcome to Creonnect, {member.name}! 🎉",
            description=welcome_text,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="🔗 Get Started", value="Visit [creonnect.com](https://creonnect.com)", inline=False)
        
        await welcome_channel.send(f"{member.mention}", embed=embed)
        
        # Auto-assign role if configured
        if CONFIG['auto_role_id']:
            role = member.guild.get_role(CONFIG['auto_role_id'])
            if role:
                await member.add_roles(role)
                
    except Exception as e:
        print(f"Error sending welcome: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Content monitoring
    await monitor_content(message)
    
    # Answer when mentioned or DM'd
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        await answer_question(message)
    
    await bot.process_commands(message)

async def monitor_content(message):
    """Monitor for spam and inappropriate content"""
    if CONFIG['monitored_channels'] and message.channel.id not in CONFIG['monitored_channels']:
        if CONFIG['monitored_channels']:  # Only skip if specific channels are set
            return
    
    issues = []
    user_id = message.author.id
    current_time = datetime.utcnow()
    
    # Clean old messages
    message_history[user_id] = [
        (msg, time) for msg, time in message_history[user_id]
        if (current_time - time).total_seconds() < 60
    ]
    
    message_history[user_id].append((message.content, current_time))
    
    # Check spam
    recent_messages = [msg for msg, _ in message_history[user_id]]
    if recent_messages.count(message.content) >= CONFIG['content_rules']['spam_threshold']:
        issues.append("Spam detected (repeated messages)")
    
    # Check caps
    if len(message.content) > 10:
        caps_ratio = sum(1 for c in message.content if c.isupper()) / len(message.content)
        if caps_ratio > CONFIG['content_rules']['caps_threshold']:
            issues.append("Excessive caps")
    
    # Check forbidden words
    content_lower = message.content.lower()
    for word in CONFIG['content_rules']['forbidden_words']:
        if word.lower() in content_lower:
            issues.append(f"Forbidden word: {word}")
    
    # Check links
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
    for url in urls:
        if not any(domain in url for domain in CONFIG['content_rules']['link_whitelist']):
            issues.append(f"Unwhitelisted link")
    
    if issues and CONFIG['mod_log_channel_id']:
        await log_content_issue(message, issues)

async def log_content_issue(message, issues):
    """Log to moderation channel"""
    mod_channel = bot.get_channel(CONFIG['mod_log_channel_id'])
    if not mod_channel:
        return
    
    embed = discord.Embed(
        title="⚠️ Content Monitoring Alert",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="User", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Issues", value="\n".join(f"• {issue}" for issue in issues), inline=False)
    embed.add_field(name="Message", value=message.content[:1000], inline=False)
    embed.add_field(name="Link", value=f"[Jump to message]({message.jump_url})", inline=False)
    
    await mod_channel.send(embed=embed)

async def answer_question(message):
    """AI-powered Q&A"""
    question = message.content.replace(f'<@{bot.user.id}>', '').strip()
    
    if not question:
        return
    
    try:
        async with message.channel.typing():
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=f"""You are the Creonnect AI Assistant. Answer questions about Creonnect and help community members.

{CONFIG['server_knowledge']}

Be friendly, helpful, and concise. If you don't know something, acknowledge it and suggest asking a moderator. Keep responses under 3-4 sentences unless more detail is needed.""",
                messages=[{"role": "user", "content": question}]
            )
            
            answer = response.content[0].text
            
            embed = discord.Embed(
                description=answer,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Creonnect AI Assistant • Ask me anything!")
            
            await message.reply(embed=embed)
    except Exception as e:
        print(f"Error: {e}")
        await message.reply("Sorry, I encountered an error. Please try again!")

# ============================================
# CREONNECT COMMANDS
# ============================================

@bot.command(name='about')
async def about_creonnect(ctx):
    """Learn about Creonnect"""
    embed = discord.Embed(
        title="🌟 About Creonnect",
        description="**Where Creators innovate Brands**",
        color=discord.Color.blue(),
        url="https://www.creonnect.com"
    )
    embed.add_field(name="🎯 Mission", value="Eliminate fake metrics and build trust in creator economy", inline=False)
    embed.add_field(name="✅ What We Do", value="Verified profiles • Real analytics • Direct collaboration • Fair payouts", inline=False)
    embed.add_field(name="🔗 Get Started", value="Visit [creonnect.com](https://www.creonnect.com)", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='creators')
async def for_creators(ctx):
    """Info for creators"""
    embed = discord.Embed(title="🎬 Creonnect for Creators", color=discord.Color.green())
    embed.add_field(name="✅ Get Verified", value="Stand out with verified profile", inline=False)
    embed.add_field(name="📊 Real Analytics", value="Access honest performance data", inline=False)
    embed.add_field(name="🔍 Find Brands", value="Discover perfect partnerships", inline=False)
    embed.add_field(name="💰 Fair Pay", value="Transparent direct payments", inline=False)
    embed.set_footer(text="Start → creonnect.com")
    await ctx.send(embed=embed)

@bot.command(name='brands')
async def for_brands(ctx):
    """Info for brands"""
    embed = discord.Embed(title="🏢 Creonnect for Brands", color=discord.Color.purple())
    embed.add_field(name="🔍 Verified Creators", value="Find authentic influencers", inline=False)
    embed.add_field(name="📊 Data-Driven", value="Make insight-backed decisions", inline=False)
    embed.add_field(name="📈 Track ROI", value="Measure real campaign impact", inline=False)
    embed.set_footer(text="Explore → creonnect.com")
    await ctx.send(embed=embed)

@bot.command(name='ask')
async def ask_question(ctx, *, question: str):
    """Ask the AI assistant"""
    await answer_question(ctx.message)

@bot.command(name='inspire')
async def inspire(ctx):
    """Get creator motivation"""
    import random
    quotes = [
        "Your content matters. Keep creating! 🎬",
        "Authenticity beats vanity metrics every time. ✨",
        "Every creator started at zero. You've got this! 💪",
        "Quality over quantity. Real engagement over fake numbers. 📊",
        "Your unique voice is your superpower. Share it! 🎤",
    ]
    quote = random.choice(quotes)
    embed = discord.Embed(description=f"**{quote}**", color=discord.Color.gold())
    embed.set_footer(text="Powered by Creonnect 💙")
    await ctx.send(embed=embed)

# ============================================
# ADMIN COMMANDS
# ============================================

@bot.command(name='setwelcome')
@commands.has_permissions(administrator=True)
async def set_welcome(ctx, channel: discord.TextChannel):
    """Set welcome channel"""
    CONFIG['welcome_channel_id'] = channel.id
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

@bot.command(name='setmodlog')
@commands.has_permissions(administrator=True)
async def set_modlog(ctx, channel: discord.TextChannel):
    """Set moderation log channel"""
    CONFIG['mod_log_channel_id'] = channel.id
    await ctx.send(f"✅ Mod log channel set to {channel.mention}")

@bot.command(name='botstatus')
async def status(ctx):
    """Check bot status"""
    embed = discord.Embed(title="🤖 Bot Status", color=discord.Color.blue())
    embed.add_field(name="Welcome Channel", value=f"<#{CONFIG['welcome_channel_id']}>" if CONFIG['welcome_channel_id'] else "Not set", inline=True)
    embed.add_field(name="Mod Log", value=f"<#{CONFIG['mod_log_channel_id']}>" if CONFIG['mod_log_channel_id'] else "Not set", inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Status", value="✅ Online & Ready!", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission for this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error.param}")

# Run the bot
if __name__ == "__main__":
    print("\n🚀 Starting Creonnect AI Bot...")
    print("⏳ Connecting to Discord...")
    bot.run(DISCORD_TOKEN)
