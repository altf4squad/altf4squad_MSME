import os, sqlite3, csv, smtplib, time, threading, re, random
import json
from email.message import EmailMessage
from flask import Flask, render_template, request, jsonify, redirect, url_for
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.template_filter('from_json')
def from_json_filter(value):
    return json.loads(value)

DB_NAME = 'msme_agentic_final.db'
WATCH_DIR = 'whatsapp_logs'
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Ensure the watcher directory exists
if not os.path.exists(WATCH_DIR):
    os.makedirs(WATCH_DIR)

# --- AGENTIC AI LOGIC ---
class SmartNegotiationAgent:
    def draft_email(self, item_name, current_stock, threshold, supplier_name, units=500, price=None, instruction=None):
        prompt = f"""
        You are an MSME Procurement AI. Draft a professional restocking email.
        Item: {item_name}
        Current Stock: {current_stock}
        Threshold: {threshold}
        Supplier: {supplier_name}
        Requested Units: {units}
        {f'Target Price: ₹{price}' if price else ''}
        {f'Human Instruction: {instruction}' if instruction else ''}
        
        Keep the draft professional, mention that our AI systems triggered this due to low stock, and use a firm but respectful negotiation tone.
        Return ONLY the email draft (Subject and Body).
        """
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        except Exception as e:
            urgency = "CRITICAL" if current_stock < (threshold * 0.2) else "URGENT"
            return (f"Subject: [{urgency}] Restock Request for {item_name}\n\n"
                    f"Dear {supplier_name},\n\n"
                    f"Our system indicates {item_name} is low ({current_stock} units). "
                    f"We need {units} units. Please provide an invoice.")

class WhatsAppAgent:
    def is_business_relevant(self, text):
        """The Gatekeeper: Checks if a message is worth processing."""
        prompt = f"""
        Analyze if the following WhatsApp message contains genuine business value:
        - Customer feedback (positive or negative)
        - Product/Price queries
        - New sales leads
        - Urgent complaints or requests
        
        If it's just 'Hi', 'Good morning', general chatter, or noise, respond with NO.
        If it's business relevant, respond with YES.
        
        Message: "{text}"
        Answer (YES/NO):"""
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5
            )
            return "YES" in completion.choices[0].message.content.upper()
        except:
            return True # Fallback to processing if API fails

    def analyze_chat(self, raw_text):
        # First, filter the noise
        if not self.is_business_relevant(raw_text):
            print("🛑 Gatekeeper: Message ignored (Noise/General Chatter).")
            return None

        prompt = f"""
        You are an MSME Business Analyst AI. Analyze the following WhatsApp chat logs and extract key business insights.
        Return the response in strictly valid JSON format with the following keys:
        - "summary": A brief 1-sentence summary of the interaction.
        - "sentiment": "Positive", "Neutral", or "Negative".
        - "revenue_potential": Estimated INR value of potential sales mentioned.
        - "leads": A list of names/items mentioned for potential future sales.
        - "urgent_tasks": A list of immediate actions required by the owner.

        Chat Logs:
        {raw_text}
        """
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Groq Error: {e}")
            return None

    def save_insight(self, raw_text, analysis_json):
        try:
            data = json.loads(analysis_json)
            conn = get_db()
            conn.execute('''INSERT INTO whatsapp_insights (raw_text, processed_json, summary, sentiment, revenue) 
                         VALUES (?, ?, ?, ?, ?)''',
                         (raw_text, analysis_json, data['summary'], data['sentiment'], float(data.get('revenue_potential', 0))))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"DB Error: {e}")
            return False

# --- DATABASE ENGINE ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, mrp REAL, sp REAL, discount TEXT, cost REAL, stock INTEGER, min_limit INTEGER)''')
    conn.execute('CREATE TABLE IF NOT EXISTS suppliers (item_name TEXT, name TEXT, email TEXT)')
    conn.execute('''CREATE TABLE IF NOT EXISTS negotiations 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, item_name TEXT, supplier_email TEXT, 
                  draft TEXT, invoice_amount REAL, status TEXT, units INTEGER DEFAULT 500, last_reply TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS whatsapp_insights 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, raw_text TEXT, processed_json TEXT, summary TEXT, 
                  sentiment TEXT, revenue REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def send_mail(to_email, subject, body, from_email="procurement@msme-os.ai"):
    # Mock mail sending - can be replaced with real SMTP if needed
    print(f"Sending mail to {to_email} | Subject: {subject}")
    return True

def simulate_agent_read(item_name, supplier_email):
    time.sleep(5) 
    conn = get_db()
    neg = conn.execute('SELECT * FROM negotiations WHERE item_name=? AND status="INQUIRY_SENT"', (item_name,)).fetchone()
    if neg:
        raw_reply = f"Hi, confirming we have {neg['units']} units available for ₹{neg['invoice_amount']}. Ready to ship."
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an AI analyzing supplier emails. Extract the key sentiment and confirmation."},
                    {"role": "user", "content": f"Analyze this reply: {raw_reply}"}
                ],
            )
            analysis = completion.choices[0].message.content
        except:
            analysis = "Invoice data validated. Stock is ready for shipment."

        display_text = f"{analysis}"
        conn.execute('UPDATE negotiations SET status="INVOICE_RECEIVED", last_reply=? WHERE id=?', (display_text, neg['id']))
        conn.commit()
    conn.close()

def autonomous_reports_watcher():
    """Background thread that watches a folder for new WhatsApp logs."""
    agent = WhatsAppAgent()
    print(f"🤖 Agentic Reports Watcher started. Watching '{WATCH_DIR}'...")
    
    while True:
        try:
            if not os.path.exists(WATCH_DIR): os.makedirs(WATCH_DIR)
            files = [f for f in os.listdir(WATCH_DIR) if f.endswith('.txt')]
            for file in files:
                file_path = os.path.join(WATCH_DIR, file)
                print(f"📥 New log detected: {file}. Processing autonomously...")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                
                analysis = agent.analyze_chat(raw_text)
                if analysis:
                    if agent.save_insight(raw_text, analysis):
                        print(f"✅ Successfully processed {file}. Removing from watch folder.")
                        os.remove(file_path)
                
            time.sleep(10) # Check every 10 seconds
        except Exception as e:
            print(f"Watcher Error: {e}")
            time.sleep(10)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/inventory')
def inventory():
    if not os.path.exists(DB_NAME): init_db()
    conn = get_db()
    
    # Fetch all items for calculation
    all_items = conn.execute('SELECT * FROM inventory').fetchall()
    total_inventory_value = sum(item['stock'] * item['cost'] for item in all_items)
    low_stock_items_db = [item for item in all_items if item['stock'] < item['min_limit']]
    low_stock_count = len(low_stock_items_db)
    
    # Pagination logic
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start = (page - 1) * per_page
    paginated_items = all_items[start:start+per_page]
    total_pages = (len(all_items) + per_page - 1) // per_page if all_items else 1
    
    # Fetch negotiations for low stock items
    negs = conn.execute('SELECT * FROM negotiations WHERE status != "ORDER_PLACED"').fetchall()
    
    conn.close()
    
    return render_template('inventory.html', 
                           items=paginated_items, 
                           low_stock_items=low_stock_items_db,
                           negotiations=negs,
                           page=page, 
                           total_pages=total_pages,
                           total_value=f"₹{total_inventory_value:,.2f}",
                           ordered=0, # Placeholder
                           low_stock=low_stock_count)

@app.route('/upload-all', methods=['POST'])
def upload_all():
    inv_file = request.files.get('inventory')
    sup_file = request.files.get('suppliers')
    if inv_file and sup_file:
        init_db() # Ensure tables exist
        conn = get_db()
        # Simple reset for demo purposes
        conn.execute('DELETE FROM inventory')
        conn.execute('DELETE FROM suppliers')
        conn.execute('DELETE FROM negotiations')
        
        # Save and process inventory
        inv_file.save('temp_inv.csv')
        with open('temp_inv.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Flexible header mapping
                name = row.get('item') or row.get('name') or row.get('Item Name')
                cost = float(row.get('price') or row.get('cost') or row.get('Cost Price') or 0)
                mrp = float(row.get('mrp') or row.get('MRP') or 0)
                sp = float(row.get('sp') or row.get('Selling Price') or 0)
                stock = int(row.get('stock') or row.get('Stock') or 0)
                min_limit = int(row.get('min_limit') or row.get('Threshold') or row.get('Min Limit') or 10)
                discount = row.get('discount') or row.get('Discount') or '0%'
                
                if name:
                    conn.execute('''INSERT INTO inventory (name, mrp, sp, discount, cost, stock, min_limit) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                 (name, mrp, sp, discount, cost, stock, min_limit))
        
        # Save and process suppliers
        sup_file.save('temp_sup.csv')
        with open('temp_sup.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = row.get('item') or row.get('item_name') or row.get('Product')
                s_name = row.get('supplier_name') or row.get('Supplier') or row.get('Name')
                s_email = row.get('supplier_email') or row.get('Email') or row.get('Contact')
                if item and s_name:
                    conn.execute('INSERT INTO suppliers VALUES (?, ?, ?)', (item, s_name, s_email))
        
        # Auto-trigger negotiations for low stock items
        agent = SmartNegotiationAgent()
        low_items = conn.execute('''SELECT i.*, s.name as s_name, s.email 
                                 FROM inventory i 
                                 JOIN suppliers s ON i.name=s.item_name 
                                 WHERE i.stock < i.min_limit''').fetchall()
        for item in low_items:
            ai_draft = agent.draft_email(item['name'], item['stock'], item['min_limit'], item['s_name'])
            conn.execute('''INSERT INTO negotiations (item_name, supplier_email, draft, status, invoice_amount) 
                         VALUES (?, ?, ?, ?, ?)''',
                         (item['name'], item['email'], ai_draft, "AWAITING_HUMAN", item['cost']*500))
        
        conn.commit()
        conn.close()
    return redirect(url_for('inventory'))

@app.route('/edit-agent', methods=['POST'])
def edit_agent():
    data = request.json
    neg_id, instruction = data['id'], data['instruction'].lower()
    conn = get_db()
    neg_detail = conn.execute('''SELECT n.*, i.stock, i.min_limit, i.cost, s.name 
                                FROM negotiations n 
                                JOIN inventory i ON n.item_name = i.name 
                                JOIN suppliers s ON n.item_name = s.item_name 
                                WHERE n.id=?''', (neg_id,)).fetchone()
    
    if not neg_detail:
        return jsonify({"success": False, "error": "Negotiation not found"})

    new_units = neg_detail['units']
    nums = re.findall(r'\d+', instruction)
    if nums:
        for n in nums:
            if int(n) >= 50: new_units = int(n)
    
    discount = 0.85 if "discount" in instruction or "off" in instruction else 1.0
    new_price = (neg_detail['cost'] * new_units) * discount
    
    agent = SmartNegotiationAgent()
    updated_draft = agent.draft_email(neg_detail['item_name'], neg_detail['stock'], neg_detail['min_limit'], neg_detail['name'], 
                                     units=new_units, price=new_price, instruction=instruction)
    
    conn.execute('UPDATE negotiations SET draft=?, units=?, invoice_amount=? WHERE id=?', (updated_draft, new_units, new_price, neg_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_draft": updated_draft})

@app.route('/send-inquiry/<int:id>', methods=['POST'])
def send_inquiry(id):
    conn = get_db()
    neg = conn.execute('SELECT * FROM negotiations WHERE id=?', (id,)).fetchone()
    if neg:
        send_mail(neg['supplier_email'], f"Supply Inquiry: {neg['item_name']}", neg['draft'])
        conn.execute('UPDATE negotiations SET status="INQUIRY_SENT" WHERE id=?', (id,))
        conn.commit()
        threading.Thread(target=simulate_agent_read, args=(neg['item_name'], neg['supplier_email'])).start()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/finalize-order/<int:id>', methods=['POST'])
def finalize_order(id):
    conn = get_db()
    neg = conn.execute('SELECT * FROM negotiations WHERE id=?', (id,)).fetchone()
    if neg:
        send_mail(neg['supplier_email'], "PURCHASE ORDER CONFIRMED", f"Proceed with shipping {neg['units']} units.")
        conn.execute('UPDATE inventory SET stock = stock + ? WHERE name=?', (neg['units'], neg['item_name']))
        conn.execute('UPDATE negotiations SET status="ORDER_PLACED" WHERE id=?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/reports')
def reports():
    if not os.path.exists(DB_NAME): init_db()
    conn = get_db()
    insights = conn.execute('SELECT * FROM whatsapp_insights ORDER BY timestamp DESC').fetchall()
    
    total_revenue_potential = sum(i['revenue'] for i in insights if i['revenue'])
    positive_interactions = len([i for i in insights if i['sentiment'] == 'Positive'])
    
    conn.close()
    return render_template('reports.html', insights=insights, total_revenue=total_revenue_potential, pos_count=positive_interactions)

@app.route('/process-whatsapp', methods=['POST'])
def process_whatsapp():
    raw_text = request.form.get('chat_log')
    if raw_text:
        agent = WhatsAppAgent()
        analysis_json = agent.analyze_chat(raw_text)
        if analysis_json:
            if agent.save_insight(raw_text, analysis_json):
                return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Filtered as noise by Gatekeeper"})
    return jsonify({"success": False})

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    Real-time Webhook Entry Point. 
    This is where services like Twilio or Meta will send messages.
    """
    data = request.json
    # Logic depends on the service provider (e.g., Twilio sends 'Body')
    message_text = data.get('Body') or data.get('message', {}).get('text')
    
    if message_text:
        agent = WhatsAppAgent()
        # Processing happens autonomously
        analysis = agent.analyze_chat(message_text)
        if analysis:
            agent.save_insight(message_text, analysis)
            return jsonify({"status": "processed"}), 200
            
    return jsonify({"status": "ignored"}), 200

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/support')
def support():
    return render_template('support.html')

if __name__ == '__main__':
    init_db()
    # Start the autonomous watcher in a background thread
    threading.Thread(target=autonomous_reports_watcher, daemon=True).start()
    app.run(debug=True, port=5000)
