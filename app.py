from flask import Flask, render_template, request

app = Flask(__name__)

# Mock Data for Inventory
inventory_items = [
    {"id": i, "name": f"Item {i}", "mrp": 1000 + i*10, "sp": 900 + i*10, "discount": "10%", "cost": 700 + i*10, "stock": 50 - i}
    for i in range(1, 51)
]

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/inventory')
def inventory():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = inventory_items[start:end]
    
    total_inventory_value = sum(item['stock'] * item['cost'] for item in inventory_items)
    ordered_items_count = 12 # Mock
    low_stock_count = len([item for item in inventory_items if item['stock'] < 10])
    total_skus = len(inventory_items)
    
    total_pages = (len(inventory_items) + per_page - 1) // per_page
    
    return render_template('inventory.html', 
                           items=paginated_items, 
                           page=page, 
                           total_pages=total_pages,
                           total_value=f"₹{total_inventory_value:,}",
                           ordered=ordered_items_count,
                           low_stock=low_stock_count,
                           skus=total_skus)

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/orders')
def orders():
    return render_template('orders.html')

@app.route('/support')
def support():
    return render_template('support.html')

if __name__ == '__main__':
    app.run(debug=True)
