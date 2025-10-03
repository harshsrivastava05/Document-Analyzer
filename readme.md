# 🧠 DocAnalyzer AI - Intelligent Document Processing Platform

**The deployed version of this website is discontinued as I have deleted the API keys for LLMs.**

[![Next.js](https://img.shields.io/badge/Next.js-14.0-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue?logo=typescript)](https://typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow?logo=python)](https://python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)](https://mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **Transform your documents into intelligent conversations** with AI-powered analysis, persistent chat history, and seamless Google Drive integration.

## ✨ Features

### 🔐 **Secure Authentication**
- Google OAuth integration with NextAuth.js
- Protected routes and middleware
- Persistent user sessions

### 📄 **Smart Document Processing**
- **Multi-format Support**: PDF, DOCX, TXT files
- **Google Cloud Storage Integration**: Automatic cloud storage and sync
- **Gemini 2.5 Flash**: Advanced AI-powered document analysis
- **Intelligent Insights**: Summary generation, sentiment analysis, entity extraction

### 💬 **RAG-Powered Conversations**
- **Context-Aware Chat**: Ask questions about your documents
- **Persistent History**: All conversations saved to MySQL database
- **Vector Search**: Powered by Pinecone and Cohere embeddings
- **Source Citations**: Answers with references to original document sections

### 🎨 **Modern User Interface**
- **Dark-First Design**: Sleek violet and purple gradient themes
- **Responsive Layout**: Mobile-first design with Tailwind CSS
- **Smooth Animations**: Framer Motion powered interactions
- **Glass Morphism**: Modern frosted glass effects

### 📊 **Analytics & Management**
- **Upload History**: Track all processed documents
- **Usage Analytics**: Monitor API usage and costs
- **Real-time Status**: Live processing and connection indicators

## 🏗️ Architecture

```mermaid
graph TB
    A[Next.js Frontend] --> B[NextAuth.js]
    A --> C[FastAPI Backend]
    C --> D[MySQL Database]
    C --> E[Google Drive API]
    C --> F[Gemini LLM]
    C --> G[Pinecone Vector DB]
    C --> H[Cohere Embeddings]
    
    subgraph "Authentication"
        B --> I[Google OAuth]
    end
    
    subgraph "Document Processing"
        F --> J[Analysis & Insights]
        H --> K[Text Embeddings]
        G --> L[Vector Storage]
    end
    
    subgraph "Data Persistence"
        D --> M[User Data]
        D --> N[Chat History]
        D --> O[Document Metadata]
        E --> P[File Storage]
    end
```

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Authentication**: NextAuth.js
- **Database ORM**: Prisma
- **Icons**: React Icons

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **Database**: MySQL 8.0
- **Authentication**: JWT with NextAuth integration

### AI & ML Services
- **LLM**: Google Gemini 2.5 Flash
- **Embeddings**: Cohere embed-multilingual-v3.0
- **Vector Database**: Pinecone
- **Cloud Storage**: Google Drive API

### DevOps & Deployment
- **Frontend Hosting**: Vercel
- **Backend Hosting**: Railway/Heroku
- **Database**: PlanetScale/AWS RDS
- **Monitoring**: Built-in analytics

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- MySQL 8.0+
- Google Cloud Platform account
- Pinecone account
- Cohere account

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/document-analyzer.git

cd document-analyzer

# Setup frontend
cd frontend
npm install
cp .env.example .env.local

# Setup backend
cd ../backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Database setup
mysql -u root -p -e "CREATE DATABASE document_analyzer_db;"
mysql -u root -p document_analyzer_db < database_schema.sql

# Run the application
# Terminal 1: Backend
cd backend && uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

📖 **For detailed setup instructions, see [Installation Guide](https://github.com/harshsrivastava05/Document-Analyzer/blob/main/installation-guide.md)**

## 📁 Project Structure

```
docanalyzer-ai/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # App router pages
│   │   │   ├── page.tsx     # Homepage
│   │   │   ├── dashboard/   # User dashboard
│   │   │   ├── upload/      # Document upload
│   │   │   ├── chat/        # Chat interface
│   │   │   └── api/         # API routes
│   │   ├── components/      # React components
│   │   │   ├── Navbar.tsx
│   │   │   ├── Hero.tsx
│   │   │   ├── Features.tsx
│   │   │   └── Footer.tsx
│   │   ├── middleware.ts    # Route protection
│   │   └── auth.ts         # NextAuth config
│   ├── prisma/             # Database schema
│   └── tailwind.config.js  # Styling config
├── backend/                # FastAPI application
│   ├── main.py            # FastAPI main app
│   ├── requirements.txt   # Python dependencies
│   ├── database_schema.sql # MySQL schema
│   └── google-credentials.json # Google API credentials
├── docs/                  # Documentation
│   ├── installation-guide.md
│   ├── api-documentation.md
│   └── interview-qa.md
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables

#### Frontend (.env.local)
```env
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-secret-key"
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
DATABASE_URL="mysql://user:password@localhost:3306/document_analyzer_db"
```

#### Backend (.env)
```env
GEMINI_API_KEY="your-gemini-api-key"
PINECONE_API_KEY="your-pinecone-api-key"
COHERE_API_KEY="your-cohere-api-key"
PINECONE_INDEX_NAME="document-analyzer"
GOOGLE_DRIVE_FOLDER_ID="your-folder-id"
GOOGLE_APPLICATION_CREDENTIALS="./google-credentials.json"
MYSQL_HOST="127.0.0.1"
MYSQL_USER="root"
MYSQL_PASSWORD="your-password"
MYSQL_DATABASE="document_analyzer_db"
```

## 📋 API Documentation

### Authentication Endpoints
- `GET /api/auth/signin` - Google OAuth sign-in
- `GET /api/auth/signout` - Sign out user
- `GET /api/auth/session` - Get current session

### Document Endpoints
- `POST /api/upload` - Upload document to Google Drive
- `GET /api/documents` - Get user's document history
- `GET /api/documents/{id}` - Get specific document details

### Chat Endpoints
- `POST /api/chat` - Send message about document
- `GET /api/chat-history/{document_id}` - Get chat history for document

### Analytics Endpoints
- `GET /api/analytics/usage` - Get user usage statistics
- `GET /api/analytics/costs` - Get API usage costs

## 🎯 Use Cases

### 📚 **Academic Research**
- Upload research papers and ask specific questions
- Extract key findings and methodologies
- Generate comprehensive summaries

### 💼 **Business Analysis**
- Process financial reports and business documents
- Extract KPIs and important metrics
- Generate executive summaries

### ⚖️ **Legal Document Review**
- Analyze contracts and legal documents
- Extract key terms and obligations
- Identify potential risks or issues

### 🏥 **Medical Documentation**
- Process medical reports and research
- Extract patient information and recommendations
- Summarize complex medical terminology

## 🔒 Security & Privacy

- **End-to-End Encryption**: All data encrypted in transit and at rest
- **Private Storage**: Documents stored in user's private Google Drive
- **Secure Authentication**: OAuth 2.0 with Google
- **Data Isolation**: Each user's data completely isolated
- **No Data Sharing**: Your documents and conversations remain private

## 🚀 Performance

- **Fast Processing**: Average document analysis in 2-3 seconds
- **Scalable Architecture**: Handles concurrent users efficiently
- **Optimized Queries**: Database indexes for quick retrieval
- **CDN Integration**: Fast global content delivery
- **Caching Strategy**: Redis caching for improved response times

## 🔮 Roadmap

### Version 2.0 (Q2 2025)
- [ ] Multi-language document support
- [ ] Batch document processing
- [ ] Advanced analytics dashboard
- [ ] API rate limiting and quotas

### Version 2.1 (Q3 2025)
- [ ] Team collaboration features
- [ ] Document comparison tools
- [ ] Integration with Microsoft Office
- [ ] Mobile app development

### Version 3.0 (Q4 2025)
- [ ] Custom AI model training
- [ ] Enterprise SSO integration
- [ ] Advanced security features
- [ ] White-label solutions

## 🤝 Contributing

We welcome contributions!

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style
- Frontend: ESLint + Prettier
- Backend: Black + isort
- Commit messages: Conventional Commits

## 📞 Support

- **Email Support**: harshsrivastava8704@gmail.com
- **GitHub Issues**: [Create an issue](https://github.com/harshsrivastava05/Document-Analyzer/issues)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Cloud** for Gemini API and Drive integration
- **Pinecone** for vector database services  
- **Cohere** for multilingual embeddings
- **Vercel** for seamless deployment
- **Next.js team** for the amazing framework

---

<div align="center">

**[🚀 Get Started](https://github.com/harshsrivastava05/Document-Analyzer/blob/main/installation-guide.md)** | **[🌟 Star on GitHub](https://github.com/harshsrivastava05/Document-Analyzer)**

Made with ❤️ by [Harsh Srivastava](https://github.com/harshsrivastava05)

</div>
