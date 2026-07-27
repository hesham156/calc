# النشر على Railway

المشروع يتكوّن من **3 خدمات** داخل مشروع Railway واحد:

| الخدمة | Root Directory | الوصف |
|--------|----------------|-------|
| `Postgres` | — | قاعدة البيانات (تُضاف من قائمة Railway الجاهزة) |
| `backend` | `backend` | FastAPI |
| `frontend` | `frontend` | Next.js |

كل خدمة تُبنى من الـ `Dockerfile` الخاص بها، والإعدادات مكتوبة في `backend/railway.json` و `frontend/railway.json`.

---

## الخطوات

### 1) ارفع الكود على GitHub

```bash
git push origin main
```

### 2) أنشئ المشروع وقاعدة البيانات

1. من [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo** → اختر `hesham156/calc`.
2. داخل المشروع: **+ New** → **Database** → **Add PostgreSQL**.

### 3) خدمة الـ backend

في إعدادات الخدمة → **Settings**:

- **Source** → **Root Directory** = `/backend`
- **Config-as-code** → **Railway Config File** = `/backend/railway.json`
- **Networking** → **Generate Domain** (لازم قبل ضبط المتغيرات)

> ⚠️ الإعدادان مطلوبان معاً. **Root Directory** يحدد الملفات التي تُسحب وسياق البناء — بدونه يفحص Railway جذر الريبو، لا يجد `Dockerfile`، ويفشل بـ
> `Railpack could not determine how to build the app`.
> و**مسار ملف الإعدادات لا يتبع Root Directory** — لازم مسار مطلق، وإلا يُتجاهَل الـ healthcheck.

ثم **Variables**:

| المتغير | القيمة |
|---------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `CORS_ORIGINS` | `https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}` |
| `UPLOAD_DIR` | `/data/uploads` |
| `EXPORT_DIR` | `/data/exports` |
| `COMPANY_NAME` | اسم شركتك |
| `MAX_UPLOAD_MB` | `50` |

**Volume للملفات المرفوعة:** الملفات على Railway تُمسح مع كل إعادة نشر. من الخدمة → **+ Volume** → **Mount path** = `/data`.
(البيانات المستخرجة من الملفات تُخزَّن في Postgres، فالـ Volume لحفظ الملفات الأصلية فقط.)

### 4) خدمة الـ frontend

**+ New** → **GitHub Repo** → نفس الريبو. ثم **Settings**:

- **Source** → **Root Directory** = `/frontend`
- **Config-as-code** → **Railway Config File** = `/frontend/railway.json`
- **Networking** → **Generate Domain**

ثم **Variables**:

| المتغير | القيمة |
|---------|--------|
| `NEXT_PUBLIC_API_URL` | `https://${{backend.RAILWAY_PUBLIC_DOMAIN}}` |

> ⚠️ **الأهم:** `NEXT_PUBLIC_API_URL` يُخبز داخل الـ bundle **وقت البناء** لا وقت التشغيل. لو ضبطته بعد أول نشر، لازم **Redeploy** للـ frontend وإلا هيفضل ينادي `http://localhost:8000` وتظهر الصفحة بدون بيانات.

> ملاحظة: `${{backend...}}` و `${{frontend...}}` لازم تطابق **أسماء الخدمات الفعلية** عندك في Railway. لو سمّيتها غير كده، عدّل الاسم داخل الأقواس.

### 5) أعد النشر وافتح الموقع

بعد ضبط المتغيرات: **Redeploy** للخدمتين (الـ frontend إلزامي).

افتح دومين الـ frontend → تفتح لوحة التحكم مباشرة (لا يوجد تسجيل دخول).

> ⚠️ **لا يوجد أي حماية على التطبيق.** أي شخص يعرف الدومين يقدر يفتح البيانات ويرفع ملفات ويعدّل الإعدادات. لو الرابط هيكون عام، ضع حماية على مستوى الشبكة (Railway private networking أو بروكسي أمامه بكلمة مرور).

---

## ملاحظات مهمة

**البيانات المحلية لا تنتقل.** قاعدة `backend/attendance.db` هي SQLite على جهازك وغير مرفوعة أصلاً (مستبعدة في `.gitignore`). قاعدة Railway تبدأ فارغة، والجداول تُنشأ تلقائياً عند أول تشغيل. لو عايز تنقل بياناتك الحالية، ده يحتاج سكربت ترحيل منفصل — قوللي وأعمله.

**البيانات التجريبية (`app/db/seed.py`) للتطوير فقط** — تنشئ موظفين وهميين وبيانات حضور عشوائية. لا تشغّلها على الإنتاج.

**التكلفة.** الخطة المجانية عندها حد شهري؛ ثلاث خدمات (backend + frontend + Postgres) تستهلك أسرع من خدمة واحدة.

**تقليل عمليات البناء غير الضرورية.** لأن الخدمتين من نفس الريبو، أي `push` يعيد بناء الاثنتين. من **Settings** → **Watch Paths** ضع `/backend/**` لخدمة الباك إند و `/frontend/**` للواجهة.

---

## حل المشاكل

### `Railpack could not determine how to build the app`

اللوج يعرض ملفات جذر الريبو (`docker-compose.yml`, `.gitignore` …) بدل ملفات الخدمة.
**السبب:** الـ **Root Directory** غير مضبوط، فلم يجد Railway الـ `Dockerfile`.
**الحل:** اضبطه على `/backend` أو `/frontend` كما في الخطوات أعلاه، ثم **Redeploy**.

### `failed to compute cache key: "/app/public": not found`

مجلد `frontend/public/` فارغ، وجيت لا يتتبّع المجلدات الفارغة — فلا يصل إلى سياق البناء.
معالَج في الـ Dockerfile بـ `RUN mkdir -p public`. لو أضفت مجلداً فارغاً آخر يعتمد عليه البناء، ستحتاج نفس الحيلة أو ملف `.gitkeep` بداخله.

### الموقع يفتح لكن بلا بيانات / أخطاء شبكة في الـ console

`NEXT_PUBLIC_API_URL` لم يُضبط **قبل** البناء، فالواجهة تنادي `http://localhost:8000`.
**الحل:** اضبط المتغير ثم **Redeploy** للواجهة (تغيير المتغير وحده لا يكفي).

### خطأ CORS في المتصفح

`CORS_ORIGINS` في الباك إند لا يطابق دومين الواجهة. لاحظ: بدون `/` في النهاية، ومع `https://`.

### `Application failed to respond`

الخدمة لا تستمع على `$PORT`. الـ Dockerfiles هنا معالِجة لذلك بالفعل — تأكد أن Railway يبني من الـ Dockerfile وليس Railpack.

---

## بديل: النشر عبر الـ CLI

يتطلب متصفحاً لتسجيل الدخول:

```bash
npm i -g @railway/cli
```

```bash
railway login
```

ثم من داخل كل مجلد (`backend` ثم `frontend`):

```bash
railway up
```

الطريقة الأولى (GitHub) أفضل — كل `git push` ينشر تلقائياً.
