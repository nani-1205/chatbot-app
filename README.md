# Document Chatbot Web Application

## Overview

This is a Python Flask web application that provides a chatbot interface for answering questions based on the content of documents stored in an Amazon S3 bucket. The chatbot uses:

- **Data Source:** Files in various text-based formats (TXT, PDF, CSV, Excel, DOCX, etc.) from an S3 bucket.
- **Language Model:** Google Gemini 1.5 Flash (via the Google Generative AI API).
- **Semantic Search:** Sentence Transformers for generating embeddings and performing semantic search.
- **Database:** MongoDB for storing chat history.
- **Frontend:** HTML, CSS, and JavaScript.
- **Configuration:** Environment variables managed using `.env`.

## Features

- **Document-Based Answers**
- **Multi-File Format Support**
- **Semantic Search with Sentence Embeddings**
- **Chat History in MongoDB**
- **Clean Web Interface**
- **Secure Configuration with .env**
- **Deployable on EC2**


## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- pip
- MongoDB instance
- Google Gemini API Key
- AWS account with an S3 bucket

### Installation

```bash
git clone -b neural-network https://github.com/nani-1205/chatbot-app.git chatbot-webapp
cd chatbot-webapp
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root project directory:

```env
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY
MONGODB_USERNAME=your_mongodb_username
MONGODB_PASSWORD=your_mongodb_password
MONGODB_HOST=your_mongodb_host_address
MONGODB_PORT=27017
MONGODB_AUTH_SOURCE=admin
DATABASE_NAME=chatbot_db
COLLECTION_NAME=chat_history
S3_BUCKET_NAME=your-s3-bucket-name
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_REGION_NAME=your-aws-region
```

### Running the Application

```bash
python app.py
```

Visit: `http://127.0.0.1:5000/`

#### PM2 (Recommended for EC2):
```bash
pm2 start app.py --update-env
pm2 logs app
```

### Usage

1. Open `http://127.0.0.1:5000/` in your browser
2. Ask questions in the input box
3. Chatbot answers based on your document content
4. Chat history is saved and visible on page reload

### EC2 Deployment Steps

1. Launch EC2 instance with necessary access
2. SSH into instance and install dependencies
3. Clone the repo and setup `.env`
4. Run using `pm2` or production-ready WSGI server
5. Access via EC2 public IP or DNS with port 5000

### Dependencies

- Flask
- python-dotenv
- boto3
- PyPDF2
- python-docx
- pandas
- openpyxl
- google-generativeai
- pymongo
- sentence-transformers
- numpy
- scikit-learn

---


