# Document Chatbot Web Application

## Overview

This is a Python Flask web application that provides a chatbot interface for answering questions based on the content of documents stored in an Amazon S3 bucket. The chatbot uses:

*   **Data Source:**  Files in various text-based formats (TXT, PDF, CSV, Excel, DOCX, etc.) from an S3 bucket.
*   **Language Model:** Google Gemini 1.5 Flash (using the `gemini-1.5-flash-latest` model via the Google Generative AI API).
*   **Semantic Search:** Sentence Transformers for generating embeddings and performing semantic search to find relevant document chunks for better question answering.
*   **Database:** MongoDB for storing chat history (questions and responses).
*   **Frontend:** A simple and clean web interface built with HTML, CSS, and JavaScript.
*   **Configuration:** Environment variables managed using `.env` for sensitive information.

## Features

*   **Document-Based Answers:** Chatbot answers questions based solely on the content of documents you provide in your S3 bucket.
*   **Multi-File Format Support:**  Processes TXT, PDF, CSV, Excel (xlsx, xls), and DOCX files.
*   **Semantic Search:** Uses sentence embeddings to find semantically relevant information in your documents, leading to more accurate answers.
*   **Chat History:**  Stores questions and responses in a MongoDB database for persistent chat logs.
*   **User-Friendly Web Interface:** Simple and intuitive web interface for interacting with the chatbot.
*   **Environment Variable Configuration:**  Uses `.env` file to securely manage API keys, database credentials, and S3 bucket information.
*   **Easy Deployment (EC2):** Designed to be easily deployed on an EC2 instance.

## Architecture Flow - Step-by-Step

   +-------------------+
   | 1. User (Frontend) |
   +-------------------+
         |
         | User Request (Question, Page Load)
         v
   +-----------------------+
   | 2. Flask Backend (app.py) |
   +-----------------------+
         |         ^         ^
         |         |         | (Chat History)
         |         |         |
         v         |         |
   +-----------------------+     +---------------------+
   | 3. LLM Interaction  | ----> | 4. Data Processing  |
   |    (llm/gemini_api.py) |     | (data_processing/) |
   +-----------------------+     +---------------------+
         |                           ^         ^
         | Gemini API Request        |         | (Document Data & Embeddings)
         v                           |         |
   +-----------------------+         |         |
   |   Google Gemini API   |         |         |
   +-----------------------+         |         |
         |                           |         |
         | Gemini API Response       |         |
         v                           |         |
   +-----------------------+         |         |
   | 2. Flask Backend (app.py) | <-----         |
   +-----------------------+         |         |
         |                           |         |
         | Response to Frontend      |         |
         v                           |         |
   +-------------------+             |         |
   | 1. User (Frontend) | <-----------         |
   +-------------------+                       |
                                               |
                                               | Startup Data Loading:
   +---------------------+       Load Data &    |
   | 4. Data Processing  | ---->  Embeddings   |
   | (data_processing/) |       <--------------+
   +---------------------+         |
         |                         | Download Files
         |                         v
   +-------------------+      +---------------------+
   | 6. S3 Bucket      | <----| 4. Data Processing  |
   +-------------------+      +---------------------+
                                               |
                                               | Chat History:
   +---------------------+       Store/Retrieve |
   | 2. Flask Backend (app.py) | ---->   History    |
   +---------------------+       <--------------+
         |                         |
         |                         v
   +---------------------+
   | 5. Data Storage     |
   |    (db/MongoDB)    |
   +---------------------+


**Legend:**

*   `+---------+`: Represents a Component/Module
*   `--->`: Data Flow Direction
*   `v`: Data Flow Downwards
*   `^`: Data Flow Upwards
*   `<---`: Data Flow Direction from Right to Left
*   `------->`: Interaction/Function Call


**Explanation of the Flow Diagram:**

1.  **User (Frontend) (1):** This is where the user interacts with the chatbot through the web browser interface.
2.  **Flask Backend (app.py) (2):** This is the central Flask application that orchestrates the entire chatbot workflow. It handles:
    *   Receiving user requests from the Frontend.
    *   Calling the LLM Interaction module.
    *   Interacting with Data Processing for semantic search.
    *   Managing Data Storage for chat history.
    *   Sending responses back to the Frontend.
3.  **LLM Interaction (llm/gemini_api.py) (3):** This module is responsible for:
    *   Generating embeddings for user queries (using Data Processing).
    *   Performing semantic search (using Data Processing).
    *   Constructing prompts for the Gemini API.
    *   Calling the Google Gemini API.
    *   Processing Gemini API responses.
4.  **Data Processing (data_processing/) (4):** This directory contains modules for:
    *   `data_loader.py`: Loading data from S3, chunking text, and triggering embedding generation.
    *   `text_extractor.py`: Extracting text content from different file formats.
    *   `embeddings.py`: Generating and performing semantic search using sentence embeddings.
5.  **Data Storage (db/MongoDB) (5):** This is the MongoDB database where chat history (questions and answers) is stored and retrieved by `db_manager.py`.
6.  **S3 Bucket (6):** This is your Amazon S3 bucket where your document files are stored. Data is loaded from S3 at application startup by `data_loader.py`.
7.  **Google Gemini API:** This is the external Google Generative AI API (using the Gemini model) that is called by `llm/gemini_api.py` to generate chatbot responses based on the provided context and prompts.

**Workflow Paths:**

*   **Question Answering Flow:** Follow the arrows from **User (Frontend)** -> **Flask Backend** -> **LLM Interaction** -> **Data Processing** (for semantic search) -> **Gemini API** -> back through the path to **User (Frontend)**.
*   **Startup Data Loading Flow:**  Follow the path from **Flask Backend** -> **Data Processing** -> **S3 Bucket** and back to **Data Processing** and then back to **Flask Backend** (for initial data loading and embedding generation).
*   **Chat History Flow:** Follow the path from **Flask Backend** <-> **Data Storage (MongoDB)** for saving and retrieving chat history.


## Setup Instructions

### Prerequisites

*   **Python 3.9 or higher**
*   **pip** (Python package installer)
*   **MongoDB Database:** You need access to a running MongoDB database instance.
*   **Google Gemini API Key:** Obtain a Google Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey) or [Vertex AI](https://cloud.google.com/vertex-ai).
*   **AWS Account and S3 Bucket:** You need an AWS account and an S3 bucket where your document files are stored. (If you are accessing S3 from an EC2 instance with an IAM role, you might not need explicit AWS keys in `.env`).

### Installation

1.  **Clone the repository:**
    ```bash
    git clone -b neural-network https://github.com/nani-1205/chatbot-app.git  chatbot-webapp
    cd chatbot-webapp
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Create a `.env` file in the root directory of the `chatbot-webapp` project.
    *   Add the following environment variables to `.env`, replacing the placeholder values with your actual credentials and configurations:

        ```env
        GOOGLE_API_KEY=YOUR_GEMINI_API_KEY
        MONGODB_USERNAME=your_mongodb_username
        MONGODB_PASSWORD=your_mongodb_password
        MONGODB_HOST=your_mongodb_host_address
        MONGODB_PORT=27017
        MONGODB_AUTH_SOURCE=admin  # Or your MongoDB authSource database
        DATABASE_NAME=chatbot_db
        COLLECTION_NAME=chat_history
        S3_BUCKET_NAME=your-s3-bucket-name
        AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID # (Optional, if needed for S3 access)
        AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY # (Optional, if needed for S3 access)
        AWS_REGION_NAME=your-aws-region # e.g., ap-south-2 (Optional, if needed for S3 access)
        ```
        **Important:**  Keep your `.env` file secure and do not commit it to version control if it contains sensitive information.

### Running the Application

1.  **Start the Flask development server:**
    ```bash
    python app.py
    ```
    The application will be accessible at `http://127.0.0.1:5000/` in your web browser.

2.  **Run with PM2 (for more robust execution, especially on EC2):**
    ```bash
    pm2 start app.py --update-env
    ```
    You can check the application logs using `pm2 logs app`.

### Usage

1.  **Access the Chatbot in your Browser:** Open your web browser and go to `http://127.0.0.1:5000/` (or the public IP/DNS of your EC2 instance if deployed).
2.  **Interact with the Chatbot:** Type your question in the "Type your question here..." input box and click "Send".
3.  **View Responses:** The chatbot's responses will appear in the chat history area.
4.  **Chat History:** The chat history is saved in the MongoDB database and will be displayed when you reload the page.

### Deployment to EC2 (Basic Steps)

1.  **Launch an EC2 Instance:** Launch an EC2 instance (e.g., Ubuntu) and ensure it has network access (security groups allowing HTTP/HTTPS traffic).
2.  **SSH into EC2 Instance:** Connect to your EC2 instance using SSH.
3.  **Install Python and Dependencies:** Install Python, `pip`, and then clone your `chatbot-webapp` repository to the EC2 instance and install dependencies using `pip install -r requirements.txt`.
4.  **Configure `.env` on EC2:** Create and configure the `.env` file on your EC2 instance with your API keys and database credentials.
5.  **Run the App on EC2:** You can run the Flask app using `pm2 start app.py --update-env`.  For production, consider using a WSGI server like Gunicorn and a process manager like Supervisor or systemd for better reliability and performance.
6.  **Access the Chatbot via EC2 Public IP/DNS:** Access your chatbot using the public IP address or public DNS name of your EC2 instance, followed by port `5000` (e.g., `http://your-ec2-public-ip:5000`).

### Dependencies

*   Flask
*   python-dotenv
*   boto3
*   PyPDF2
*   python-docx
*   pandas
*   openpyxl
*   google-generativeai
*   pymongo
*   sentence-transformers
*   numpy
*   scikit-learn

---

