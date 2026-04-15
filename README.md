# 🧠 NeuroQuery — AI-Powered Natural Language to SQL System

## 🚀 Overview
NeuroQuery is an intelligent system that converts natural language queries into SQL, executes them on a relational database, and returns results with full transparency.

It combines LLMs and Retrieval-Augmented Generation (RAG) to understand database schemas and generate accurate SQL queries.

---

## 🎯 Key Features

### ✅ Natural Language → SQL
- Ask questions in plain English  
- Automatically generates SQL queries  
- Supports joins, aggregation, filtering  

### 🧠 RAG-Based Schema Understanding
- Converts database schema into embeddings  
- Retrieves only relevant tables and columns  
- Improves SQL accuracy  

### 🔗 Relationship-Aware Queries
- Uses foreign key relationships  
- Enables correct JOIN generation  

### 🔐 SQL Safety Layer
- Blocks unsafe queries (INSERT, DELETE, DROP)  
- Only allows SELECT operations  

### 🧹 SQL Cleaning
- Removes markdown artifacts (```sql)  
- Normalizes LLM-generated queries  

### 🧠 SQL Validation Layer (sqlglot 🔥)
- Parses SQL using sqlglot  
- Ensures only valid SELECT queries are executed  
- Extracts tables and columns from queries  
- Prevents invalid or hallucinated SQL execution  

---

## 🏗️ Architecture

User Query (CLI / UI)  
↓  
Schema Extraction (PK + FK + Tables)  
↓  
RAG Pipeline (FAISS + Embeddings)  
↓  
LLM (SQL Generation)  
↓  
SQL Cleaning  
↓  
SQL Validation (sqlglot)  
↓  
Safety Check  
↓  
PostgreSQL Execution  
↓  
Results + Debug Output  

---

## ⚙️ Tech Stack

- LLM: Groq API (LLaMA 3.1 8B Instant)  
- Database: PostgreSQL (Neon DB)  
- Backend: Python (psycopg2)  
- Frontend: Streamlit  
- RAG: FAISS + Sentence Transformers  
- SQL Parser: sqlglot  
- Embeddings: all-MiniLM-L6-v2  

---

## 📂 Project Structure

NeuroQuery/  
│  
├── db/                # Database connection & execution  
├── llm/               # LLM integration & prompts  
├── rag/               # Retrieval pipeline  
├── utils/             # Validation and schema tools  
│   └── validator.py   # sqlglot-based SQL validation  
├── memory/            # Chat memory (future)  
├── visualization/     # Plotting  
│  
├── app.py             # Streamlit UI  
├── main.py            # CLI interface  
├── requirements.txt  
├── .env.example  
└── README.md  

---

## 🧪 Example Queries

- Show all users  
- Total orders by each user  
- Top customers by spending  
- Average rating per product  

---

## 🧠 SQL Validation (sqlglot Integration)

The system uses sqlglot to validate and parse SQL queries before execution.

### 🔍 Capabilities
- Validates SQL syntax  
- Ensures only SELECT queries  
- Extracts tables used in query  
- Extracts columns used in query  

---

## 🔄 Updated Query Flow

### Before:
LLM → SQL → Execute  

### Now:
LLM → SQL  
↓  
sqlglot validation  
↓  
table & column extraction  
↓  
safety check  
↓  
EXECUTE  

---

## ⚠️ Current Limitations

- May generate suboptimal joins  
- Limited semantic understanding  
- No join path optimization yet  

---

## 🔮 Future Improvements

- Agent-based architecture (LangGraph)  
- Join graph engine  
- Semantic layer  
- Auto query correction loop  
- Local LLM via Ollama  

---

## 🛠️ Setup Instructions

### 1. Clone the repository
git clone https://github.com/SUJALGOYALL/neuroquery.git
cd neuroquery  

### 2. Create virtual environment
python -m venv venv  
venv\Scripts\activate  

### 3. Install dependencies
pip install -r requirements.txt  

### 4. Setup environment variables

Create a `.env` file:

GROQ_API_KEY=your_api_key_here  
DB_HOST=your_host  
DB_USER=your_user  
DB_PASSWORD=your_password  
DB_NAME=your_db  

---

### 5. Run the app

#### Streamlit UI
streamlit run app.py  

#### CLI mode
python main.py  

---

## 🎯 Vision

To build a fully autonomous AI Data Analyst system that:
- Understands natural language  
- Generates SQL queries  
- Works on any database  
- Runs locally  

---

## 💡 Author

Sujal Goyal  
MNC (Mathematics & Computing)  
AI/ML + Data Systems Enthusiast  

---

## ⭐ Support

If you like this project, consider giving it a star ⭐