import sqlite3
import random

def main():
    db_path = '/home/ubuntu/workspace/sales.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, product TEXT, price REAL, quantity INTEGER)")

    # Products to choose from
    products = ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'USB Drive', 'Headphones', 'Webcam', 'Printer']

    # Insert 50 rows of random data
    for i in range(1, 51):
        product = random.choice(products)
        price = round(random.uniform(10.0, 500.0), 2)
        quantity = random.randint(1, 10)
        cursor.execute("INSERT INTO orders (product, price, quantity) VALUES (?, ?, ?)", (product, price, quantity))

    conn.commit()

    # Calculate total revenue
    cursor.execute("SELECT SUM(price * quantity) FROM orders")
    total_revenue = cursor.fetchone()[0]

    print(f"Total Revenue: ${total_revenue:.2f}")

    conn.close()

if __name__ == '__main__':
    main()