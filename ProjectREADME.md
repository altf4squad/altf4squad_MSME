# 🤖 AgenticOS for MSMEs
### *The Autonomous Operating System for Modern Small Businesses*

**AgenticOS** is not just a dashboard; it's a collection of autonomous AI agents working together to manage inventory, analyze customer feedback, and provide real-time business intelligence for MSMEs.

---

## 🚀 Key Features

### 1. 📦 Agentic Inventory Management
- **Autonomous Decision Making**: When stock levels drop below the minimum limit, the "Logistics Agent" automatically generates professional restock emails for suppliers.
- **Smart Tracking**: Real-time inventory valuation and low-stock alerting systems.

### 2. 💬 Real-Time AI Gatekeeper (WhatsApp Sync)
- **Intelligent Filtering**: A dedicated agent monitors WhatsApp group chats (via real-time webhooks) and filters out "noise" (memes, greetings).
- **Value Extraction**: Only high-value data like customer feedback, pricing queries, and new sales leads are synchronized to the dashboard.
- **Background Autonomy**: An autonomous watcher scans for manual chat logs and processes them instantly.

### 3. 📊 Advanced Analytics & Conversational BI
- **KPI Command Center**: Track Total Asset Value, Revenue Potential, and Active SKUs at a glance.
- **Dynamic Data Analyst**: A Groq-powered Llama-3 agent that "reads" your database. Ask questions like *"Which item is my best seller?"* or *"Summarize my low stock issues"* in natural language and get instant answers.
- **Rich Visualizations**: Live Chart.js integration for bar and donut charts showing distribution and valuation.

---

## 🏗️ Architecture

graph TD
    subgraph Users
        User((User))
    end

    subgraph "AgenticOS Core"
        Dashboard[Advanced Dashboard UI]
        SQLite[(Inventory & Insights DB)]
        
        subgraph Agents
            AI_Analyst[Groq Llama-3 Analyst Agent]
            Gatekeeper[AI Gatekeeper Agent]
            Logistics[Logistics Agent]
        end
    end

    subgraph External
        WhatsApp[WhatsApp Groups]
        SupplierEmail[Supplier]
    end

    %% Flows
    User -->|Browser| Dashboard
    Dashboard -->|Natural Language Query| AI_Analyst
    AI_Analyst -->|Read Data| SQLite
    
    WhatsApp -->|Webhook JSON| Gatekeeper
    Gatekeeper -->|Filter Comp/Noise| SQLite
    
    SQLite -.->|Monitor Low Stock| Logistics
    Logistics -->|Send Restock Request| SupplierEmail

---

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **AI Core**: Groq API (Llama-3-70b/8b)
- **Frontend**: Vanilla CSS3, modern JavaScript, Chart.js
- **Database**: SQLite3 (Agentic Sync)
- **Background Tasks**: Autonomous Watcher Threads

---

## ⚡ Quick Setup

1. **Clone & Setup Environment**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AI**:
   Create a `.env` file and add your Groq API Key:
   ```env
   GROQ_API_KEY=your_key_here
   ```

3. **Run AgenticOS**:
   ```bash
   python app.py
   ```
   *The background agent will automatically start watching `whatsapp_logs/`.*

---

