# Multi-Agent AI Systems with CrewAI

A collection of multi-agent AI applications built with [CrewAI](https://crewai.com) framework, demonstrating collaborative AI agents working together to solve complex tasks.

## 🚀 Projects

### 1. Financial Analysis (`Financial_Analysis.py`)
A hierarchical multi-agent system for stock market analysis and trading recommendations.

**Agents:**
- **Data Analyst** - Monitors and analyzes market data using statistical modeling
- **Trading Strategy Developer** - Develops and tests trading strategies
- **Trade Advisor** - Suggests optimal trade execution strategies
- **Risk Advisor** - Evaluates risks and suggests mitigation strategies

**Features:**
- Real-time market data analysis
- Trading strategy development
- Risk assessment and management
- Hierarchical process with manager LLM

---

### 2. Job Application Tailor (`Tailor_Job_App.py`)
An AI-powered job application assistant that customizes resumes and prepares interview materials.

**Agents:**
- **Tech Job Researcher** - Analyzes job postings to extract requirements
- **Personal Profiler** - Builds comprehensive candidate profiles from GitHub and resume
- **Resume Strategist** - Tailors resumes to match job requirements
- **Interview Preparer** - Creates interview questions and talking points

**Outputs:**
- `tailored_resume.md` - Customized resume for the job
- `interview_materials.md` - Interview preparation document

---

### 3. Event Planning (`Event_Planning.py`)
A collaborative system for planning and organizing events.

**Agents:**
- **Venue Coordinator** - Identifies and books appropriate venues
- **Logistics Manager** - Manages catering, equipment, and logistics
- **Marketing Communications Agent** - Handles event marketing and communications

**Features:**
- Venue search and booking
- Logistics coordination
- Marketing strategy development

---

### 4. Customer Support (`Customer_Support.py`)
A quality-focused customer support system with built-in QA.

**Agents:**
- **Senior Support Representative** - Provides friendly, helpful customer support
- **Support Quality Assurance Specialist** - Ensures support quality and completeness

**Features:**
- Role-playing for realistic support interactions
- Delegation between agents for quality assurance
- Web scraping and search capabilities

---

### 5. Customer Outreach (`Tools_Customer_Outreach.py`)
A sales-focused system for lead generation and nurturing.

**Agents:**
- **Sales Representative** - Identifies high-value leads
- **Lead Sales Representative** - Nurtures leads with personalized communications

**Features:**
- Lead identification and scoring
- Personalized outreach messages
- Directory and file reading for sales instructions

---

## 📋 Prerequisites

- Python 3.13+
- API Keys (set in `.env` file):
  ```
  GROQ_API_KEY=your_groq_key
  HF_TOKEN=your_huggingface_token
  SERPER_API_KEY=your_serper_key
  OPENAI_API_KEY=your_openai_key  # optional
  ```

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Xmen3em/LLM-Projects.git
   cd "LLM Projects/Multi-Agent"
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Or install with pip:
   ```bash
   pip install crewai crewai-tools litellm python-dotenv
   ```

4. Create a `.env` file with your API keys.

## 🚀 Usage

Run any project using Python:

```bash
# Financial Analysis
py -3.13 src/multi_agent/Financial_Analysis.py

# Job Application Tailor
py -3.13 src/multi_agent/Tailor_Job_App.py

# Event Planning
py -3.13 src/multi_agent/Event_Planning.py

# Customer Support
py -3.13 src/multi_agent/Customer_Support.py

# Customer Outreach
py -3.13 src/multi_agent/Tools_Customer_Outreach.py
```

## 🔧 LLM Configuration

The projects support multiple LLM providers via LiteLLM:

```python
# HuggingFace
manager_llm = LLM(model="huggingface/Qwen/Qwen2.5-72B-Instruct")

# OpenAI
manager_llm = LLM(model="openai/gpt-4o-mini")
```

## 📁 Project Structure

```
Multi-Agent/
├── src/
│   └── multi_agent/
│       ├── Customer_Support.py
│       ├── Event_Planning.py
│       ├── Financial_Analysis.py
│       ├── Tailor_Job_App.py
│       ├── Tools_Customer_Outreach.py
│       ├── utils.py
│       ├── fake_resume.md
│       ├── venue_details.json
│       └── instructions/
├── pyproject.toml
├── README.md
└── .env
```

## 📚 Key Concepts

- **Agents**: Autonomous AI entities with specific roles, goals, and backstories
- **Tasks**: Specific objectives assigned to agents with expected outputs
- **Crews**: Teams of agents working together on related tasks
- **Tools**: External capabilities like web scraping, search, and file operations
- **Hierarchical Process**: Manager LLM coordinates agent activities


## 👤 Author

**Abdelmoneim Mohamed** - [@Xmen3em](https://github.com/Xmen3em)