# 🔍 LexScan - AI Document Intelligence Platform

An AI-powered document intelligence platform that reads legal, medical, and general documents, detects important entities, and provides intelligent insights.

## ✨ Features

- 📄 **Multi-Domain Analysis** - Legal, Medical, and General documents
- 🎯 **Entity Extraction** - Automatic detection of persons, organizations, diseases, laws, dates
- 💬 **AI Assistant** - Ask follow-up questions about extracted entities
- 📦 **Batch Processing** - Analyze multiple documents together
- 🌐 **Multi-Language Support** - Translate and analyze 20+ languages
- 📊 **Advanced Analytics** - Domain reasoning and insights
- 📥 **Report Generation** - Download detailed PDF reports
- 📤 **Data Export** - Export as JSON

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git

### Installation

```bash
git clone https://github.com/Meghana0306/LexScan_NER.git
cd LexScan_NER
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

Open: `http://localhost:5000`

## 📊 Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript
- **ML/NLP:** Transformers, spaCy, HuggingFace
- **LLM:** Groq API, Google Gemini
- **PDF:** ReportLab

## 📁 Project Structure

## 📊 Supported Domains

- **Legal** - Contract analysis, case law extraction
- **Medical** - Disease/drug/treatment detection
- **General** - Entity extraction from any text

## 🔐 Security

- API keys in `.env` file (not in repo)
- Input validation on all endpoints
- No secrets in code

## 📝 License

MIT License - See LICENSE file

## 👨‍💻 Author

**Meghana**

- GitHub: [@Meghana0306](https://github.com/Meghana0306)

## 🙏 Acknowledgments

- Hugging Face - Pre-trained models
- FastAPI - Web framework
- Groq - LLM API
