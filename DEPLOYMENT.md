# 🚀 Google Cloud Run Deployment Guide — ShopMate AI

This guide details the complete, step-by-step production deployment workflow for **ShopMate AI** on **Google Cloud Run**, including environment variables, secrets management, CORS configuration for React/Next.js frontends, and container scaling settings.

---

## 📋 Architectural Overview

- **Backend:** FastAPI (Python 3.11/3.12)
- **Frontend:** React / Next.js (hosted on Vercel, Firebase, or Cloud Run)
- **Server Entrypoint:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Execution Environment:** Google Cloud Run (Fully Managed Serverless Container)
- **Secrets Management:** Google Cloud Secret Manager
- **Database:** PostgreSQL (Cloud SQL) or SQLite (in `/tmp`)

---

## 🛠️ 1. Prerequisites

1. **Google Cloud SDK (`gcloud`):** Install and initialize the CLI:
   ```bash
   gcloud init
   gcloud auth login
   ```
2. **Set Active Project:**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Enable Required Google Cloud APIs:**
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     secretmanager.googleapis.com \
     artifactregistry.googleapis.com
   ```

---

## 🔐 2. Production Secrets & Environment Variables

### Key Environment Variables

| Variable | Description | Production Recommended Value |
| :--- | :--- | :--- |
| `PORT` | Container listening port | Automatically set to `8080` by Cloud Run |
| `HOST` | Bind host address | `0.0.0.0` |
| `ENVIRONMENT` | Deployment stage | `production` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `https://your-react-app.vercel.app,http://localhost:3000` |
| `SECRET_KEY` | JWT signing secret | 32+ byte cryptographically secure random string |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE` |
| `AMAZON_PRODUCT_API_KEY` | Rainforest API Key | Configured in Secret Manager |
| `EBAY_API_KEY` | Countdown API Key | Configured in Secret Manager |
| `GEMINI_API_KEY` | Google Gemini API Key | Configured in Secret Manager |
| `OPENAI_API_KEY` | OpenAI API Key (optional) | Configured in Secret Manager |

### Store Secrets in Google Cloud Secret Manager

Create secrets securely instead of passing them as plain-text:

```bash
# 1. Create JWT Secret Key
echo -n "your-32-byte-ultra-secure-jwt-key" | gcloud secrets create SHOPMATE_SECRET_KEY --data-file=-

# 2. Create Gemini API Key (if using external Gemini model)
echo -n "your-gemini-api-key" | gcloud secrets create SHOPMATE_GEMINI_KEY --data-file=-

# 3. Create Amazon Rainforest API Key
echo -n "your-rainforest-api-key" | gcloud secrets create SHOPMATE_AMAZON_KEY --data-file=-

# 4. Create eBay Countdown API Key
echo -n "your-countdown-api-key" | gcloud secrets create SHOPMATE_EBAY_KEY --data-file=-
```

Grant Cloud Run's default compute service account permission to read these secrets:
```bash
PROJECT_NUM=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding SHOPMATE_SECRET_KEY \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding SHOPMATE_GEMINI_KEY \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 🚢 3. Deployment Options

### Option A: Direct Source Deploy (Recommended)

Google Cloud Run will build the container using the provided [Dockerfile](file:///c:/Users/sindhu/Desktop/Shopmate%20AI/Dockerfile) and [.gcloudignore](file:///c:/Users/sindhu/Desktop/Shopmate%20AI/.gcloudignore):

```bash
gcloud run deploy shopmate-ai \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars="ENVIRONMENT=production,ALLOWED_ORIGINS=https://your-react-app.vercel.app,http://localhost:3000" \
  --set-secrets="SECRET_KEY=SHOPMATE_SECRET_KEY:latest,GEMINI_API_KEY=SHOPMATE_GEMINI_KEY:latest"
```

### Option B: Build with Artifact Registry & Deploy

1. **Create an Artifact Registry Docker Repository:**
   ```bash
   gcloud artifacts repositories create shopmate-repo \
     --repository-format=docker \
     --location=us-central1 \
     --description="ShopMate AI Docker Repository"
   ```

2. **Build and Push the Container Image:**
   ```bash
   gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/shopmate-repo/shopmate-backend:latest .
   ```

3. **Deploy Image to Cloud Run:**
   ```bash
   gcloud run deploy shopmate-ai \
     --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/shopmate-repo/shopmate-backend:latest \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --set-env-vars="ENVIRONMENT=production,ALLOWED_ORIGINS=https://your-react-app.vercel.app" \
     --set-secrets="SECRET_KEY=SHOPMATE_SECRET_KEY:latest"
   ```

---

## 🌐 4. Configuring CORS for React / Next.js Frontend

When hosting your React / Next.js frontend (e.g. on Vercel, Netlify, Cloud Run, or custom domains):

1. **Update Cloud Run CORS Environment Variable:**
   ```bash
   gcloud run services update shopmate-ai \
     --region us-central1 \
     --update-env-vars="ALLOWED_ORIGINS=https://shopmate-app.vercel.app,https://shopmate.yourdomain.com,http://localhost:3000"
   ```

2. **Configure Frontend Environment Variable (`.env.production` in React / Next.js):**
   ```env
   NEXT_PUBLIC_API_URL=https://shopmate-ai-xyz-uc.a.run.app/api
   ```

3. **Verify CORS Headers via cURL:**
   ```bash
   curl -I -X OPTIONS https://shopmate-ai-xyz-uc.a.run.app/api/products \
     -H "Origin: https://shopmate-app.vercel.app" \
     -H "Access-Control-Request-Method: GET"
   ```
   *Expected Response:*
   ```http
   HTTP/2 200
   access-control-allow-origin: https://shopmate-app.vercel.app
   access-control-allow-credentials: true
   ```

---

## 🗄️ 5. Connecting Cloud SQL (PostgreSQL)

For production deployments with multiple auto-scaling instances, connect to a Cloud SQL instance:

1. Create a Cloud SQL PostgreSQL instance in the same region.
2. Grant Cloud Run instance access:
   ```bash
   gcloud run services update shopmate-ai \
     --region us-central1 \
     --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:shopmate-postgres \
     --update-env-vars "DATABASE_URL=postgresql+psycopg2://user:password@/shopmate_db?host=/cloudsql/YOUR_PROJECT_ID:us-central1:shopmate-postgres"
   ```

---

## ✅ 6. Verification and Monitoring

1. **Check Service Health:**
   ```bash
   curl https://shopmate-ai-xyz-uc.a.run.app/health
   ```
   Response:
   ```json
   {
     "status": "healthy",
     "version": "1.0.0",
     "project": "ShopMate AI - Agentic Retail Assistant",
     "environment": "production",
     "port": 8080
   }
   ```

2. **View Interactive Swagger Documentation:**
   👉 `https://shopmate-ai-xyz-uc.a.run.app/docs`

3. **Inspect Real-Time Logs:**
   ```bash
   gcloud beta run services logs tail shopmate-ai --region us-central1
   ```
