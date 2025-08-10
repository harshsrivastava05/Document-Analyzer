# 🚀 DocAnalyzer AI - Complete Installation Guide

This comprehensive guide will walk you through setting up the entire DocAnalyzer AI application, from environment setup to deployment.

## 📋 Prerequisites

Before starting, ensure you have the following installed:

- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **Python** (v3.9 or higher) - [Download](https://python.org/)
- **MySQL** (v8.0 or higher) - [Download](https://mysql.com/)
- **Git** - [Download](https://git-scm.com/)

## 🔑 Required API Keys

You'll need to obtain the following API keys:

1. **Google Cloud Console** - [console.cloud.google.com](https://console.cloud.google.com)
   - Gemini API Key
   - Google Drive API credentials
   - Google OAuth credentials

2. **Pinecone** - [pinecone.io](https://pinecone.io)
   - API key and index setup

3. **Cohere** - [cohere.ai](https://cohere.ai)
   - API key for embeddings

## 📁 Step 1: Project Setup

### 1.1 Create Project Directory
```bash
mkdir docanalyzer-ai
cd docanalyzer-ai
```

### 1.2 Initialize Next.js Frontend
```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir
cd frontend
npm install next-auth framer-motion @next-auth/prisma-adapter prisma @prisma/client mysql2 react-icons
```

### 1.3 Create Backend Directory
```bash
cd ..
mkdir backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 1.4 Install Python Dependencies
```bash
pip install fastapi uvicorn python-multipart python-jose passlib mysql-connector-python google-generativeai pinecone-client cohere google-auth google-api-python-client sqlalchemy alembic pydantic python-dotenv aiofiles
```

## ⚙️ Step 2: Environment Configuration

### 2.1 Create Frontend Environment File
Create `frontend/.env.local`:
```env
# NextAuth Configuration
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-super-secret-key-here"

# Google OAuth
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"

# Database
DATABASE_URL="mysql://root:password@localhost:3306/document_analyzer_db"
```

### 2.2 Create Backend Environment File
Create `backend/.env`:
```env
# API Keys
GEMINI_API_KEY="your-gemini-api-key"
PINECONE_API_KEY="your-pinecone-api-key"
COHERE_API_KEY="your-cohere-api-key"

# Pinecone
PINECONE_INDEX_NAME="document-analyzer"

# Google Drive API
GOOGLE_DRIVE_FOLDER_ID="your-drive-folder-id"
GOOGLE_APPLICATION_CREDENTIALS="./google-credentials.json"

# MySQL Database
MYSQL_HOST="127.0.0.1"
MYSQL_USER="root"
MYSQL_PASSWORD="your-mysql-password"
MYSQL_DATABASE="document_analyzer_db"
```

### 2.3 Google Credentials Setup
1. Download your Google service account credentials JSON file
2. Rename it to `google-credentials.json`
3. Place it in the `backend/` directory

## 🗄️ Step 3: Database Setup

### 3.1 Create MySQL Database
```sql
mysql -u root -p
CREATE DATABASE document_analyzer_db;
USE document_analyzer_db;
```

### 3.2 Run Database Schema
Execute the provided `database_schema.sql` file:
```bash
mysql -u root -p document_analyzer_db < database_schema.sql
```

### 3.3 Setup Prisma (Frontend)
```bash
cd frontend
npx prisma generate
npx prisma db push
```

## 📂 Step 4: File Structure Setup

### 4.1 Copy Frontend Files
Copy all the provided frontend files to their respective locations:

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   ├── upload/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── chat/
│   │   │   └── [id]/
│   │   │       └── page.tsx
│   │   └── api/
│   │       └── auth/
│   │           └── [...nextauth]/
│   │               └── route.ts
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── Hero.tsx
│   │   ├── Features.tsx
│   │   ├── CTA.tsx
│   │   └── Footer.tsx
│   ├── middleware.ts
│   └── auth.ts
├── prisma/
│   └── schema.prisma
├── tailwind.config.js
├── next.config.js
└── package.json
```

### 4.2 Copy Backend Files
Copy the FastAPI files:

```
backend/
├── main.py
├── requirements.txt
├── google-credentials.json
├── .env
└── venv/
```

## 🌐 Step 5: API Configuration

### 5.1 Google Cloud Setup
1. Enable the following APIs:
   - Google Drive API
   - Google Gemini API
   - Gmail API (optional)

2. Create OAuth 2.0 credentials
3. Add authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google`

### 5.2 Pinecone Setup
1. Create a new index named `document-analyzer`
2. Set dimensions to `1024` (for Cohere embeddings)
3. Use cosine similarity metric

## 🚀 Step 6: Running the Application

### 6.1 Start the Backend
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### 6.2 Start the Frontend
```bash
cd frontend
npm run dev
```

### 6.3 Access the Application
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Failed
- Verify MySQL is running: `sudo systemctl status mysql`
- Check credentials in `.env` files
- Ensure database exists: `SHOW DATABASES;`

#### 2. Authentication Not Working
- Verify Google OAuth credentials
- Check redirect URIs match exactly
- Ensure NextAuth secret is set

#### 3. File Upload Fails
- Check Google Drive folder permissions
- Verify service account has access
- Ensure credentials file is in correct location

#### 4. API Keys Invalid
- Double-check all API keys are correct
- Verify billing is enabled for Google Cloud
- Check API usage limits

### Performance Optimization

#### 1. Database Indexing
```sql
-- Add indexes for better performance
CREATE INDEX idx_documents_user_created ON documents(user_id, created_at DESC);
CREATE INDEX idx_chat_document_created ON chat_history(document_id, created_at ASC);
```

#### 2. Caching Configuration
Add Redis for session caching (optional):
```bash
# Install Redis
sudo apt-get install redis-server

# Add to requirements.txt
redis==4.5.0
```

## 📱 Mobile Responsive Testing

Test the application on different screen sizes:
- Desktop: 1920x1080
- Tablet: 768x1024
- Mobile: 375x667

## 🔒 Security Checklist

- [ ] All API keys are in environment variables
- [ ] `.env` files are in `.gitignore`
- [ ] Database passwords are strong
- [ ] HTTPS is configured (production)
- [ ] CORS is properly configured
- [ ] File upload size limits are set

## 🚦 Deployment Preparation

### For Production Deployment:

1. **Frontend (Vercel)**:
   ```bash
   npm run build
   vercel --prod
   ```

2. **Backend (Railway/Heroku)**:
   ```bash
   pip freeze > requirements.txt
   # Deploy using platform-specific commands
   ```

3. **Database (PlanetScale/AWS RDS)**:
   - Migrate to production database
   - Update connection strings

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section
2. Verify all environment variables
3. Ensure all services are running
4. Check API documentation at `/docs`

---

🎉 **Congratulations!** You now have a fully functional AI-powered document analyzer with Google authentication, document upload, and intelligent Q&A capabilities!