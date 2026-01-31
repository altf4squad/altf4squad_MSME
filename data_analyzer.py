import os
import pandas as pd
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv


from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from typing import TypedDict


load_dotenv()

app = Flask(__name__)


GROQ_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model="llama-3.3-70b-versatile", 
    groq_api_key=GROQ_KEY,
    temperature=0.2
)


current_data_context = ""


class AgentState(TypedDict):
    raw_data: str
    analysis: str
    decisions: str


def analyzer_node(state: AgentState):
    print("\n--- ⚡ ANALYZER IS ON IT (Groq 70B) ---")
    data = state['raw_data']
    prompt = f"Analyze this MSME data: {data}. Find 3 main problems with deep reasoning. Return ONLY JSON."
    response = llm.invoke(prompt)
    return {"analysis": response.content}

def decision_node(state: AgentState):
    print("\n--- 🧠 DECISION AGENT PROVIDING SOLUTIONS ---")
    analysis = state['analysis']
    prompt = f"Based on: {analysis}, give 2 business decisions with step-by-step logic. Return ONLY JSON."
    response = llm.invoke(prompt)
    return {"decisions": response.content}


builder = StateGraph(AgentState)
builder.add_node("analyzer", analyzer_node)
builder.add_node("decision_maker", decision_node)
builder.set_entry_point("analyzer")
builder.add_edge("analyzer", "decision_maker")
builder.add_edge("decision_maker", END)
graph_executor = builder.compile()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_data():
    global current_data_context
    try:
        file = request.files['file']
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file, engine='openpyxl')
        
        # Save context for Q&A
        current_data_context = df.head(15).to_json(orient='records')
        
        result = graph_executor.invoke({"raw_data": current_data_context})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    user_q = request.json.get('question')
    if not current_data_context:
        return jsonify({"answer": "Pehle data upload karo bhai!"})
    
    prompt = f"Context Data: {current_data_context}\nQuestion: {user_q}\nAnswer with deep reasoning based ONLY on the data."
    res = llm.invoke(prompt)
    return jsonify({"answer": res.content})

if __name__ == "__main__":
    app.run(port=8000, debug=True)