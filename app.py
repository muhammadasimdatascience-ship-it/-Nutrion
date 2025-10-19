import os
import sqlite3
import traceback
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from urllib.parse import unquote

# --- Configuration ---
DATABASE_FILE = 'invoice_app_v4.db'
INITIAL_INVOICE_NUMBER = 30

app = Flask(__name__)
CORS(app)


# --- Database Helper Functions ---

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(clear_existing_data=False):
    conn = get_db_connection()
    cursor = conn.cursor()

    if clear_existing_data:
        print("Clearing existing data from all tables...")
        cursor.execute("DROP TABLE IF EXISTS opening_balance_adjustments")
        cursor.execute("DROP TABLE IF EXISTS invoice_items")
        cursor.execute("DROP TABLE IF EXISTS invoices")
        cursor.execute("DROP TABLE IF EXISTS payments")
        cursor.execute("DROP TABLE IF EXISTS parties")
        cursor.execute("DROP TABLE IF EXISTS stock")
        print("Existing tables dropped.")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            initial_opening_balance REAL DEFAULT 0.0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opening_balance_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            adjustment_date TEXT NOT NULL,
            old_balance REAL NOT NULL,
            new_balance REAL NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (party_id) REFERENCES parties (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            party_name TEXT NOT NULL,
            date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            previous_balance REAL NOT NULL, -- This will now store the party's balance *before* this invoice
            grand_total REAL NOT NULL, -- This is previous_balance + total_amount for *this* invoice
            FOREIGN KEY (party_name) REFERENCES parties (name) ON UPDATE CASCADE ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            qty REAL NOT NULL,
            packing TEXT,
            unit_price REAL NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_name TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            remarks TEXT,
            FOREIGN KEY (party_name) REFERENCES parties (name) ON UPDATE CASCADE ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            batch_no TEXT,
            date TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized/checked successfully.")


# --- Helper to calculate the current balance for a party ---
def calculate_current_party_balance(party_name, conn):
    """Calculates the current balance for a party based on initial balance, invoices, and payments."""
    cursor = conn.cursor()

    # Get initial opening balance
    cursor.execute("SELECT initial_opening_balance FROM parties WHERE name = ?", (party_name,))
    party_row = cursor.fetchone()
    initial_balance = party_row['initial_opening_balance'] if party_row and party_row['initial_opening_balance'] is not None else 0.0

    # Sum of all invoice total amounts for this party
    cursor.execute("SELECT SUM(total_amount) FROM invoices WHERE party_name = ?", (party_name,))
    total_invoices_row = cursor.fetchone()
    total_invoices = total_invoices_row[0] if total_invoices_row and total_invoices_row[0] is not None else 0.0

    # Sum of all payment amounts for this party
    cursor.execute("SELECT SUM(amount) FROM payments WHERE party_name = ?", (party_name,))
    total_payments_row = cursor.fetchone()
    total_payments = total_payments_row[0] if total_payments_row and total_payments_row[0] is not None else 0.0

    # Current balance = Initial Balance + Total Invoices - Total Payments
    current_balance = round(initial_balance + total_invoices - total_payments, 2)

    return current_balance


# --- Helper to update subsequent invoice balances after an update/delete ---
def update_subsequent_invoice_balances(party_name, starting_date, starting_invoice_number, conn):
    """
    Recalculates the previous_balance and grand_total for invoices
    that occurred after a specific point in time for a party.
    This is needed after an invoice is updated or deleted.
    """
    cursor = conn.cursor()

    # Get invoices for the party, ordered chronologically from the starting point
    cursor.execute('''
        SELECT id, invoice_number, date, total_amount, previous_balance, grand_total
        FROM invoices
        WHERE party_name = ? AND (date > ? OR (date = ? AND CAST(invoice_number AS INTEGER) > CAST(? AS INTEGER)))
        ORDER BY date ASC, CAST(invoice_number AS INTEGER) ASC
    ''', (party_name, starting_date, starting_date, starting_invoice_number))
    subsequent_invoices = cursor.fetchall()

    # Get the balance *immediately preceding* the starting point
    # This requires calculating the balance up to the transaction just before the starting point
    cursor.execute("SELECT initial_opening_balance FROM parties WHERE name = ?", (party_name,))
    party_row = cursor.fetchone()
    initial_balance = party_row['initial_opening_balance'] if party_row and party_row['initial_opening_balance'] is not None else 0.0

    # Sum of invoice amounts before the starting point
    cursor.execute('''
        SELECT SUM(total_amount) FROM invoices
        WHERE party_name = ? AND (date < ? OR (date = ? AND CAST(invoice_number AS INTEGER) < CAST(? AS INTEGER)))
    ''', (party_name, starting_date, starting_date, starting_invoice_number))
    invoices_before_row = cursor.fetchone()
    total_invoices_before = invoices_before_row[0] if invoices_before_row and invoices_before_row[0] is not None else 0.0

    # Sum of payment amounts before the starting point
    cursor.execute('''
        SELECT SUM(amount) FROM payments
        WHERE party_name = ? AND date <= ? -- Payments on the same day as the starting invoice are included if they occurred before it chronologically (by ID)
    ''', (party_name, starting_date)) # Note: This date comparison might need refinement if payments and invoices on the same day need strict ordering.
    payments_before_row = cursor.fetchone()
    total_payments_before = payments_before_row[0] if payments_before_row and payments_before_row[0] is not None else 0.0

    # The balance before the starting point is initial balance + invoices before - payments before
    current_previous_balance = initial_balance + total_invoices_before - total_payments_before


    for invoice in subsequent_invoices:
        # The new previous_balance for this invoice is the calculated balance before it
        new_previous_balance = current_previous_balance
        new_grand_total = new_previous_balance + invoice['total_amount']

        cursor.execute('''
            UPDATE invoices SET previous_balance = ?, grand_total = ? WHERE id = ?
        ''', (new_previous_balance, new_grand_total, invoice['id']))

        # The grand_total of this invoice becomes the previous_balance for the *next* invoice
        current_previous_balance = new_grand_total


# --- API Endpoints ---

@app.route('/api/status', methods=['GET'])
def get_status():
    db_exists = os.path.exists(DATABASE_FILE)
    return jsonify({
        "status": "Backend is running",
        "database_file": f"{DATABASE_FILE} {'exists' if db_exists else 'does not exist (will be created upon first operation)'}"
    }), 200

@app.route('/api/ledger/<party_name>', methods=['GET'])
def get_party_ledger_api(party_name):
    """
    Provides data for the detailed ledger view.
    Opening balance is the initial_opening_balance from the parties table.
    Transactions include invoice items and payments.
    Current balance is initial_opening_balance + grand_total of last invoice - total payments.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        party_name_param = unquote(party_name)

        # Fetch the initial opening balance for the party
        cursor.execute("SELECT id, initial_opening_balance FROM parties WHERE name = ?", (party_name_param,))
        party_row = cursor.fetchone()

        if party_row is None:
            conn.close()
            return jsonify({"error": "Party not found"}), 404

        party_id = party_row['id']
        initial_opening_balance = party_row['initial_opening_balance'] if party_row['initial_opening_balance'] is not None else 0.0

        # Fetch all invoices for the party, ordered chronologically
        cursor.execute(
            '''SELECT id, invoice_number, date, total_amount, previous_balance, grand_total
               FROM invoices WHERE party_name = ? ORDER BY date ASC, CAST(invoice_number AS INTEGER) ASC''', (party_name_param,))
        invoices = cursor.fetchall()

        # Fetch all payments for the party, ordered chronologically
        cursor.execute(
            "SELECT id as paymentId, amount, date, remarks FROM payments WHERE party_name = ? ORDER BY date ASC, paymentId ASC", (party_name_param,))
        payments = cursor.fetchall()

        # Combine invoice items and payments into a single timeline
        timeline = []
        for inv in invoices:
            cursor.execute(
                "SELECT product_name, qty, packing, unit_price, amount FROM invoice_items WHERE invoice_id = ? ORDER BY id",
                (inv['id'],))
            items = cursor.fetchall()

            # Add each invoice item as a separate transaction entry for the detailed ledger
            for item in items:
                 timeline.append({
                    'type': 'invoice_item',
                    'date': inv['date'],
                    'invoiceNumber': inv['invoice_number'],
                    'productName': item['product_name'],
                    'qty': item['qty'],
                    'packing': item['packing'],
                    'unitPrice': item['unit_price'],
                    'amount': item['amount'] # This is the debit amount for the item
                })

        for pay in payments:
            # Add each payment as a separate transaction entry
            timeline.append({
                'type': 'payment',
                'date': pay['date'],
                'remarks': pay['remarks'],
                'amount': pay['amount'] # This is the credit amount for the payment
            })

        # Sort the combined timeline of invoice items and payments by date and then by type/id for consistency
        try:
            timeline.sort(key=lambda x: (
                datetime.strptime(x.get('date', '1970-01-01'), '%Y-%m-%d'),
                0 if x['type'] == 'invoice_item' else 1, # Invoice items before payments on the same day
                int(x.get('invoiceNumber', '0')) if x['type'] == 'invoice_item' else x.get('paymentId', 0) # Then by invoice/payment ID
            ))
        except ValueError:
            # Handle cases with bad date formats gracefully, though DB constraints should prevent this
            pass

        # Calculate the current cumulative balance using the dedicated helper function
        current_cumulative_balance = calculate_current_party_balance(party_name_param, conn)


        conn.close()

        # The frontend now receives a clean, sorted timeline of events to display.
        return jsonify({
            "partyName": party_name_param,
            "openingBalance": initial_opening_balance, # Use the initial_opening_balance from the parties table
            "currentBalance": current_cumulative_balance, # initial_opening_balance + grand_total of last invoice - total payments
            "transactions": timeline,  # This is the key change for the ledger display
        }), 200

    except Exception as e:
        print(f"Error fetching ledger for {party_name_param}: {e}")
        traceback.print_exc() # Print traceback for debugging
        return jsonify({"error": f"Error fetching ledger: {str(e)}"}), 500


@app.route('/api/parties', methods=['GET'])
def get_parties_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    # We now need to calculate the current balance for each party for this list
    cursor.execute("SELECT name FROM parties ORDER BY name")
    parties_names = cursor.fetchall()

    parties_with_balance = []
    for party_row in parties_names:
        party_name = party_row['name']

        # Calculate the current balance using the dedicated helper function
        current_balance = calculate_current_party_balance(party_name, conn)

        parties_with_balance.append({
            "name": party_name,
            "balance": current_balance
        })

    conn.close()
    return jsonify(parties_with_balance), 200


@app.route('/api/party-balance', methods=['GET'])
def get_party_balance_for_invoice():
    """
    Fetches the previous_balance for a *new* invoice for a party.
    This is the party's current balance before the new invoice is added.
    Also returns the initial_opening_balance separately.
    """
    party_name = request.args.get('partyName')
    if not party_name:
        return jsonify({"error": "Party name is required"}), 400
    conn = get_db_connection()

    cursor = conn.cursor()
    cursor.execute("SELECT initial_opening_balance FROM parties WHERE name = ?", (party_name,))
    party_row = cursor.fetchone()
    initial_balance = party_row['initial_opening_balance'] if party_row and party_row['initial_opening_balance'] is not None else 0.0

    # The previous balance for the new invoice is the party's current balance before this invoice
    previous_balance_for_new_invoice = calculate_current_party_balance(party_name, conn)

    conn.close()
    return jsonify({"balance": previous_balance_for_new_invoice, "initialOpeningBalance": initial_balance}), 200


@app.route('/api/next-invoice-number', methods=['GET'])
def get_next_invoice_number_api():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(CAST(invoice_number AS INTEGER)) FROM invoices WHERE invoice_number GLOB '[0-9]*'")
    max_invoice_num_row = cursor.fetchone()
    conn.close()
    next_num_val = INITIAL_INVOICE_NUMBER
    if max_invoice_num_row and max_invoice_num_row[0] is not None:
        next_num_val = int(max_invoice_num_row[0]) + 1
    next_num_val = max(INITIAL_INVOICE_NUMBER, next_num_val)
    return jsonify({"nextInvoiceNumber": str(next_num_val)}), 200


# --- CREATE INVOICE API ---
@app.route('/api/invoices', methods=['POST'])
def create_invoice_api():
    data = request.get_json()
    party_name = data.get('partyName')
    invoice_date = data.get('date')
    invoice_number = data.get('invoiceNumber')
    items = data.get('items', [])

    # Basic validation
    if not all([party_name, invoice_date, invoice_number]):
        return jsonify({"error": "Missing required invoice data (partyName, date, invoiceNumber)."}), 400
    if not items:
        return jsonify({"error": "Invoice must have at least one item."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure party exists or create it
        cursor.execute("SELECT id FROM parties WHERE name = ?", (party_name,))
        party_row = cursor.fetchone()
        if not party_row:
            cursor.execute("INSERT INTO parties (name, initial_opening_balance) VALUES (?, 0.0)", (party_name,))

        # 1. Recalculate total_amount on the server from the items list for accuracy.
        total_amount = round(sum(float(item.get('amount', 0)) for item in items), 2)

        # 2. Get the party's current balance *before* this new invoice. This is the previous_balance for this invoice.
        previous_balance = calculate_current_party_balance(party_name, conn)

        # 3. Calculate the grand_total for this new invoice.
        grand_total = previous_balance + total_amount

        # Insert the new invoice
        cursor.execute('''
            INSERT INTO invoices (invoice_number, party_name, date, total_amount, previous_balance, grand_total)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (invoice_number, party_name, invoice_date, total_amount, previous_balance, grand_total))
        invoice_id = cursor.lastrowid

        # Insert the associated invoice items
        for item in items:
            cursor.execute('''
                INSERT INTO invoice_items (invoice_id, product_name, qty, packing, unit_price, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (invoice_id, item.get('productName'), float(item.get('qty', 0)), item.get('packing'),
                  float(item.get('unitPrice', 0)), float(item.get('amount', 0))))

        conn.commit()

        # Get the next invoice number for the frontend
        cursor.execute("SELECT MAX(CAST(invoice_number AS INTEGER)) FROM invoices WHERE invoice_number GLOB '[0-9]*'")
        max_num_row = cursor.fetchone()
        next_inv_num = INITIAL_INVOICE_NUMBER
        if max_num_row and max_num_row[0] is not None:
            next_inv_num = int(max_num_row[0]) + 1
        next_inv_num = max(INITIAL_INVOICE_NUMBER, next_inv_num)

        # The previous balance for the *next* invoice is the grand_total of the just-created invoice
        new_previous_balance_for_next_invoice = grand_total

        return jsonify({
            "message": "Invoice created successfully!",
            "invoiceNumber": invoice_number,
            "nextInvoiceNumber": str(next_inv_num),
            "previousBalanceForNextInvoice": new_previous_balance_for_next_invoice # Return the grand_total of this invoice
        }), 201
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE constraint failed: invoices.invoice_number" in str(e):
            return jsonify({"error": f"Invoice number '{invoice_number}' already exists."}), 409
        return jsonify({"error": f"Database integrity error: {str(e)}"}), 409
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Error creating invoice: {str(e)}"}), 500
    finally:
        conn.close()


# --- UPDATE INVOICE API ---
@app.route('/api/invoices/<string:invoice_number_to_update>', methods=['PUT'])
def update_invoice_api(invoice_number_to_update):
    data = request.get_json()
    party_name = data.get('partyName')
    date = data.get('date')
    items = data.get('items', [])

    if not all([party_name, date]):
        return jsonify({"error": "Missing required invoice data for update (partyName, date)."}), 400
    if not items:
        return jsonify({"error": "Invoice must have at least one item."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Find the original invoice details
        cursor.execute("SELECT id, party_name, date, invoice_number, total_amount FROM invoices WHERE invoice_number = ?",
                       (invoice_number_to_update,))
        original_invoice = cursor.fetchone()
        if not original_invoice:
            conn.close()
            return jsonify({"error": "Invoice to update not found"}), 404

        original_invoice_id = original_invoice['id']
        original_party_name = original_invoice['party_name']
        original_date = original_invoice['date']
        original_invoice_number = original_invoice['invoice_number']
        original_total_amount = original_invoice['total_amount']

        # Ensure new party exists if changed
        if original_party_name != party_name:
             cursor.execute("SELECT id FROM parties WHERE name = ?", (party_name,))
             party_exists = cursor.fetchone()
             if not party_exists:
                 cursor.execute("INSERT INTO parties (name, initial_opening_balance) VALUES (?, 0.0)", (party_name,))


        # 1. Recalculate the new total_amount from the updated items list
        new_total_amount = round(sum(float(item.get('amount', 0)) for item in items), 2)

        # 2. Get the party's balance *before* this invoice (based on transactions before its original date/number).
        #    This value should not change based on the update itself, only the grand_total changes.
        #    We need to fetch the previous_balance that was stored with this invoice.
        cursor.execute("SELECT previous_balance FROM invoices WHERE id = ?", (original_invoice_id,))
        previous_balance_for_this_invoice = cursor.fetchone()['previous_balance']


        # 3. Calculate the new grand_total for this invoice record.
        new_grand_total = previous_balance_for_this_invoice + new_total_amount

        # Update invoice details in the invoices table
        cursor.execute('''
            UPDATE invoices SET party_name = ?, date = ?, total_amount = ?, grand_total = ?
            WHERE id = ? ''',
                       (party_name, date, new_total_amount, new_grand_total,
                        original_invoice_id))

        # Delete old items and insert new ones
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (original_invoice_id,))
        for item in items:
            cursor.execute(
                '''INSERT INTO invoice_items (invoice_id, product_name, qty, packing, unit_price, amount) VALUES (?, ?, ?, ?, ?, ?)''',
                (original_invoice_id, item.get('productName'), float(item.get('qty', 0)), item.get('packing'),
                 float(item.get('unitPrice', 0)), float(item.get('amount', 0))))

        # --- IMPORTANT: Recalculate balances for subsequent invoices if total_amount changed or party changed ---
        if new_total_amount != original_total_amount or original_party_name != party_name:
            # If party changed, we need to recalculate balances for subsequent invoices of *both* parties
            if original_party_name != party_name:
                 # Recalculate for the original party starting from the invoice *after* the deleted one
                 # (or the first invoice if the deleted one was the first)
                 update_subsequent_invoice_balances(original_party_name, original_date, original_invoice_number, conn)

            # Recalculate for the current party starting from this updated invoice
            update_subsequent_invoice_balances(party_name, date, invoice_number_to_update, conn)


        conn.commit()

        # After updating, get the grand_total of this invoice to return as the new previous balance for the *next* invoice
        cursor.execute("SELECT grand_total FROM invoices WHERE id = ?", (original_invoice_id,))
        updated_grand_total = cursor.fetchone()['grand_total']


        return jsonify({"message": f"Invoice {invoice_number_to_update} updated successfully",
                        "previousBalanceForNextInvoice": updated_grand_total, # Return the grand_total of this updated invoice
                        "partyName": party_name # Return party name in case it changed
                        }), 200
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Error updating invoice: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/api/invoices/<string:invoice_number>', methods=['GET'])
def get_single_invoice_api(invoice_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
    invoice = cursor.fetchone()

    if not invoice:
        conn.close()
        return jsonify({"error": "Invoice not found"}), 404

    # Fetch items associated with this invoice
    invoice_id = invoice['id']
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id", (invoice_id,))
    items = cursor.fetchall()
    conn.close()

    # Structure the response to match frontend expectations
    invoice_dict = dict(invoice)
    invoice_dict['items'] = [dict(item) for item in items]
    invoice_dict['invoiceNumber'] = invoice_dict.pop('invoice_number')
    invoice_dict['partyName'] = invoice_dict.pop('party_name')
    invoice_dict['totalAmount'] = invoice_dict.pop('total_amount')
    invoice_dict['previousBalance'] = invoice_dict.pop('previous_balance')
    invoice_dict['grandTotal'] = invoice_dict.pop('grand_total')

    # Convert snake_case from DB to camelCase for frontend
    for item in invoice_dict['items']:
        item['productName'] = item.pop('product_name')
        item['unitPrice'] = item.pop('unit_price')

    return jsonify(invoice_dict), 200


@app.route('/api/invoices', methods=['GET'])
def get_all_invoices_api():
    """Fetches all invoices, with optional filtering by date range."""
    conn = get_db_connection()
    cursor = conn.cursor()

    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    base_query = '''
        SELECT id, invoice_number, party_name, date, total_amount, previous_balance, grand_total
        FROM invoices
    '''
    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY date DESC, CAST(invoice_number AS INTEGER) DESC"

    cursor.execute(base_query, params)
    invoices_master_rows = cursor.fetchall()

    result_invoices = []
    for inv_master_row in invoices_master_rows:
        invoice_entry = {
            "invoiceNumber": inv_master_row['invoice_number'],
            "partyName": inv_master_row['party_name'],
            "date": inv_master_row['date'],
            "totalAmount": inv_master_row['total_amount'],
            "previousBalance": inv_master_row['previous_balance'],
            "grandTotal": inv_master_row['grand_total'],
            "items": []
        }
        cursor.execute(
            "SELECT product_name, qty, packing, unit_price, amount FROM invoice_items WHERE invoice_id = ? ORDER BY id",
            (inv_master_row['id'],))
        items_db = cursor.fetchall()
        for item_db_row in items_db:
            invoice_entry['items'].append({
                "productName": item_db_row['product_name'],
                "qty": item_db_row['qty'],
                "packing": item_db_row['packing'],
                "unitPrice": item_db_row['unit_price'],
                "amount": item_db_row['amount']
            })
        result_invoices.append(invoice_entry)

    conn.close()
    return jsonify(result_invoices), 200


@app.route('/api/payments', methods=['POST'])
def record_payment_api():
    data = request.get_json()
    party_name = data.get('partyName')
    amount = data.get('amount')
    date = data.get('date')
    remarks = data.get('remarks', None)

    if not party_name or not date or amount is None:
        return jsonify({"error": "Missing required payment data (partyName, amount, date)."}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Invalid amount format."}), 400

    if amount <= 0:
        return jsonify({"error": "Payment amount must be positive."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure party exists or create it
        cursor.execute("SELECT id FROM parties WHERE name = ?", (party_name,))
        party_exists = cursor.fetchone()
        if not party_exists:
            cursor.execute("INSERT INTO parties (name, initial_opening_balance) VALUES (?, 0.0)", (party_name,))

        cursor.execute("INSERT INTO payments (party_name, amount, date, remarks) VALUES (?, ?, ?, ?)",
                       (party_name, amount, date, remarks))
        payment_id = cursor.lastrowid

        conn.commit()

        # After recording payment, we need to recalculate the party's current balance
        current_party_balance = calculate_current_party_balance(party_name, conn)


        return jsonify({"message": "Payment recorded successfully!", "paymentId": payment_id,
                        "currentPartyBalance": current_party_balance}), 201
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Error recording payment: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/api/payments', methods=['GET'])
def get_all_payments_api():
    """Fetches payments with optional filtering by party name and/or date range."""
    conn = get_db_connection()
    cursor = conn.cursor()

    party_name = request.args.get('partyName')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    base_query = "SELECT id as paymentId, party_name as partyName, amount, date, remarks FROM payments"
    where_clauses = []
    params = []

    if party_name:
        where_clauses.append("partyName = ?")
        params.append(party_name)
    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY date DESC, paymentId DESC"

    cursor.execute(base_query, params)
    payments = cursor.fetchall()
    conn.close()
    return jsonify([dict(p) for p in payments]), 200


@app.route('/api/payments/<int:payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    """Deletes a specific payment by its ID and updates the corresponding party balance."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT party_name, amount FROM payments WHERE id = ?", (payment_id,))
        payment_to_delete = cursor.fetchone()

        if not payment_to_delete:
            conn.close()
            return jsonify({'message': 'Payment to delete not found'}), 404

        party_name = payment_to_delete['party_name']
        amount = payment_to_delete['amount']

        cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

        conn.commit()

        # After deleting payment, recalculate the party's current balance
        current_party_balance = calculate_current_party_balance(party_name, conn)


        return jsonify({'message': f'Payment ID {payment_id} deleted successfully.',
                        'partyName': party_name, # Return party name for frontend refresh
                        'currentPartyBalance': current_party_balance # Return updated balance
                        })
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"An error occurred during payment deletion: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/api/stock', methods=['GET'])
def get_stock_api():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, product_name, batch_no, date, quantity FROM stock ORDER BY product_name, date DESC")
    stock_rows = cursor.fetchall()
    conn.close()

    stock_items_camel_case = []
    for item in stock_rows:
        stock_items_camel_case.append({
            "id": item['id'],
            "productName": item['product_name'],
            "batchNo": item['batch_no'],
            "date": item['date'],
            "quantity": item['quantity']
        })
    return jsonify(stock_items_camel_case), 200


@app.route('/api/stock/batch-add', methods=['POST'])
def add_stock_batch_api():
    data = request.get_json()
    items_to_add = data.get('items', [])
    if not items_to_add:
        return jsonify({"error": "No items provided to add to stock."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        processed_count = 0
        for item in items_to_add:
            product_name = item.get('productName')
            batch_no = item.get('batchNo')
            date = item.get('date')
            quantity = float(item.get('quantity', 0))
            if not all([product_name, date]) or quantity <= 0:
                continue
            cursor.execute('''INSERT INTO stock (product_name, batch_no, date, quantity) VALUES (?, ?, ?, ?)''',
                           (product_name, batch_no, date, quantity))
            processed_count += 1
        conn.commit()
        return jsonify({"message": f"{processed_count} stock item(s) processed successfully."}), 201
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Database error during batch stock addition: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/api/stock/deduct', methods=['POST'])
def deduct_stock_api():
    data = request.get_json()
    items_to_deduct = data.get('items', [])
    if not items_to_deduct:
        return jsonify({"error": "No items provided for stock deduction."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        errors = []
        for item in items_to_deduct:
            product_name = item.get('productName')
            qty_to_deduct = float(item.get('qty', 0))
            if not product_name or qty_to_deduct <= 0:
                continue

            cursor.execute("SELECT SUM(quantity) as total FROM stock WHERE product_name = ?", (product_name,))
            total_available_row = cursor.fetchone()
            total_available = total_available_row['total'] if total_available_row and total_available_row[
                'total'] else 0

            if total_available < qty_to_deduct:
                errors.append(
                    f"Not enough stock for '{product_name}'. Available: {total_available}, Required: {qty_to_deduct}")
                continue

            # FIFO logic: Deduct from oldest batches first
            cursor.execute(
                "SELECT id, quantity FROM stock WHERE product_name = ? AND quantity > 0 ORDER BY date ASC, id ASC",
                (product_name,))
            available_batches = cursor.fetchall()

            remaining_to_deduct = qty_to_deduct
            for batch in available_batches:
                if remaining_to_deduct <= 0:
                    break
                deduct_from_this_batch = min(batch['quantity'], remaining_to_deduct)
                new_quantity = batch['quantity'] - deduct_from_this_batch
                cursor.execute("UPDATE stock SET quantity = ? WHERE id = ?", (new_quantity, batch['id']))
                remaining_to_deduct -= deduct_from_this_batch

        if errors:
            conn.rollback()
            return jsonify({"error": ". ".join(errors)}), 400

        conn.commit()
        return jsonify({"message": "Stock deducted successfully."}), 200
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"An error occurred during stock deduction: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/api/all-party-ledgers', methods=['GET'])
def get_all_party_ledgers_api():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM parties ORDER BY name")
    all_parties_names = cursor.fetchall()

    all_ledgers_data = []
    for party_row in all_parties_names:
        party_name = party_row['name']

        # Calculate current balance for each party using the helper
        current_balance = calculate_current_party_balance(party_name, conn)

        all_ledgers_data.append({
            "partyName": party_name,
            "currentBalance": current_balance
        })

    conn.close()
    return jsonify(all_ledgers_data), 200


@app.route('/api/admin/delete-all-data', methods=['POST'])
def delete_all_data_api():
    print("Received request to DELETE ALL backend data.")
    try:
        # Re-initializing the DB clears all data
        init_db(clear_existing_data=True)
        return jsonify(
            {"message": "All backend data has been successfully deleted and the database re-initialized."}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify(
            {"error": f"A critical error occurred on the server while attempting to delete data: {str(e)}"}), 500


@app.route('/api/invoices/<string:invoice_number_to_delete>', methods=['DELETE'])
def delete_invoice(invoice_number_to_delete):
    """Deletes a specific invoice by its number and recalculates subsequent balances."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get invoice details before deleting
        cursor.execute("SELECT id, party_name, date, invoice_number FROM invoices WHERE invoice_number = ?", (invoice_number_to_delete,))
        invoice_to_delete = cursor.fetchone()

        if not invoice_to_delete:
            conn.close()
            return jsonify({'message': f'Invoice {invoice_number_to_delete} not found'}), 404

        invoice_id = invoice_to_delete['id']
        party_name = invoice_to_delete['party_name']
        invoice_date = invoice_to_delete['date']
        invoice_number = invoice_to_delete['invoice_number']

        # Delete invoice items associated with this invoice
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))

        # Delete the invoice itself
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))

        # --- IMPORTANT: Recalculate balances for subsequent invoices ---
        update_subsequent_invoice_balances(party_name, invoice_date, invoice_number, conn)

        conn.commit()

        # After deleting, recalculate the party's current balance
        current_party_balance = calculate_current_party_balance(party_name, conn)


        return jsonify({'message': f'Invoice {invoice_number_to_delete} and related items deleted successfully.',
                        'partyName': party_name, # Return party name for frontend refresh
                        'currentPartyBalance': current_party_balance # Return updated balance
                        }), 200

    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"An error occurred during invoice deletion: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/parties/<string:party_name>/set-prev-balance', methods=['POST'])
def set_prev_balance(party_name):
    data = request.get_json()
    new_initial_balance = data.get('prevBalance') # Renamed to new_initial_balance for clarity
    reason = data.get('reason', 'No reason provided') # Get the reason from the frontend

    if not party_name or new_initial_balance is None:
        return jsonify({"error": "Missing required data (partyName, prevBalance)."}), 400
    try:
        new_initial_balance = float(new_initial_balance)
    except ValueError:
        return jsonify({"error": "Invalid previous balance format."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, initial_opening_balance FROM parties WHERE name = ?", (party_name,))
        party_row = cursor.fetchone()

        old_initial_balance = 0.0
        party_id = None

        if not party_row:
            # If party doesn't exist, create it with the new initial opening balance
            cursor.execute("INSERT INTO parties (name, initial_opening_balance) VALUES (?, ?)", (party_name, new_initial_balance))
            party_id = cursor.lastrowid
            # old_initial_balance remains 0.0 as it's a new party
        else:
            # If party exists, get the current initial opening balance (old_initial_balance)
            party_id = party_row['id']
            old_initial_balance = party_row['initial_opening_balance'] if party_row['initial_opening_balance'] is not None else 0.0

            # Update the initial opening balance
            cursor.execute("UPDATE parties SET initial_opening_balance = ? WHERE id = ?", (new_initial_balance, party_id))

        # Record the adjustment in the new table
        cursor.execute('''
            INSERT INTO opening_balance_adjustments (party_id, adjustment_date, old_balance, new_balance, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (party_id, datetime.now().strftime('%Y-%m-%d'), old_initial_balance, new_initial_balance, reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        conn.commit()

        # After setting the opening balance, recalculate the party's current balance
        current_party_balance = calculate_current_party_balance(party_name, conn)


        return jsonify({"message": f"Opening balance for '{party_name}' set to {new_initial_balance:.2f} successfully.",
                        "currentPartyBalance": current_party_balance # Return updated balance
                        }), 200 if party_row else 201 # Return 200 for update, 201 for create
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/api/parties/<string:party_name>/opening-balance-history', methods=['GET'])
def get_opening_balance_history(party_name):
    """Fetches the history of opening balance adjustments for a party."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        party_name_param = unquote(party_name)

        # Get the party ID
        cursor.execute("SELECT id FROM parties WHERE name = ?", (party_name_param,))
        party_row = cursor.fetchone()

        if party_row is None:
            conn.close()
            return jsonify({"error": "Party not found"}), 404

        party_id = party_row['id']

        # Fetch adjustment records for this party, ordered by date and creation time
        cursor.execute('''
            SELECT adjustment_date, old_balance, new_balance, reason, created_at
            FROM opening_balance_adjustments
            WHERE party_id = ?
            ORDER BY adjustment_date ASC, created_at ASC
        ''', (party_id,))
        history_records = cursor.fetchall()

        conn.close()

        # Format the records for the frontend
        formatted_history = []
        for record in history_records:
            formatted_history.append({
                "adjustment_date": record['adjustment_date'],
                "old_balance": record['old_balance'],
                "new_balance": record['new_balance'],
                "reason": record['reason'],
                "created_at": record['created_at']
            })

        return jsonify(formatted_history), 200

    except Exception as e:
        print(f"Error fetching opening balance history for {party_name_param}: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error fetching opening balance history: {str(e)}"}), 500
if __name__ == '__main__':
    if not os.path.exists(DATABASE_FILE):
        print(f"Database file '{DATABASE_FILE}' not found. Initializing database.")
        init_db()
    else:
        # Check tables exist on every startup, but don't clear data unless specified
        print(f"Database file '{DATABASE_FILE}' found. Checking schema.")
        init_db(clear_existing_data=False)
    print(f"Starting Flask server on http://127.0.0.1:5000")
    print("Ensure your HTML frontend makes API calls to this address.")
    app.run(debug=True, port=5000)

