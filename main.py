import os
import re
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # هيقراه من متغير البيئة

# دالة حساب النقاط حسب المركز
def get_rank_points(rank):
    if rank == 1: return 10
    elif rank == 2: return 6
    elif rank == 3: return 5
    elif rank == 4: return 4
    elif rank == 5: return 3
    elif rank == 6: return 2
    elif 7 <= rank <= 10: return 1
    else: return 0

user_templates = {}
user_data = {}
user_double = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 أهلاً بيك في بوت حساب نتائج ببجي!\n\n"
        "1️⃣ استخدم /settemplate وارفع الريزلت الفاضية.\n"
        "2️⃣ ابعت صور النتائج.\n"
        "3️⃣ لو الصورة دبل، استخدم /double قبلها.\n"
        "4️⃣ وأخيرًا استخدم /result عشان تطلع الصورة النهائية 🔥"
    )

# /settemplate
async def set_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("📷 ابعت الصورة بعد الأمر /settemplate.")
        return
    file = await update.message.photo[-1].get_file()
    path = f"template_{update.effective_user.id}.jpg"
    await file.download_to_drive(path)
    user_templates[update.effective_user.id] = path
    user_data[update.effective_user.id] = {}
    await update.message.reply_text("✅ تم حفظ الريزلت الفاضية بنجاح!")

# /double
async def double_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_double[update.effective_user.id] = True
    await update.message.reply_text("✴️ الصورة الجاية هتتحسب دبل!")

# استقبال الصور ومعالجة النتائج
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_templates:
        await update.message.reply_text("📸 لازم تبعت الريزلت الفاضية الأول بـ /settemplate.")
        return

    file = await update.message.photo[-1].get_file()
    path = f"user_{user_id}_last.jpg"
    await file.download_to_drive(path)

    img_for_ocr = Image.open(path).convert("L").point(lambda p: 255 if p > 140 else 0)
    text = pytesseract.image_to_string(img_for_ocr, lang="eng+ara")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    results = []
    current_rank = None

    for line in lines:
        if re.match(r"^\d+$", line):
            current_rank = int(line)
            continue
        m = re.search(r"([A-Za-z0-9\u0600-\u06FF\-\|_\s]+)\s+(\d+)\s*eliminations?", line, re.IGNORECASE)
        if m and current_rank:
            team = m.group(1).strip()
            kills = int(m.group(2))
            results.append((team, kills, current_rank))

    if not results:
        await update.message.reply_text(
            "❌ مش قادر أقرأ بيانات من الصورة.\n"
            "📋 جرب تكبّر الخط أو قص الصورة."
        )
        print("📋 OCR TEXT:\n", text)
        return

    for team, kills, rank in results:
        total = get_rank_points(rank) + kills
        if user_double.get(user_id):
            total *= 2
            user_double[user_id] = False
        if team not in user_data[user_id]:
            user_data[user_id][team] = 0
        user_data[user_id][team] += total

    await update.message.reply_text("✅ تم حساب الصورة بنجاح!")

# /result
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id]:
        await update.message.reply_text("❌ مفيش بيانات. ابعت صور الأول.")
        return

    template_path = user_templates.get(user_id)
    if not template_path:
        await update.message.reply_text("📸 لازم تبعت التمبليت الأول.")
        return

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    sorted_teams = sorted(user_data[user_id].items(), key=lambda x: x[1], reverse=True)
    x, y, gap = 150, 200, 55

    for i, (team, points) in enumerate(sorted_teams):
        line = f"{i+1}. {team} - {points} pts"
        draw.text((x, y + i * gap), line, font=font, fill="white")

    out_path = f"result_{user_id}.jpg"
    img.save(out_path)
    with open(out_path, "rb") as f:
        await update.message.reply_photo(photo=f)
    await update.message.reply_text("📊 دي النتيجة النهائية ✅")

# تشغيل البوت
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("settemplate", set_template))
app.add_handler(CommandHandler("double", double_command))
app.add_handler(CommandHandler("result", result))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("✅ Bot is running...")
app.run_polling()
