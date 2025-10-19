from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
import sqlite3
import traceback

app = Flask(__name__)
CORS(app)

# Get the absolute path for the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'invoices.db')

print(f"Database will be created at: {DB_PATH}")


# Database setup
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check if invoices table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        table_exists = c.fetchone()

        if not table_exists:
            # Table doesn't exist, create it
            c.execute('''
                CREATE TABLE invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT NOT NULL,
                    fbr_invoice_number TEXT,
                    date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    party_name TEXT NOT NULL,
                    items TEXT NOT NULL,
                    subtotal REAL NOT NULL,
                    gst_total REAL,
                    grand_total REAL NOT NULL,
                    invoice_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            print("Database table created successfully")
        else:
            # Check if created_at column exists
            c.execute("PRAGMA table_info(invoices)")
            columns = [column[1] for column in c.fetchall()]
            if 'created_at' not in columns:
                c.execute('ALTER TABLE invoices ADD COLUMN created_at TEXT')
                print("Added created_at column to existing table")

        conn.commit()
        print("Database initialized successfully")

    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        print(traceback.format_exc())
    finally:
        if conn:
            conn.close()


init_db()


@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'FBR.html')


@app.route('/save_invoice', methods=['POST'])
def save_invoice():
    conn = None
    try:
        data = request.json
        print("Received invoice data:", data)

        # Validate required fields
        required_fields = ['invoice_number', 'date', 'due_date', 'party_name', 'items', 'subtotal', 'grand_total',
                           'invoice_type']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        if not data['items'] or len(data['items']) == 0:
            return jsonify({'success': False, 'error': 'At least one item is required'}), 400

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check if invoice already exists (for update)
        if 'id' in data and data['id']:
            c.execute('''
                UPDATE invoices 
                SET invoice_number=?, fbr_invoice_number=?, date=?, due_date=?, party_name=?, 
                    items=?, subtotal=?, gst_total=?, grand_total=?, invoice_type=?
                WHERE id=?
            ''', (
                data['invoice_number'],
                data.get('fbr_invoice_number', ''),
                data['date'],
                data['due_date'],
                data['party_name'],
                json.dumps(data['items']),
                data['subtotal'],
                data.get('gst_total', 0),
                data['grand_total'],
                data['invoice_type'],
                data['id']
            ))
            invoice_id = data['id']
            print(f"Updated existing invoice with ID: {invoice_id}")
        else:
            # Insert new invoice
            c.execute('''
                INSERT INTO invoices 
                (invoice_number, fbr_invoice_number, date, due_date, party_name, items, subtotal, gst_total, grand_total, invoice_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['invoice_number'],
                data.get('fbr_invoice_number', ''),
                data['date'],
                data['due_date'],
                data['party_name'],
                json.dumps(data['items']),
                data['subtotal'],
                data.get('gst_total', 0),
                data['grand_total'],
                data['invoice_type'],
                datetime.now().isoformat()
            ))
            invoice_id = c.lastrowid
            print(f"Created new invoice with ID: {invoice_id}")

        conn.commit()

        # Verify the invoice was saved
        c.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        saved_invoice = c.fetchone()
        if saved_invoice:
            print(f"Successfully verified invoice save - ID: {invoice_id}")
        else:
            print("Warning: Invoice save verification failed")

        return jsonify({'success': True, 'invoice_id': invoice_id})

    except Exception as e:
        print("Error saving invoice:", str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/get_invoices_by_date', methods=['POST'])
def get_invoices_by_date():
    conn = None
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        invoice_type = data.get('invoice_type')  # 'tax' or 'non-tax'

        if not start_date or not end_date:
            return jsonify({'success': False, 'error': 'Start date and end date are required'}), 400

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        query = '''
            SELECT * FROM invoices 
            WHERE date BETWEEN ? AND ?
        '''
        params = [start_date, end_date]

        if invoice_type:
            query += ' AND invoice_type = ?'
            params.append(invoice_type)

        print(f"Executing query: {query} with params: {params}")
        c.execute(query, params)
        invoices = c.fetchall()

        print(f"Found {len(invoices)} invoices")

        # Convert to list of dictionaries
        result = []
        for invoice in invoices:
            result.append({
                'id': invoice[0],
                'invoice_number': invoice[1],
                'fbr_invoice_number': invoice[2],
                'date': invoice[3],
                'due_date': invoice[4],
                'party_name': invoice[5],
                'items': json.loads(invoice[6]),
                'subtotal': invoice[7],
                'gst_total': invoice[8],
                'grand_total': invoice[9],
                'invoice_type': invoice[10],
                'created_at': invoice[11] if len(invoice) > 11 else datetime.now().isoformat()
            })

        return jsonify({'success': True, 'invoices': result})

    except Exception as e:
        print("Error in get_invoices_by_date:", str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/search_invoice', methods=['POST'])
def search_invoice():
    conn = None
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()

        if not search_term:
            return jsonify({'success': False, 'error': 'Search term is required'}), 400

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Search by invoice number, party name, or FBR invoice number
        search_pattern = f'%{search_term}%'
        c.execute('''
            SELECT * FROM invoices 
            WHERE invoice_number LIKE ? OR party_name LIKE ? OR fbr_invoice_number LIKE ?
            ORDER BY date DESC
        ''', (search_pattern, search_pattern, search_pattern))

        invoices = c.fetchall()
        print(f"Search found {len(invoices)} invoices for term: '{search_term}'")

        # Convert to list of dictionaries
        result = []
        for invoice in invoices:
            result.append({
                'id': invoice[0],
                'invoice_number': invoice[1],
                'fbr_invoice_number': invoice[2],
                'date': invoice[3],
                'due_date': invoice[4],
                'party_name': invoice[5],
                'items': json.loads(invoice[6]),
                'subtotal': invoice[7],
                'gst_total': invoice[8],
                'grand_total': invoice[9],
                'invoice_type': invoice[10],
                'created_at': invoice[11] if len(invoice) > 11 else datetime.now().isoformat()
            })

        return jsonify({'success': True, 'invoices': result})

    except Exception as e:
        print("Error in search_invoice:", str(e))
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/get_invoice/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
        invoice = c.fetchone()

        if invoice:
            result = {
                'id': invoice[0],
                'invoice_number': invoice[1],
                'fbr_invoice_number': invoice[2],
                'date': invoice[3],
                'due_date': invoice[4],
                'party_name': invoice[5],
                'items': json.loads(invoice[6]),
                'subtotal': invoice[7],
                'gst_total': invoice[8],
                'grand_total': invoice[9],
                'invoice_type': invoice[10],
                'created_at': invoice[11] if len(invoice) > 11 else datetime.now().isoformat()
            }
            return jsonify({'success': True, 'invoice': result})
        else:
            return jsonify({'success': False, 'error': 'Invoice not found'}), 404

    except Exception as e:
        print("Error in get_invoice:", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/delete_invoice/<int:invoice_id>', methods=['DELETE'])
def delete_invoice(invoice_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
        conn.commit()

        if c.rowcount > 0:
            return jsonify({'success': True, 'message': 'Invoice deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Invoice not found'}), 404

    except Exception as e:
        print("Error in delete_invoice:", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/check_database', methods=['GET'])
def check_database():
    """Endpoint to check database status"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        table_exists = c.fetchone()

        # Count records
        c.execute("SELECT COUNT(*) FROM invoices")
        count = c.fetchone()[0]

        # Get database info
        c.execute("PRAGMA table_info(invoices)")
        columns = c.fetchall()

        conn.close()

        return jsonify({
            'success': True,
            'database_path': DB_PATH,
            'table_exists': bool(table_exists),
            'total_invoices': count,
            'columns': [col[1] for col in columns]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/reset_database', methods=['POST'])
def reset_database():
    """Endpoint to reset the database - use only for development"""
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("Old database deleted")

        init_db()
        return jsonify({'success': True, 'message': 'Database reset successfully'})
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Flask server...")
    print(f"Database location: {DB_PATH}")
    init_db()
    app.run(debug=True, port=5001)