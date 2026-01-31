import os, sqlite3, csv, smtplib, time, threading, re, random
from email.message import EmailMessage
from flask import Flask, render_template, request, jsonify, redirect, url_for
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DB_NAME = 'msme_agentic_final.db'
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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

# --- DATABASE ENGINE ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def reset_system():
    conn = get_db()
    conn.execute('DROP TABLE IF EXISTS inventory')
    conn.execute('DROP TABLE IF EXISTS suppliers')
    conn.execute('DROP TABLE IF EXISTS negotiations')
    conn.execute('CREATE TABLE inventory (id INTEGER PRIMARY KEY, item TEXT, stock INTEGER, min_limit INTEGER, price REAL)')
    conn.execute('CREATE TABLE suppliers (item TEXT, name TEXT, email TEXT)')
    conn.execute('''CREATE TABLE negotiations (id INTEGER PRIMARY KEY, item TEXT, supplier_email TEXT, 
                 draft TEXT, invoice_amount REAL, status TEXT, units INTEGER DEFAULT 500, last_reply TEXT)''')
    conn.commit()
    conn.close()

def send_mail(to_email, subject, body, from_email="procurement@msme-os.ai"):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['To'] = to_email
    msg['From'] = from_email
    try:
        with smtplib.SMTP('localhost', 1025) as s: 
            s.send_message(msg)
        return True
    except: return False

def simulate_agent_read(item_name, supplier_email):
    time.sleep(5) 
    conn = get_db()
    neg = conn.execute('SELECT * FROM negotiations WHERE item=? AND status="INQUIRY_SENT"', (item_name,)).fetchone()
    if neg:
        raw_reply = f"Hi, confirming we have {neg['units']} units available for ₹{neg['invoice_amount']}. Ready to ship."
        
        # USE AI TO ANALYZE REPLY
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
            analysis = "Invoice data validated."

        display_text = f"🤖 AGENT ANALYSIS: {analysis}"
        send_mail("procurement@msme-os.ai", f"RE: {item_name} Restock", raw_reply, from_email=supplier_email)
        conn.execute('UPDATE negotiations SET status="INVOICE_RECEIVED", last_reply=? WHERE id=?', (display_text, neg['id']))
        conn.commit()
    conn.close()

@app.route('/')
def index():
    if not os.path.exists(DB_NAME): reset_system()
    conn = get_db()
    inv = conn.execute('SELECT * FROM inventory').fetchall()
    negs = conn.execute('SELECT * FROM negotiations WHERE status != "ORDER_PLACED"').fetchall()
    conn.close()
    return render_template('negotiator.html', inventory=inv, negotiations=negs)

@app.route('/upload-all', methods=['POST'])
def upload_all():
    inv_file = request.files.get('inventory')
    sup_file = request.files.get('suppliers')
    if inv_file and sup_file:
        reset_system()
        conn = get_db()
        inv_file.save('temp_inv.csv')
        with open('temp_inv.csv', 'r') as f:
            for row in csv.DictReader(f):
                conn.execute('INSERT INTO inventory (item, stock, min_limit, price) VALUES (?, ?, ?, ?)',
                             (row['item'], int(row['stock']), int(row['min_limit']), float(row['price'])))
        sup_file.save('temp_sup.csv')
        with open('temp_sup.csv', 'r') as f:
            for row in csv.DictReader(f):
                conn.execute('INSERT INTO suppliers VALUES (?, ?, ?)', (row['item'], row['supplier_name'], row['supplier_email']))
        
        agent = SmartNegotiationAgent()
        low_items = conn.execute('SELECT i.*, s.name, s.email FROM inventory i JOIN suppliers s ON i.item=s.item WHERE i.stock < i.min_limit').fetchall()
        for item in low_items:
            ai_draft = agent.draft_email(item['item'], item['stock'], item['min_limit'], item['name'])
            conn.execute('INSERT INTO negotiations (item, supplier_email, draft, status, invoice_amount) VALUES (?, ?, ?, ?, ?)',
                         (item['item'], item['email'], ai_draft, "AWAITING_HUMAN", item['price']*500))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/edit-agent', methods=['POST'])
def edit_agent():
    data = request.json
    neg_id, instruction = data['id'], data['instruction'].lower()
    conn = get_db()
    neg_detail = conn.execute('''SELECT n.*, i.stock, i.min_limit, i.price, s.name 
                                FROM negotiations n 
                                JOIN inventory i ON n.item = i.item 
                                JOIN suppliers s ON n.item = s.item 
                                WHERE n.id=?''', (neg_id,)).fetchone()
    
    new_units = neg_detail['units']
    nums = re.findall(r'\d+', instruction)
    if nums:
        for n in nums:
            if int(n) >= 50: new_units = int(n)
    
    discount = 0.85 if "discount" in instruction or "off" in instruction else 1.0
    new_price = (neg_detail['price'] * new_units) * discount
    
    agent = SmartNegotiationAgent()
    updated_draft = agent.draft_email(neg_detail['item'], neg_detail['stock'], neg_detail['min_limit'], neg_detail['name'], units=new_units, price=new_price, instruction=instruction)
    
    conn.execute('UPDATE negotiations SET draft=?, units=?, invoice_amount=? WHERE id=?', (updated_draft, new_units, new_price, neg_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_draft": updated_draft})

@app.route('/send-inquiry/<int:id>', methods=['POST'])
def send_inquiry(id):
    conn = get_db()
    neg = conn.execute('SELECT * FROM negotiations WHERE id=?', (id,)).fetchone()
    send_mail(neg['supplier_email'], f"Supply Inquiry: {neg['item']}", neg['draft'])
    conn.execute('UPDATE negotiations SET status="INQUIRY_SENT" WHERE id=?', (id,))
    conn.commit()
    threading.Thread(target=simulate_agent_read, args=(neg['item'], neg['supplier_email'])).start()
    conn.close()
    return redirect(url_for('index'))

@app.route('/finalize-order/<int:id>', methods=['POST'])
def finalize_order(id):
    conn = get_db()
    neg = conn.execute('SELECT * FROM negotiations WHERE id=?', (id,)).fetchone()
    if neg:
        send_mail(neg['supplier_email'], "PURCHASE ORDER CONFIRMED", f"Proceed with shipping {neg['units']} units.")
        conn.execute('UPDATE inventory SET stock = stock + ? WHERE item=?', (neg['units'], neg['item']))
        conn.execute('UPDATE negotiations SET status="ORDER_PLACED" WHERE id=?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)