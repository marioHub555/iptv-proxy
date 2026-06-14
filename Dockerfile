# استخدام نسخة بايثون رسمية ومستقرة
FROM python:3.10-slim

# تثبيت أداة FFmpeg وتحديث حزم النظام الأساسية
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# تحديد مجلد العمل داخل السيرفر
WORKDIR /app

# نسخ ملف المكتبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ بقية ملفات المشروع إلى السيرفر
COPY . .

# فتح المنفذ الذي حددته في كودك
EXPOSE 7860

# أمر تشغيل التطبيق مباشرة
CMD ["python", "api/index.py"]
