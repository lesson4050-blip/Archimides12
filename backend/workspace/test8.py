import random
from collections import defaultdict

products = ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Headphones', 'Webcam', 'USB Drive', 'Adapter']

# 1. Generate 100 random sales records
sales_records = []
for _ in range(100):
    product = random.choice(products)
    quantity = random.randint(1, 10)
    price = round(random.uniform(10.0, 500.0), 2)
    sales_records.append({'product': product, 'quantity': quantity, 'price': price})

# 2. Calculate total revenue per product
revenue_per_product = defaultdict(float)
for record in sales_records:
    revenue = record['quantity'] * record['price']
    revenue_per_product[record['product']] += revenue

# 3. Find the top 3 products
top_products = sorted(revenue_per_product.items(), key=lambda x: x[1], reverse=True)[:3]

# 4. Save summary report
with open('test8_report.txt', 'w') as f:
    f.write("Sales Summary Report\n")
    f.write("==================\n")
    f.write("Top 3 Products by Revenue:\n")
    for product, revenue in top_products:
        f.write(f"- {product}: ${revenue:.2f}\n")
    f.write("\nFull Revenue Breakdown:\n")
    for product, revenue in sorted(revenue_per_product.items()):
        f.write(f"{product}: ${revenue:.2f}\n")

print("Script executed successfully. Report saved to /home/ubuntu/workspace/test8_report.txt")
