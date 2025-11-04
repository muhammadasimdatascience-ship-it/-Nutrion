import streamlit as st
import pandas as pd
import json
import datetime
from datetime import datetime, timedelta
import io
import base64
import tempfile
import os
import sqlite3
import uuid
from PIL import Image

# Try to import plotly with fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("Plotly not available. Using alternative visualizations.")

# Try to import fpdf with fallback
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    st.warning("FPDF not available. PDF generation disabled.")

# Set page configuration
st.set_page_config(
    page_title="HMD Solutions - Business Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for attractive styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 1rem;
        border-bottom: 3px solid #667eea;
        padding-bottom: 0.5rem;
    }
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
    }
    .positive {
        color: #10b981;
        font-weight: bold;
        font-size: 1.1em;
    }
    .negative {
        color: #ef4444;
        font-weight: bold;
        font-size: 1.1em;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        margin: 0.5rem;
    }
    .footer {
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        color: white;
        padding: 2rem;
        text-align: center;
        margin-top: 3rem;
        border-radius: 15px;
    }
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2c3e50 0%, #3498db 100%);
    }
    .tab-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    .edit-btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        margin-right: 0.5rem;
        color: white !important;
        border: none !important;
    }
    .delete-btn {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
        color: white !important;
        border: none !important;
    }
    .update-btn {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        margin-right: 0.5rem;
    }
    .quick-action-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 1rem 2rem;
        border-radius: 15px;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        width: 100%;
        margin: 0.5rem 0;
    }
    .quick-action-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    }
    .download-btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        margin: 0.2rem;
    }
    .success-message {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .warning-message {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .info-card {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    .form-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    .data-table {
        background: white;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
    }
    .search-box {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Database setup for persistent storage
def init_database():
    conn = sqlite3.connect('hmd_solutions.db', check_same_thread=False)
    c = conn.cursor()

    # Create employees table with all columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            initial_balance REAL DEFAULT 0,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            department TEXT DEFAULT '',
            position TEXT DEFAULT '',
            join_date TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            employee_id TEXT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT '',
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # Create expenses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT '',
            employee_name TEXT DEFAULT '',
            date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id TEXT PRIMARY KEY,
            company_name TEXT DEFAULT 'HMD Solutions',
            company_address TEXT DEFAULT 'Karachi, Pakistan',
            company_phone TEXT DEFAULT '+92-3207429422',
            company_email TEXT DEFAULT 'info@hmdsolutions.com',
            currency TEXT DEFAULT 'PKR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default settings if not exists
    c.execute('''
        INSERT OR IGNORE INTO settings (id, company_name, company_address, company_phone, company_email, currency)
        VALUES ('default', 'HMD Solutions', 'Karachi, Pakistan', '+92-3207429422', 'info@hmdsolutions.com', 'PKR')
    ''')

    # Check and add missing columns to employees table
    c.execute("PRAGMA table_info(employees)")
    existing_columns = [column[1] for column in c.fetchall()]
    
    # Add missing columns if they don't exist
    missing_columns = {
        'phone': 'TEXT DEFAULT ""',
        'email': 'TEXT DEFAULT ""', 
        'department': 'TEXT DEFAULT ""',
        'position': 'TEXT DEFAULT ""',
        'join_date': 'TEXT DEFAULT ""'
    }
    
    for column_name, column_type in missing_columns.items():
        if column_name not in existing_columns:
            try:
                c.execute(f'ALTER TABLE employees ADD COLUMN {column_name} {column_type}')
                st.success(f"Added missing column: {column_name}")
            except Exception as e:
                st.warning(f"Could not add column {column_name}: {str(e)}")

    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect('hmd_solutions.db', check_same_thread=False)

class SettingsManager:
    def __init__(self):
        init_database()

    def get_settings(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM settings WHERE id = "default"')
        row = c.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'company_name': row[1],
                'company_address': row[2],
                'company_phone': row[3],
                'company_email': row[4],
                'currency': row[5],
                'created_at': row[6]
            }
        return None

    def update_settings(self, company_name, company_address, company_phone, company_email, currency):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE settings 
            SET company_name = ?, company_address = ?, company_phone = ?, company_email = ?, currency = ?
            WHERE id = "default"
        ''', (company_name, company_address, company_phone, company_email, currency))
        conn.commit()
        conn.close()

class EmployeeLedger:
    def __init__(self):
        init_database()
    
    def add_employee(self, name, initial_balance=0, phone="", email="", department="", position="", join_date=None):
        conn = get_db_connection()
        c = conn.cursor()
        employee_id = str(uuid.uuid4())
        
        if join_date is None:
            join_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            c.execute('''
                INSERT INTO employees (id, name, initial_balance, phone, email, department, position, join_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (employee_id, name, initial_balance, phone, email, department, position, join_date))
            
            conn.commit()
            return employee_id
        except Exception as e:
            st.error(f"Error adding employee: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_employees(self, search_query=""):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            if search_query:
                c.execute('''
                    SELECT * FROM employees 
                    WHERE name LIKE ? OR department LIKE ? OR position LIKE ? OR email LIKE ?
                    ORDER BY name
                ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
            else:
                c.execute('SELECT * FROM employees ORDER BY name')
                
            rows = c.fetchall()
            employees = []
            
            for row in rows:
                employee = {
                    'id': row[0], 
                    'name': row[1], 
                    'initial_balance': row[2] if len(row) > 2 else 0,
                    'phone': row[3] if len(row) > 3 else "",
                    'email': row[4] if len(row) > 4 else "",
                    'department': row[5] if len(row) > 5 else "",
                    'position': row[6] if len(row) > 6 else "",
                    'join_date': row[7] if len(row) > 7 else datetime.now().strftime('%Y-%m-%d')
                }
                employees.append(employee)
            
            return employees
        except Exception as e:
            st.error(f"Error fetching employees: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_employee(self, employee_id):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
            row = c.fetchone()
            
            if row:
                return {
                    'id': row[0], 
                    'name': row[1], 
                    'initial_balance': row[2] if len(row) > 2 else 0,
                    'phone': row[3] if len(row) > 3 else "",
                    'email': row[4] if len(row) > 4 else "",
                    'department': row[5] if len(row) > 5 else "",
                    'position': row[6] if len(row) > 6 else "",
                    'join_date': row[7] if len(row) > 7 else datetime.now().strftime('%Y-%m-%d')
                }
            return None
        except Exception as e:
            st.error(f"Error fetching employee: {str(e)}")
            return None
        finally:
            conn.close()
    
    def update_employee(self, employee_id, name, initial_balance, phone, email, department, position, join_date):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('''
                UPDATE employees 
                SET name = ?, initial_balance = ?, phone = ?, email = ?, department = ?, position = ?, join_date = ?
                WHERE id = ?
            ''', (name, initial_balance, phone, email, department, position, join_date, employee_id))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error updating employee: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_employee(self, employee_id):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            # First delete related transactions
            c.execute('DELETE FROM transactions WHERE employee_id = ?', (employee_id,))
            # Then delete employee
            c.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting employee: {str(e)}")
            return False
        finally:
            conn.close()
    
    def add_transaction(self, employee_id, transaction_type, amount, description, category="", date=None):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            transaction_id = str(uuid.uuid4())
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
                
            c.execute('''
                INSERT INTO transactions (id, employee_id, type, amount, description, category, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (transaction_id, employee_id, transaction_type, amount, description, category, date))
            conn.commit()
            return transaction_id
        except Exception as e:
            st.error(f"Error adding transaction: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_employee_transactions(self, employee_id, start_date=None, end_date=None):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            query = 'SELECT * FROM transactions WHERE employee_id = ?'
            params = [employee_id]
            
            if start_date and end_date:
                query += ' AND date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            
            query += ' ORDER BY date DESC'
            
            c.execute(query, params)
            rows = c.fetchall()
            transactions = []
            
            for row in rows:
                transaction = {
                    'id': row[0],
                    'employee_id': row[1],
                    'type': row[2],
                    'amount': row[3],
                    'description': row[4],
                    'category': row[5] if len(row) > 5 else "",
                    'date': row[6] if len(row) > 6 else row[5]
                }
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            st.error(f"Error fetching transactions: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_transaction(self, transaction_id):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,))
            row = c.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'employee_id': row[1],
                    'type': row[2],
                    'amount': row[3],
                    'description': row[4],
                    'category': row[5] if len(row) > 5 else "",
                    'date': row[6] if len(row) > 6 else row[5]
                }
            return None
        except Exception as e:
            st.error(f"Error fetching transaction: {str(e)}")
            return None
        finally:
            conn.close()
    
    def update_transaction(self, transaction_id, employee_id, transaction_type, amount, description, category, date):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('''
                UPDATE transactions 
                SET employee_id = ?, type = ?, amount = ?, description = ?, category = ?, date = ?
                WHERE id = ?
            ''', (employee_id, transaction_type, amount, description, category, date, transaction_id))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error updating transaction: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_transaction(self, transaction_id):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting transaction: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_employee_balance(self, employee_id):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            # Get initial balance
            c.execute('SELECT initial_balance FROM employees WHERE id = ?', (employee_id,))
            result = c.fetchone()
            initial_balance = result[0] if result else 0
            
            # Calculate total expenses and payments
            c.execute('SELECT type, SUM(amount) FROM transactions WHERE employee_id = ? GROUP BY type', (employee_id,))
            transactions = c.fetchall()
            
            total_expenses = 0
            total_payments = 0
            
            for trans_type, amount in transactions:
                if trans_type == 'expense':
                    total_expenses += amount if amount else 0
                elif trans_type == 'payment':
                    total_payments += amount if amount else 0
            
            # Balance = Initial Balance + Expenses - Payments
            return initial_balance + total_expenses - total_payments
        except Exception as e:
            st.error(f"Error calculating balance: {str(e)}")
            return 0
        finally:
            conn.close()
    
    def get_employee_summary(self, employee_id, start_date=None, end_date=None):
        try:
            transactions = self.get_employee_transactions(employee_id, start_date, end_date)
            
            total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
            total_payments = sum(t['amount'] for t in transactions if t['type'] == 'payment')
            
            # Get initial balance for the employee
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT initial_balance FROM employees WHERE id = ?', (employee_id,))
            result = c.fetchone()
            initial_balance = result[0] if result else 0
            conn.close()
            
            balance = initial_balance + total_expenses - total_payments
            
            return {
                'total_expenses': total_expenses,
                'total_payments': total_payments,
                'balance': balance,
                'transaction_count': len(transactions)
            }
        except Exception as e:
            st.error(f"Error getting employee summary: {str(e)}")
            return {
                'total_expenses': 0,
                'total_payments': 0,
                'balance': 0,
                'transaction_count': 0
            }
    
    def get_transactions(self, search_query=""):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            if search_query:
                c.execute('''
                    SELECT t.*, e.name as employee_name 
                    FROM transactions t 
                    LEFT JOIN employees e ON t.employee_id = e.id 
                    WHERE t.description LIKE ? OR e.name LIKE ? OR t.category LIKE ?
                    ORDER BY t.date DESC
                ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
            else:
                c.execute('''
                    SELECT t.*, e.name as employee_name 
                    FROM transactions t 
                    LEFT JOIN employees e ON t.employee_id = e.id 
                    ORDER BY t.date DESC
                ''')
                
            rows = c.fetchall()
            transactions = []
            
            for row in rows:
                if len(row) >= 8:
                    transaction = {
                        'id': row[0],
                        'employee_id': row[1],
                        'type': row[2],
                        'amount': row[3],
                        'description': row[4],
                        'category': row[5],
                        'date': row[6],
                        'employee_name': row[7]
                    }
                else:
                    transaction = {
                        'id': row[0],
                        'employee_id': row[1],
                        'type': row[2],
                        'amount': row[3],
                        'description': row[4],
                        'category': "",
                        'date': row[5] if len(row) > 5 else row[4],
                        'employee_name': "Unknown"
                    }
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            st.error(f"Error fetching transactions: {str(e)}")
            return []
        finally:
            conn.close()

class ExpenseTracker:
    def __init__(self):
        init_database()
    
    def add_expense(self, expense_type, description, amount, category="", employee_name=None, date=None, status="Pending"):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            expense_id = str(uuid.uuid4())
            
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            c.execute('''
                INSERT INTO expenses (id, type, description, amount, category, employee_name, date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (expense_id, expense_type, description, amount, category, employee_name, date, status))
            
            conn.commit()
            return expense_id
        except Exception as e:
            st.error(f"Error adding expense: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_expenses(self, expense_type=None, start_date=None, end_date=None, search_query=""):
        conn = get_db_connection()
        c = conn.cursor()
        
        try:
            query = 'SELECT * FROM expenses'
            params = []
            
            conditions = []
            if expense_type:
                conditions.append('type = ?')
                params.append(expense_type)
            
            if start_date and end_date:
                conditions.append('date BETWEEN ? AND ?')
                params.extend([start_date, end_date])
            
            if search_query:
                conditions.append('(description LIKE ? OR category LIKE ? OR employee_name LIKE ?)')
                params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY date DESC'
            
            c.execute(query, params)
            rows = c.fetchall()
            expenses = []
            
            for row in rows:
                if len(row) >= 8:
                    expense = {
                        'id': row[0],
                        'type': row[1],
                        'description': row[2],
                        'amount': row[3],
                        'category': row[4],
                        'employee_name': row[5],
                        'date': row[6],
                        'status': row[7]
                    }
                else:
                    expense = {
                        'id': row[0],
                        'type': row[1],
                        'description': row[2],
                        'amount': row[3],
                        'category': "",
                        'employee_name': row[4] if len(row) > 4 else "",
                        'date': row[5] if len(row) > 5 else row[4],
                        'status': 'Pending'
                    }
                expenses.append(expense)
            
            return expenses
        except Exception as e:
            st.error(f"Error fetching expenses: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_expense(self, expense_id):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
            row = c.fetchone()
            
            if row:
                if len(row) >= 8:
                    return {
                        'id': row[0],
                        'type': row[1],
                        'description': row[2],
                        'amount': row[3],
                        'category': row[4],
                        'employee_name': row[5],
                        'date': row[6],
                        'status': row[7]
                    }
                else:
                    return {
                        'id': row[0],
                        'type': row[1],
                        'description': row[2],
                        'amount': row[3],
                        'category': "",
                        'employee_name': row[4] if len(row) > 4 else "",
                        'date': row[5] if len(row) > 5 else row[4],
                        'status': 'Pending'
                    }
            return None
        except Exception as e:
            st.error(f"Error fetching expense: {str(e)}")
            return None
        finally:
            conn.close()
    
    def update_expense(self, expense_id, expense_type, description, amount, category, employee_name, date, status):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('''
                UPDATE expenses 
                SET type = ?, description = ?, amount = ?, category = ?, employee_name = ?, date = ?, status = ?
                WHERE id = ?
            ''', (expense_type, description, amount, category, employee_name, date, status, expense_id))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error updating expense: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_expense(self, expense_id):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error deleting expense: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_summary(self, start_date=None, end_date=None):
        try:
            expenses = self.get_expenses(start_date=start_date, end_date=end_date)
            
            company_total = sum(e['amount'] for e in expenses if e['type'] == 'company')
            employee_total = sum(e['amount'] for e in expenses if e['type'] == 'employee')
            grand_total = company_total + employee_total
            
            return {
                'company_total': company_total,
                'employee_total': employee_total,
                'grand_total': grand_total,
                'expense_count': len(expenses)
            }
        except Exception as e:
            st.error(f"Error getting expense summary: {str(e)}")
            return {
                'company_total': 0,
                'employee_total': 0,
                'grand_total': 0,
                'expense_count': 0
            }

class PDFGenerator:
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.get_settings()

    def generate_employee_ledger_pdf(self, employee_name, transactions, summary, start_date=None, end_date=None):
        if not FPDF_AVAILABLE:
            st.error("PDF generation is not available. Please install fpdf.")
            return None
            
        try:
            pdf = FPDF()
            pdf.add_page()

            # Header with company name from settings
            pdf.set_font('Arial', 'B', 20)
            pdf.cell(0, 10, self.settings['company_name'], 0, 1, 'C')
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Employee Ledger Report', 0, 1, 'C')
            pdf.ln(5)

            # Report period
            pdf.set_font('Arial', 'I', 12)
            period_text = f"Period: {start_date} to {end_date}" if start_date and end_date else "All Time Period"
            pdf.cell(0, 10, period_text, 0, 1, 'C')
            pdf.ln(10)

            # Employee information
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, f'Employee: {employee_name}', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f'Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
            pdf.ln(5)

            # Summary
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'Summary:', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Total Expenses: {self.settings["currency"]} {summary["total_expenses"]:.2f}', 0, 1)
            pdf.cell(0, 8, f'Total Payments: {self.settings["currency"]} {summary["total_payments"]:.2f}', 0, 1)

            # Balance with color
            balance_status = '(Due)' if summary['balance'] > 0 else '(Advance)' if summary['balance'] < 0 else ''
            if summary['balance'] > 0:
                pdf.set_text_color(255, 0, 0)  # Red for due
            else:
                pdf.set_text_color(0, 128, 0)  # Green for advance
                
            pdf.cell(0, 8, f'Balance: {self.settings["currency"]} {abs(summary["balance"]):.2f} {balance_status}', 0, 1)
            pdf.set_text_color(0, 0, 0)  # Reset to black
            pdf.ln(10)

            # Transactions table
            if transactions:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, 'Transaction History:', 0, 1)

                # Table header
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(40, 10, 'Date', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Type', 1, 0, 'C', True)
                pdf.cell(70, 10, 'Description', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Amount', 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)
                for t in transactions:
                    # Alternate row colors
                    if transactions.index(t) % 2 == 0:
                        pdf.set_fill_color(240, 240, 240)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    pdf.cell(40, 8, t['date'], 1, 0, 'C', True)
                    pdf.cell(30, 8, t['type'].title(), 1, 0, 'C', True)
                    pdf.cell(70, 8, t['description'][:40], 1, 0, 'C', True)

                    # Color code amounts
                    if t['type'] == 'expense':
                        pdf.set_text_color(255, 0, 0)
                    else:
                        pdf.set_text_color(0, 128, 0)
                    pdf.cell(30, 8, f"{self.settings['currency']} {t['amount']:.2f}", 1, 1, 'C', True)
                    pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(0, 10, 'No transactions found for the selected period.', 0, 1)

            # Footer with company info
            pdf.ln(15)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 10, f'Generated by {self.settings["company_name"]} Business Management System', 0, 1, 'C')
            pdf.cell(0, 5, f'Contact: {self.settings["company_phone"]} | Email: {self.settings["company_email"]}', 0, 1, 'C')

            return pdf
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return None

    def generate_expense_report_pdf(self, expenses, report_type="All", employee_name=None, start_date=None, end_date=None):
        if not FPDF_AVAILABLE:
            st.error("PDF generation is not available. Please install fpdf.")
            return None
            
        try:
            pdf = FPDF()
            pdf.add_page()

            # Header
            pdf.set_font('Arial', 'B', 20)
            pdf.cell(0, 10, self.settings['company_name'], 0, 1, 'C')
            pdf.set_font('Arial', 'B', 16)

            if report_type == "employee" and employee_name:
                pdf.cell(0, 10, f'Expense Report - {employee_name}', 0, 1, 'C')
            else:
                pdf.cell(0, 10, f'{report_type.title()} Expense Report', 0, 1, 'C')

            # Report period
            pdf.set_font('Arial', 'I', 12)
            period_text = f"Period: {start_date} to {end_date}" if start_date and end_date else "All Time Period"
            pdf.cell(0, 10, period_text, 0, 1, 'C')
            pdf.ln(5)

            # Report details
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
            pdf.ln(5)

            # Summary
            total_amount = sum(e['amount'] for e in expenses)
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, f'Total Amount: {self.settings["currency"]} {total_amount:.2f}', 0, 1)
            pdf.ln(5)

            # Expenses table
            if expenses:
                pdf.set_font('Arial', 'B', 12)

                # Table header
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(25, 10, 'Date', 1, 0, 'C', True)
                pdf.cell(25, 10, 'Type', 1, 0, 'C', True)
                pdf.cell(60, 10, 'Description', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Employee', 1, 0, 'C', True)
                pdf.cell(30, 10, 'Amount', 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)
                for idx, e in enumerate(expenses):
                    # Alternate row colors
                    if idx % 2 == 0:
                        pdf.set_fill_color(240, 240, 240)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    pdf.cell(25, 8, e['date'], 1, 0, 'C', True)
                    pdf.cell(25, 8, e['type'].title(), 1, 0, 'C', True)
                    pdf.cell(60, 8, e['description'][:35], 1, 0, 'C', True)
                    pdf.cell(30, 8, e['employee_name'] or 'N/A', 1, 0, 'C', True)
                    pdf.cell(30, 8, f"{self.settings['currency']} {e['amount']:.2f}", 1, 1, 'C', True)
            else:
                pdf.cell(0, 10, 'No expenses found for the selected period.', 0, 1)

            # Footer with company info
            pdf.ln(15)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 10, f'Generated by {self.settings["company_name"]} Business Management System', 0, 1, 'C')
            pdf.cell(0, 5, f'Contact: {self.settings["company_phone"]} | Email: {self.settings["company_email"]}', 0, 1, 'C')

            return pdf
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return None

    def generate_employee_list_pdf(self, employees, ledger):
        if not FPDF_AVAILABLE:
            st.error("PDF generation is not available. Please install fpdf.")
            return None
            
        try:
            pdf = FPDF()
            pdf.add_page()

            # Header
            pdf.set_font('Arial', 'B', 20)
            pdf.cell(0, 10, self.settings['company_name'], 0, 1, 'C')
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Employee List Report', 0, 1, 'C')
            pdf.ln(5)

            # Report details
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
            pdf.cell(0, 8, f'Total Employees: {len(employees)}', 0, 1)
            pdf.ln(5)

            # Employee table
            if employees:
                pdf.set_font('Arial', 'B', 12)

                # Table header
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(60, 10, 'Employee Name', 1, 0, 'C', True)
                pdf.cell(40, 10, 'Initial Balance', 1, 0, 'C', True)
                pdf.cell(40, 10, 'Current Balance', 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)
                for emp in employees:
                    # Alternate row colors
                    if employees.index(emp) % 2 == 0:
                        pdf.set_fill_color(240, 240, 240)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    balance = ledger.get_employee_balance(emp['id'])
                    
                    pdf.cell(60, 8, emp['name'], 1, 0, 'C', True)
                    pdf.cell(40, 8, f"{self.settings['currency']} {emp['initial_balance']:.2f}", 1, 0, 'C', True)
                    
                    # Color code current balance
                    if balance > 0:
                        pdf.set_text_color(255, 0, 0)
                    elif balance < 0:
                        pdf.set_text_color(0, 128, 0)
                    else:
                        pdf.set_text_color(0, 0, 0)
                    
                    balance_text = f"{self.settings['currency']} {abs(balance):.2f}"
                    if balance > 0:
                        balance_text += " (Due)"
                    elif balance < 0:
                        balance_text += " (Advance)"
                    
                    pdf.cell(40, 8, balance_text, 1, 1, 'C', True)
                    pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(0, 10, 'No employees found.', 0, 1)

            # Footer with company info
            pdf.ln(15)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 10, f'Generated by {self.settings["company_name"]} Business Management System', 0, 1, 'C')
            pdf.cell(0, 5, f'Contact: {self.settings["company_phone"]} | Email: {self.settings["company_email"]}', 0, 1, 'C')

            return pdf
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return None

    def generate_comprehensive_report_pdf(self, ledger, expense_tracker, start_date=None, end_date=None):
        if not FPDF_AVAILABLE:
            st.error("PDF generation is not available. Please install fpdf.")
            return None
            
        try:
            pdf = FPDF()
            pdf.add_page()

            # Header
            pdf.set_font('Arial', 'B', 20)
            pdf.cell(0, 10, self.settings['company_name'], 0, 1, 'C')
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Comprehensive Business Report', 0, 1, 'C')
            pdf.ln(5)

            # Report period
            pdf.set_font('Arial', 'I', 12)
            period_text = f"Period: {start_date} to {end_date}" if start_date and end_date else "All Time Period"
            pdf.cell(0, 10, period_text, 0, 1, 'C')
            pdf.ln(5)

            # Report details
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Report Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
            pdf.ln(10)

            # Get data
            employees = ledger.get_employees()
            expenses = expense_tracker.get_expenses(start_date=start_date, end_date=end_date)
            expense_summary = expense_tracker.get_summary(start_date, end_date)

            # Summary section
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Business Summary', 0, 1)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Total Employees: {len(employees)}', 0, 1)
            pdf.cell(0, 8, f'Total Expenses Recorded: {len(expenses)}', 0, 1)
            pdf.cell(0, 8, f'Company Expenses: {self.settings["currency"]} {expense_summary["company_total"]:.2f}', 0, 1)
            pdf.cell(0, 8, f'Employee Expenses: {self.settings["currency"]} {expense_summary["employee_total"]:.2f}', 0, 1)
            pdf.cell(0, 8, f'Grand Total Expenses: {self.settings["currency"]} {expense_summary["grand_total"]:.2f}', 0, 1)
            pdf.ln(10)

            # Employee summary
            if employees:
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Employee Summary', 0, 1)
                pdf.set_font('Arial', 'B', 10)
                
                # Table header
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(60, 8, 'Employee', 1, 0, 'C', True)
                pdf.cell(30, 8, 'Expenses', 1, 0, 'C', True)
                pdf.cell(30, 8, 'Payments', 1, 0, 'C', True)
                pdf.cell(40, 8, 'Balance', 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 9)
                for emp in employees:
                    # Alternate row colors
                    if employees.index(emp) % 2 == 0:
                        pdf.set_fill_color(240, 240, 240)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    summary = ledger.get_employee_summary(emp['id'], start_date, end_date)
                    
                    pdf.cell(60, 6, emp['name'], 1, 0, 'C', True)
                    pdf.cell(30, 6, f"{self.settings['currency']} {summary['total_expenses']:.2f}", 1, 0, 'C', True)
                    pdf.cell(30, 6, f"{self.settings['currency']} {summary['total_payments']:.2f}", 1, 0, 'C', True)
                    
                    # Color code balance
                    if summary['balance'] > 0:
                        pdf.set_text_color(255, 0, 0)
                    elif summary['balance'] < 0:
                        pdf.set_text_color(0, 128, 0)
                    
                    balance_text = f"{self.settings['currency']} {abs(summary['balance']):.2f}"
                    if summary['balance'] > 0:
                        balance_text += " (Due)"
                    elif summary['balance'] < 0:
                        balance_text += " (Advance)"
                    
                    pdf.cell(40, 6, balance_text, 1, 1, 'C', True)
                    pdf.set_text_color(0, 0, 0)
                pdf.ln(10)

            # Expense summary
            if expenses:
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'Recent Expenses', 0, 1)
                pdf.set_font('Arial', 'B', 10)
                
                # Table header
                pdf.set_fill_color(79, 129, 189)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(25, 8, 'Date', 1, 0, 'C', True)
                pdf.cell(25, 8, 'Type', 1, 0, 'C', True)
                pdf.cell(80, 8, 'Description', 1, 0, 'C', True)
                pdf.cell(30, 8, 'Amount', 1, 1, 'C', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 8)
                for idx, exp in enumerate(expenses[:15]):  # Show last 15 expenses
                    if idx % 2 == 0:
                        pdf.set_fill_color(240, 240, 240)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    pdf.cell(25, 6, exp['date'], 1, 0, 'C', True)
                    pdf.cell(25, 6, exp['type'].title(), 1, 0, 'C', True)
                    pdf.cell(80, 6, exp['description'][:50], 1, 0, 'C', True)
                    pdf.cell(30, 6, f"{self.settings['currency']} {exp['amount']:.2f}", 1, 1, 'C', True)

            # Footer with company info
            pdf.ln(15)
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 10, f'Generated by {self.settings["company_name"]} Business Management System', 0, 1, 'C')
            pdf.cell(0, 5, f'Contact: {self.settings["company_phone"]} | Email: {self.settings["company_email"]}', 0, 1, 'C')

            return pdf
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return None

def render_dashboard(ledger, expense_tracker, pdf_generator):
    st.markdown('<div class="sub-header">📊 Business Dashboard</div>', unsafe_allow_html=True)

    # Quick stats
    employees = ledger.get_employees()
    transactions = ledger.get_transactions()
    expenses = expense_tracker.get_expenses()
    expense_summary = expense_tracker.get_summary()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f'<div class="metric-card">👥 Total Employees<br>{len(employees)}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card">💸 Total Transactions<br>{len(transactions)}</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card">🏢 Company Expenses<br>PKR {expense_summary["company_total"]:.2f}</div>',
                    unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card">👤 Employee Expenses<br>PKR {expense_summary["employee_total"]:.2f}</div>',
                    unsafe_allow_html=True)

    # Quick PDF Downloads
    st.markdown("### 📥 Quick PDF Downloads")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Comprehensive Report", use_container_width=True, key="comp_report"):
            pdf = pdf_generator.generate_comprehensive_report_pdf(ledger, expense_tracker)
            if pdf:
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="Download PDF",
                    data=pdf_output,
                    file_name=f"comprehensive_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col2:
        if st.button("👥 Employee List", use_container_width=True, key="emp_list"):
            employees = ledger.get_employees()
            pdf = pdf_generator.generate_employee_list_pdf(employees, ledger)
            if pdf:
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="Download PDF",
                    data=pdf_output,
                    file_name=f"employee_list_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col3:
        if st.button("💰 All Expenses", use_container_width=True, key="all_exp"):
            expenses = expense_tracker.get_expenses()
            pdf = pdf_generator.generate_expense_report_pdf(expenses, "All")
            if pdf:
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="Download PDF",
                    data=pdf_output,
                    file_name=f"all_expenses_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col4:
        if st.button("📈 Expense Summary", use_container_width=True, key="exp_summary"):
            expenses = expense_tracker.get_expenses()
            pdf = pdf_generator.generate_expense_report_pdf(expenses, "Summary")
            if pdf:
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="Download PDF",
                    data=pdf_output,
                    file_name=f"expense_summary_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # Recent activity
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 👥 Recent Employees")
        if employees:
            for emp in employees[:5]:
                balance = ledger.get_employee_balance(emp['id'])
                balance_text = f"PKR {abs(balance):.2f} {'(Due)' if balance > 0 else '(Advance)' if balance < 0 else ''}"
                st.write(f"**{emp['name']}** - {balance_text}")
        else:
            st.info("No employees added yet")

    with col2:
        st.markdown("### 💰 Recent Expenses")
        if expenses:
            for exp in expenses[:5]:
                type_icon = "🏢" if exp['type'] == 'company' else "👤"
                st.write(f"{type_icon} **{exp['description']}** - PKR {exp['amount']:.2f} ({exp['date']})")
        else:
            st.info("No expenses recorded yet")

    # Quick actions - FIXED: Now working properly
    st.markdown("### ⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("➕ Add New Employee", use_container_width=True, key="quick_add_emp"):
            st.session_state.current_page = "👥 Employee Ledger"
            st.session_state.active_tab = "➕ Add Employee"
            st.rerun()

    with col2:
        if st.button("💸 Record Transaction", use_container_width=True, key="quick_add_trans"):
            st.session_state.current_page = "👥 Employee Ledger"
            st.session_state.active_tab = "💸 Record Transaction"
            st.rerun()

    with col3:
        if st.button("💰 Add Expense", use_container_width=True, key="quick_add_exp"):
            st.session_state.current_page = "💰 Expense Management"
            st.session_state.active_tab = "➕ Add Expense"
            st.rerun()

    with col4:
        if st.button("📊 View Reports", use_container_width=True, key="quick_reports"):
            st.session_state.current_page = "📊 Reports & Analytics"
            st.rerun()

def render_employee_ledger(ledger, pdf_generator):
    st.markdown('<div class="sub-header">👥 Employee Ledger System</div>', unsafe_allow_html=True)
    st.write("Track expenses, payments, and balances for all employees")

    # Initialize session state for active tab
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "📋 Employee Management"

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Employee Management", 
        "➕ Add Employee", 
        "💸 Record Transaction", 
        "📊 Employee Details"
    ])

    # Set active tab from session state
    if st.session_state.get('active_tab') == "➕ Add Employee":
        st.rerun = lambda: st.experimental_set_query_params(tab="add_employee")
    elif st.session_state.get('active_tab') == "💸 Record Transaction":
        st.rerun = lambda: st.experimental_set_query_params(tab="record_transaction")

    with tab1:
        st.markdown("### 👥 Employee Management")
        
        # Search functionality
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("🔍 Search Employees", placeholder="Search by name, department, or position...")
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        employees = ledger.get_employees(search_query)
        
        if employees:
            st.markdown(f"**Found {len(employees)} employee(s)**")
            
            for emp in employees:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.write(f"**{emp['name']}**")
                        if emp.get('department') or emp.get('position'):
                            dept_info = f"{emp.get('department', '')} • {emp.get('position', '')}".strip(' •')
                            if dept_info:
                                st.caption(dept_info)
                        if emp.get('phone'):
                            st.caption(f"📞 {emp['phone']}")
                        if emp.get('email'):
                            st.caption(f"📧 {emp['email']}")
                    
                    with col2:
                        balance = ledger.get_employee_balance(emp['id'])
                        balance_text = f"PKR {abs(balance):.2f}"
                        if balance > 0:
                            st.error(f"💰 Due: {balance_text}")
                        elif balance < 0:
                            st.success(f"💰 Advance: {balance_text}")
                        else:
                            st.info("💰 Settled")
                    
                    with col3:
                        if st.button("✏️ Edit", key=f"edit_emp_{emp['id']}", use_container_width=True):
                            st.session_state.editing_employee = emp['id']
                    
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_emp_{emp['id']}", use_container_width=True):
                            st.session_state.deleting_employee = emp['id']
                    
                    st.divider()
                    
                    # Edit form
                    if st.session_state.get('editing_employee') == emp['id']:
                        with st.form(f"edit_employee_form_{emp['id']}"):
                            st.markdown("#### ✏️ Edit Employee")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                new_name = st.text_input("Name", value=emp['name'])
                                new_phone = st.text_input("Phone", value=emp.get('phone', ''))
                                new_department = st.text_input("Department", value=emp.get('department', ''))
                            with col2:
                                new_initial_balance = st.number_input("Initial Balance", value=emp['initial_balance'])
                                new_email = st.text_input("Email", value=emp.get('email', ''))
                                new_position = st.text_input("Position", value=emp.get('position', ''))
                            
                            join_date_value = emp.get('join_date')
                            if join_date_value:
                                try:
                                    if isinstance(join_date_value, str):
                                        join_date_value = datetime.strptime(join_date_value, '%Y-%m-%d').date()
                                    else:
                                        join_date_value = datetime.now().date()
                                except:
                                    join_date_value = datetime.now().date()
                            else:
                                join_date_value = datetime.now().date()
                                
                            new_join_date = st.date_input("Join Date", value=join_date_value)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Update Employee", use_container_width=True):
                                    if ledger.update_employee(emp['id'], new_name, new_initial_balance, new_phone, 
                                                         new_email, new_department, new_position, new_join_date.isoformat()):
                                        st.success("✅ Employee updated successfully!")
                                        del st.session_state.editing_employee
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    del st.session_state.editing_employee
                                    st.rerun()
                    
                    # Delete confirmation
                    if st.session_state.get('deleting_employee') == emp['id']:
                        st.warning(f"⚠️ Are you sure you want to delete **{emp['name']}**? This action cannot be undone!")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_del_emp_{emp['id']}", use_container_width=True):
                                if ledger.delete_employee(emp['id']):
                                    st.success("✅ Employee deleted successfully!")
                                    del st.session_state.deleting_employee
                                    st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_del_emp_{emp['id']}", use_container_width=True):
                                del st.session_state.deleting_employee
                                st.rerun()
        else:
            st.info("👥 No employees found. Add some employees to get started!")

    with tab2:
        st.markdown("### ➕ Add New Employee")
        with st.form("add_employee_form"):
            st.markdown("#### Employee Information")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *", placeholder="Enter employee full name")
                phone = st.text_input("Phone Number", placeholder="+92-XXX-XXXXXXX")
                department = st.text_input("Department", placeholder="e.g., Sales, IT, HR")
            with col2:
                initial_balance = st.number_input("Initial Balance", value=0.0, step=100.0, 
                                                help="Positive for due amount, negative for advance")
                email = st.text_input("Email Address", placeholder="employee@company.com")
                position = st.text_input("Position", placeholder="e.g., Manager, Developer")
            
            join_date = st.date_input("Join Date", value=datetime.now())
            
            # FIXED: Added proper submit button
            submitted = st.form_submit_button("➕ Add Employee", use_container_width=True)
            if submitted:
                if name:
                    employee_id = ledger.add_employee(name, initial_balance, phone, email, department, position, join_date.isoformat())
                    if employee_id:
                        st.success(f"✅ Employee {name} added successfully!")
                        st.rerun()
                else:
                    st.error("❌ Please enter employee name")

    with tab3:
        st.markdown("### 💸 Transaction Management")
        
        # Search transactions
        col1, col2 = st.columns([3, 1])
        with col1:
            trans_search = st.text_input("🔍 Search Transactions", placeholder="Search by description, category, or employee...")
        with col2:
            if st.button("🔄 Refresh", key="refresh_trans", use_container_width=True):
                st.rerun()
        
        transactions = ledger.get_transactions(trans_search)
        
        if transactions:
            st.markdown(f"**Found {len(transactions)} transaction(s)**")
            
            for trans in transactions:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{trans['description']}**")
                        st.caption(f"👤 {trans.get('employee_name', 'Unknown')} • {trans['date']}")
                        if trans.get('category'):
                            st.caption(f"📁 {trans['category']}")
                    
                    with col2:
                        amount_color = "red" if trans['type'] == 'expense' else "green"
                        amount_icon = "📤" if trans['type'] == 'expense' else "📥"
                        st.markdown(f"<span style='color: {amount_color}; font-weight: bold;'>{amount_icon} PKR {trans['amount']:.2f}</span>", 
                                  unsafe_allow_html=True)
                        st.caption(f"Type: {trans['type'].title()}")
                    
                    with col3, col4, col5:
                        if st.button("✏️ Edit", key=f"edit_trans_{trans['id']}", use_container_width=True):
                            st.session_state.editing_transaction = trans['id']
                        if st.button("🗑️ Delete", key=f"delete_trans_{trans['id']}", use_container_width=True):
                            st.session_state.deleting_transaction = trans['id']
                    
                    st.divider()
                    
                    # Edit transaction form
                    if st.session_state.get('editing_transaction') == trans['id']:
                        with st.form(f"edit_transaction_form_{trans['id']}"):
                            st.markdown("#### ✏️ Edit Transaction")
                            
                            employees = ledger.get_employees()
                            col1, col2 = st.columns(2)
                            with col1:
                                employee_id = st.selectbox("Employee", 
                                                         options=[emp['id'] for emp in employees],
                                                         format_func=lambda x: next(emp['name'] for emp in employees if emp['id'] == x),
                                                         index=next(i for i, emp in enumerate(employees) if emp['id'] == trans['employee_id']))
                                transaction_type = st.selectbox("Type", ["expense", "payment"], 
                                                              index=0 if trans['type'] == 'expense' else 1)
                                amount = st.number_input("Amount", value=trans['amount'])
                            with col2:
                                description = st.text_input("Description", value=trans['description'])
                                category = st.text_input("Category", value=trans.get('category', ''))
                                date = st.date_input("Date", value=datetime.strptime(trans['date'], '%Y-%m-%d').date() if isinstance(trans['date'], str) else trans['date'])
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Update Transaction", use_container_width=True):
                                    if ledger.update_transaction(trans['id'], employee_id, transaction_type, amount, description, category, date.isoformat()):
                                        st.success("✅ Transaction updated successfully!")
                                        del st.session_state.editing_transaction
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    del st.session_state.editing_transaction
                                    st.rerun()
                    
                    # Delete transaction confirmation
                    if st.session_state.get('deleting_transaction') == trans['id']:
                        st.warning(f"⚠️ Are you sure you want to delete this transaction?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_del_trans_{trans['id']}", use_container_width=True):
                                if ledger.delete_transaction(trans['id']):
                                    st.success("✅ Transaction deleted successfully!")
                                    del st.session_state.deleting_transaction
                                    st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_del_trans_{trans['id']}", use_container_width=True):
                                del st.session_state.deleting_transaction
                                st.rerun()
        
        # Add new transaction form
        st.markdown("### ➕ Record New Transaction")
        with st.form("add_transaction_form"):
            employees = ledger.get_employees()
            
            if employees:
                col1, col2 = st.columns(2)
                with col1:
                    employee_id = st.selectbox("Select Employee *", 
                                             options=[emp['id'] for emp in employees],
                                             format_func=lambda x: next(emp['name'] for emp in employees if emp['id'] == x))
                    transaction_type = st.selectbox("Transaction Type *", ["expense", "payment"])
                    amount = st.number_input("Amount *", min_value=0.0, step=100.0)
                with col2:
                    description = st.text_input("Description *", placeholder="Brief description of transaction")
                    category = st.text_input("Category", placeholder="e.g., Travel, Office, Food")
                    date = st.date_input("Date *", value=datetime.now())
                
                # FIXED: Added proper submit button
                submitted = st.form_submit_button("💾 Record Transaction", use_container_width=True)
                if submitted:
                    if description and amount > 0:
                        transaction_id = ledger.add_transaction(employee_id, transaction_type, amount, description, category, date.isoformat())
                        if transaction_id:
                            st.success("✅ Transaction recorded successfully!")
                            st.rerun()
                    else:
                        st.error("❌ Please fill all required fields correctly")
            else:
                st.info("👥 No employees found. Please add employees first.")

    with tab4:
        st.markdown("### 📊 Employee Details & Ledger")
        employees = ledger.get_employees()
        
        if employees:
            selected_employee = st.selectbox("Select Employee", 
                                           options=[emp['id'] for emp in employees],
                                           format_func=lambda x: next(emp['name'] for emp in employees if emp['id'] == x),
                                           key="employee_detail_select")
            
            if selected_employee:
                employee = ledger.get_employee(selected_employee)
                transactions = ledger.get_employee_transactions(selected_employee)
                summary = ledger.get_employee_summary(selected_employee)
                
                # Employee information card
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📊 Total Expenses", f"PKR {summary['total_expenses']:.2f}")
                with col2:
                    st.metric("💰 Total Payments", f"PKR {summary['total_payments']:.2f}")
                with col3:
                    balance_status = "Due" if summary['balance'] > 0 else "Advance" if summary['balance'] < 0 else "Settled"
                    st.metric("⚖️ Current Balance", f"PKR {abs(summary['balance']):.2f}", balance_status)
                with col4:
                    st.metric("📈 Total Transactions", summary['transaction_count'])
                
                # Date filter for transactions
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30), key="ledger_start")
                with col2:
                    end_date = st.date_input("End Date", value=datetime.now(), key="ledger_end")
                
                if st.button("🔍 Filter Transactions", key="filter_ledger"):
                    filtered_transactions = ledger.get_employee_transactions(
                        selected_employee, start_date.isoformat(), end_date.isoformat()
                    )
                    transactions = filtered_transactions
                
                # Download PDF for this employee
                if st.button("📄 Download Employee Ledger PDF", key="emp_ledger_pdf"):
                    pdf = pdf_generator.generate_employee_ledger_pdf(
                        employee['name'], transactions, summary, start_date.isoformat(), end_date.isoformat()
                    )
                    if pdf:
                        pdf_output = pdf.output(dest='S').encode('latin1')
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_output,
                            file_name=f"ledger_{employee['name']}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
                
                # Display transactions
                if transactions:
                    st.markdown("#### 📋 Transaction History")
                    for t in transactions:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                            with col1:
                                st.write(f"**{t['description']}**")
                                if t.get('category'):
                                    st.caption(f"📁 {t['category']}")
                            with col2:
                                st.write(t['date'])
                            with col3:
                                type_badge = "📤 Expense" if t['type'] == 'expense' else "📥 Payment"
                                st.write(type_badge)
                            with col4:
                                amount_color = "red" if t['type'] == 'expense' else "green"
                                st.markdown(f"<span style='color: {amount_color}; font-weight: bold;'>PKR {t['amount']:.2f}</span>", 
                                          unsafe_allow_html=True)
                            
                            st.divider()
                else:
                    st.info("💸 No transactions found for this employee.")
        else:
            st.info("👥 No employees found. Please add employees first.")

def render_expense_dashboard(expense_tracker, ledger, pdf_generator):
    st.markdown('<div class="sub-header">💰 Expense Management</div>', unsafe_allow_html=True)
    st.write("Track and manage all company and employee expenses")

    # Initialize session state for active tab
    if 'expense_active_tab' not in st.session_state:
        st.session_state.expense_active_tab = "📈 Expense Overview"

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📈 Expense Overview", 
        "➕ Add Expense", 
        "📋 Expense Management"
    ])

    with tab1:
        st.markdown("### 📈 Expense Overview")
        expense_summary = expense_tracker.get_summary()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🏢 Company Expenses", f"PKR {expense_summary['company_total']:.2f}")
        with col2:
            st.metric("👤 Employee Expenses", f"PKR {expense_summary['employee_total']:.2f}")
        with col3:
            st.metric("💰 Total Expenses", f"PKR {expense_summary['grand_total']:.2f}")
        
        # Expense breakdown
        expenses = expense_tracker.get_expenses()
        if expenses:
            df = pd.DataFrame(expenses)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                
                # Monthly trend
                monthly_expenses = df.groupby([df['date'].dt.to_period('M'), 'type'])['amount'].sum().reset_index()
                monthly_expenses['date'] = monthly_expenses['date'].astype(str)
                
                if PLOTLY_AVAILABLE:
                    fig = px.bar(monthly_expenses, x='date', y='amount', color='type',
                               title="📊 Monthly Expenses Trend", barmode='group')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(monthly_expenses.pivot(index='date', columns='type', values='amount'))

    with tab2:
        st.markdown("### ➕ Add New Expense")
        with st.form("add_expense_form"):
            col1, col2 = st.columns(2)
            with col1:
                expense_type = st.selectbox("Expense Type *", ["company", "employee"])
                amount = st.number_input("Amount *", min_value=0.0, step=100.0)
                category = st.text_input("Category", placeholder="e.g., Travel, Office Supplies")
            with col2:
                description = st.text_area("Description *", placeholder="Detailed description of the expense")
                employee_name = st.selectbox("Employee (if employee expense)", 
                                           options=[""] + [emp['name'] for emp in ledger.get_employees()],
                                           disabled=expense_type != "employee")
                date = st.date_input("Date *", value=datetime.now())
            
            status = st.selectbox("Status", ["Pending", "Approved", "Rejected", "Paid"])
            
            # FIXED: Added proper submit button
            submitted = st.form_submit_button("💾 Add Expense", use_container_width=True)
            if submitted:
                if description and amount > 0:
                    emp_name = employee_name if expense_type == "employee" else None
                    expense_id = expense_tracker.add_expense(expense_type, description, amount, category, emp_name, date.isoformat(), status)
                    if expense_id:
                        st.success("✅ Expense added successfully!")
                        st.rerun()
                else:
                    st.error("❌ Please fill all required fields correctly")

    with tab3:
        st.markdown("### 📋 Expense Management")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_type = st.selectbox("Filter by Type", ["All", "company", "employee"])
        with col2:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30), key="expense_start")
        with col3:
            end_date = st.date_input("End Date", value=datetime.now(), key="expense_end")
        
        # Search functionality
        search_query = st.text_input("🔍 Search Expenses", placeholder="Search by description, category, or employee...")
        
        # Get filtered expenses
        expense_type_filter = None if filter_type == "All" else filter_type
        expenses = expense_tracker.get_expenses(expense_type_filter, start_date.isoformat(), end_date.isoformat(), search_query)
        
        if expenses:
            st.markdown(f"**Found {len(expenses)} expense(s)**")
            
            for exp in expenses:
                with st.container():
                    col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{exp['description']}**")
                        if exp.get('employee_name'):
                            st.caption(f"👤 {exp['employee_name']}")
                        if exp.get('category'):
                            st.caption(f"📁 {exp['category']}")
                    
                    with col2:
                        st.write(exp['date'])
                    
                    with col3:
                        type_badge = "🏢" if exp['type'] == 'company' else "👤"
                        st.write(f"{type_badge} {exp['type'].title()}")
                    
                    with col4:
                        st.write(f"💰 PKR {exp['amount']:.2f}")
                    
                    with col5:
                        status_color = {
                            'Pending': 'orange',
                            'Approved': 'green', 
                            'Rejected': 'red',
                            'Paid': 'blue'
                        }.get(exp.get('status', 'Pending'), 'gray')
                        st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{exp.get('status', 'Pending')}</span>", 
                                  unsafe_allow_html=True)
                    
                    with col6:
                        if st.button("✏️ Edit", key=f"edit_exp_{exp['id']}", use_container_width=True):
                            st.session_state.editing_expense = exp['id']
                        if st.button("🗑️ Delete", key=f"delete_exp_{exp['id']}", use_container_width=True):
                            st.session_state.deleting_expense = exp['id']
                    
                    st.divider()
                    
                    # Edit expense form
                    if st.session_state.get('editing_expense') == exp['id']:
                        with st.form(f"edit_expense_form_{exp['id']}"):
                            st.markdown("#### ✏️ Edit Expense")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                new_type = st.selectbox("Expense Type", ["company", "employee"], 
                                                      index=0 if exp['type'] == 'company' else 1,
                                                      key=f"type_{exp['id']}")
                                new_amount = st.number_input("Amount", value=exp['amount'], key=f"amount_{exp['id']}")
                                new_category = st.text_input("Category", value=exp.get('category', ''), key=f"category_{exp['id']}")
                            with col2:
                                new_description = st.text_area("Description", value=exp['description'], key=f"desc_{exp['id']}")
                                new_employee = st.selectbox("Employee", 
                                                          options=[""] + [emp['name'] for emp in ledger.get_employees()],
                                                          index=0 if not exp.get('employee_name') else 
                                                          [""] + [emp['name'] for emp in ledger.get_employees()].index(exp['employee_name']),
                                                          key=f"emp_{exp['id']}",
                                                          disabled=new_type != "employee")
                                new_date = st.date_input("Date", 
                                                       value=datetime.strptime(exp['date'], '%Y-%m-%d').date() if isinstance(exp['date'], str) else exp['date'], 
                                                       key=f"date_{exp['id']}")
                            
                            new_status = st.selectbox("Status", ["Pending", "Approved", "Rejected", "Paid"],
                                                    index=["Pending", "Approved", "Rejected", "Paid"].index(exp.get('status', 'Pending')),
                                                    key=f"status_{exp['id']}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Update Expense", use_container_width=True):
                                    emp_name = new_employee if new_type == "employee" else None
                                    if expense_tracker.update_expense(exp['id'], new_type, new_description, new_amount, 
                                                                 new_category, emp_name, new_date.isoformat(), new_status):
                                        st.success("✅ Expense updated successfully!")
                                        del st.session_state.editing_expense
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    del st.session_state.editing_expense
                                    st.rerun()
                    
                    # Delete expense confirmation
                    if st.session_state.get('deleting_expense') == exp['id']:
                        st.warning(f"⚠️ Are you sure you want to delete this expense?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_del_exp_{exp['id']}", use_container_width=True):
                                if expense_tracker.delete_expense(exp['id']):
                                    st.success("✅ Expense deleted successfully!")
                                    del st.session_state.deleting_expense
                                    st.rerun()
                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_del_exp_{exp['id']}", use_container_width=True):
                                del st.session_state.deleting_expense
                                st.rerun()
        else:
            st.info("💰 No expenses found for the selected filters.")

def render_reports_analytics(ledger, expense_tracker, pdf_generator):
    st.markdown('<div class="sub-header">📊 Reports & Analytics</div>', unsafe_allow_html=True)

    # PDF Download Section
    st.markdown("### 📥 Comprehensive PDF Reports")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏢 Full Business Report", use_container_width=True, key="full_business"):
            pdf = pdf_generator.generate_comprehensive_report_pdf(ledger, expense_tracker)
            if pdf:
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="Download Full Report",
                    data=pdf_output,
                    file_name=f"full_business_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col2:
        # Date range for custom report
        col21, col22 = st.columns(2)
        with col21:
            custom_start = st.date_input("Start Date", value=datetime.now() - timedelta(days=30), key="custom_start")
        with col22:
            custom_end = st.date_input("End Date", value=datetime.now(), key="custom_end")
        
        if st.button("📅 Custom Period Report", use_container_width=True, key="custom_report"):
            pdf = pdf_generator.generate_comprehensive_report_pdf(ledger, expense_tracker, 
                                                                 custom_start.isoformat(), custom_end.isoformat())
            if pdf:
                pdf_output = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="Download Custom Report",
                    data=pdf_output,
                    file_name=f"custom_report_{custom_start}_{custom_end}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # Data Import/Export Section
    st.markdown("### 📁 Data Import & Export")
    
    tab1, tab2, tab3 = st.tabs(["📤 Export Data", "📥 Import Data", "📊 Analytics"])
    
    with tab1:
        st.markdown("#### 📤 Export Data")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export Employees
            employees = ledger.get_employees()
            if employees:
                df_employees = pd.DataFrame(employees)
                csv_employees = df_employees.to_csv(index=False)
                st.download_button(
                    label="📥 Export Employees CSV",
                    data=csv_employees,
                    file_name=f"employees_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("👥 No employee data to export")
        
        with col2:
            # Export Transactions
            transactions = ledger.get_transactions()
            if transactions:
                df_transactions = pd.DataFrame(transactions)
                csv_transactions = df_transactions.to_csv(index=False)
                st.download_button(
                    label="📥 Export Transactions CSV",
                    data=csv_transactions,
                    file_name=f"transactions_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("💸 No transaction data to export")
        
        with col3:
            # Export Expenses
            expenses = expense_tracker.get_expenses()
            if expenses:
                df_expenses = pd.DataFrame(expenses)
                csv_expenses = df_expenses.to_csv(index=False)
                st.download_button(
                    label="📥 Export Expenses CSV",
                    data=csv_expenses,
                    file_name=f"expenses_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("💰 No expense data to export")
    
    with tab2:
        st.markdown("#### 📥 Import Data")
        
        # Import Templates
        st.markdown("##### Download Import Templates")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Employees template
            employees_template = pd.DataFrame(columns=['name', 'initial_balance', 'phone', 'email', 'department', 'position', 'join_date'])
            csv_employees_template = employees_template.to_csv(index=False)
            st.download_button(
                label="📋 Employees Template",
                data=csv_employees_template,
                file_name="employees_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Transactions template
            transactions_template = pd.DataFrame(columns=['employee_id', 'type', 'amount', 'description', 'category', 'date'])
            csv_transactions_template = transactions_template.to_csv(index=False)
            st.download_button(
                label="📋 Transactions Template",
                data=csv_transactions_template,
                file_name="transactions_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col3:
            # Expenses template
            expenses_template = pd.DataFrame(columns=['type', 'description', 'amount', 'category', 'employee_name', 'date', 'status'])
            csv_expenses_template = expenses_template.to_csv(index=False)
            st.download_button(
                label="📋 Expenses Template",
                data=csv_expenses_template,
                file_name="expenses_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # File uploaders for import
        st.markdown("##### Upload Files to Import")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            uploaded_employees = st.file_uploader("Import Employees", type=['csv'], key="employees_upload")
            if uploaded_employees is not None:
                try:
                    df = pd.read_csv(uploaded_employees)
                    st.write("Preview:", df.head())
                    if st.button("Import Employees", key="import_emp"):
                        for _, row in df.iterrows():
                            ledger.add_employee(
                                row['name'],
                                float(row.get('initial_balance', 0)),
                                row.get('phone', ''),
                                row.get('email', ''),
                                row.get('department', ''),
                                row.get('position', ''),
                                row.get('join_date', datetime.now().strftime('%Y-%m-%d'))
                            )
                        st.success("✅ Employees imported successfully!")
                except Exception as e:
                    st.error(f"Error importing employees: {str(e)}")
        
        with col2:
            uploaded_transactions = st.file_uploader("Import Transactions", type=['csv'], key="transactions_upload")
            if uploaded_transactions is not None:
                try:
                    df = pd.read_csv(uploaded_transactions)
                    st.write("Preview:", df.head())
                    if st.button("Import Transactions", key="import_trans"):
                        for _, row in df.iterrows():
                            ledger.add_transaction(
                                row['employee_id'],
                                row['type'],
                                float(row['amount']),
                                row['description'],
                                row.get('category', ''),
                                row.get('date', datetime.now().strftime('%Y-%m-%d'))
                            )
                        st.success("✅ Transactions imported successfully!")
                except Exception as e:
                    st.error(f"Error importing transactions: {str(e)}")
        
        with col3:
            uploaded_expenses = st.file_uploader("Import Expenses", type=['csv'], key="expenses_upload")
            if uploaded_expenses is not None:
                try:
                    df = pd.read_csv(uploaded_expenses)
                    st.write("Preview:", df.head())
                    if st.button("Import Expenses", key="import_exp"):
                        for _, row in df.iterrows():
                            expense_tracker.add_expense(
                                row['type'],
                                row['description'],
                                float(row['amount']),
                                row.get('category', ''),
                                row.get('employee_name', ''),
                                row.get('date', datetime.now().strftime('%Y-%m-%d')),
                                row.get('status', 'Pending')
                            )
                        st.success("✅ Expenses imported successfully!")
                except Exception as e:
                    st.error(f"Error importing expenses: {str(e)}")
    
    with tab3:
        st.markdown("### 📊 Business Analytics")
        
        # Employee analytics
        employees = ledger.get_employees()
        if employees:
            employee_data = []
            for emp in employees:
                balance = ledger.get_employee_balance(emp['id'])
                employee_data.append({
                    'name': emp['name'],
                    'balance': balance,
                    'status': 'Due' if balance > 0 else 'Advance' if balance < 0 else 'Settled'
                })
            
            df_employees = pd.DataFrame(employee_data)
            
            if PLOTLY_AVAILABLE:
                fig = px.bar(df_employees, x='name', y='balance', color='status',
                           title="👥 Employee Balances", 
                           color_discrete_map={'Due': 'red', 'Advance': 'green', 'Settled': 'blue'})
                st.plotly_chart(fig, use_container_width=True)
        
        # Expense analytics
        expenses = expense_tracker.get_expenses()
        if expenses:
            df_expenses = pd.DataFrame(expenses)
            expense_by_type = df_expenses.groupby('type')['amount'].sum().reset_index()
            
            if PLOTLY_AVAILABLE:
                fig = px.pie(expense_by_type, values='amount', names='type', 
                           title="💰 Expense Distribution by Type")
                st.plotly_chart(fig, use_container_width=True)

def render_data_management(ledger, expense_tracker):
    st.markdown('<div class="sub-header">📁 Data Management</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🗃️ Database Management", "🔄 System Reset"])
    
    with tab1:
        st.markdown("### 📊 Database Information")
        
        employees = ledger.get_employees()
        transactions = ledger.get_transactions()
        expenses = expense_tracker.get_expenses()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Total Employees", len(employees))
        with col2:
            st.metric("💸 Total Transactions", len(transactions))
        with col3:
            st.metric("💰 Total Expenses", len(expenses))
        
        st.markdown("### 💾 Backup Data")
        if st.button("🔄 Create Backup", key="create_backup"):
            # Simple backup implementation
            backup_data = {
                'employees': employees,
                'transactions': transactions,
                'expenses': expenses,
                'backup_date': datetime.now().isoformat()
            }
            
            json_data = json.dumps(backup_data, indent=2)
            st.download_button(
                label="📥 Download Backup",
                data=json_data,
                file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with tab2:
        st.markdown("### ⚠️ System Reset")
        st.warning("🚨 This action cannot be undone! All data will be permanently deleted.")
        
        if st.button("🗑️ Reset All Data", type="secondary", use_container_width=True):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('DELETE FROM employees')
            c.execute('DELETE FROM transactions')
            c.execute('DELETE FROM expenses')
            conn.commit()
            conn.close()
            st.success("✅ All data has been reset!")
            st.rerun()

def render_settings(settings_manager):
    st.markdown('<div class="sub-header">⚙️ System Settings</div>', unsafe_allow_html=True)
    
    settings = settings_manager.get_settings()
    
    with st.form("settings_form"):
        st.markdown("### 🏢 Company Information")
        
        company_name = st.text_input("Company Name", value=settings['company_name'])
        company_address = st.text_area("Company Address", value=settings['company_address'])
        company_phone = st.text_input("Phone Number", value=settings['company_phone'])
        company_email = st.text_input("Email Address", value=settings['company_email'])
        
        st.markdown("### ⚙️ System Settings")
        currency = st.selectbox("Currency", ["PKR", "USD", "EUR", "GBP"], 
                               index=["PKR", "USD", "EUR", "GBP"].index(settings['currency']))
        
        # FIXED: Added proper submit buttons
        col1, col2 = st.columns(2)
        with col1:
            save_submitted = st.form_submit_button("💾 Save Settings", use_container_width=True)
            if save_submitted:
                settings_manager.update_settings(company_name, company_address, company_phone, company_email, currency)
                st.success("✅ Settings saved successfully!")
                st.rerun()
        
        with col2:
            reset_submitted = st.form_submit_button("🔄 Reset to Default", use_container_width=True)
            if reset_submitted:
                settings_manager.update_settings(
                    "HMD Solutions", 
                    "Karachi, Pakistan", 
                    "+92-3207429422", 
                    "info@hmdsolutions.com", 
                    "PKR"
                )
                st.success("✅ Settings reset to default!")
                st.rerun()

def render_footer():
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <h3>🚀 DatanexSolution</h3>
        <p>Advanced Business Management Solutions</p>
        <p>For any query please feel free to contact: <strong>+92-3207429422</strong></p>
        <p>📧 Email: info@datanexsolution.com | 🌐 Website: www.datanexsolution.com</p>
        <p style="margin-top: 1rem; font-size: 0.9rem; opacity: 0.8;">
            &copy; 2024 HMD Solutions. All rights reserved.
        </p>
    </div>
    """, unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header">🚀 HMD Solutions - Business Management System</div>', unsafe_allow_html=True)

    # Initialize systems
    ledger = EmployeeLedger()
    expense_tracker = ExpenseTracker()
    pdf_generator = PDFGenerator()
    settings_manager = SettingsManager()

    # Initialize session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Dashboard"
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "📋 Employee Management"
    if 'expense_active_tab' not in st.session_state:
        st.session_state.expense_active_tab = "📈 Expense Overview"
    if 'editing_employee' not in st.session_state:
        st.session_state.editing_employee = None
    if 'deleting_employee' not in st.session_state:
        st.session_state.deleting_employee = None
    if 'editing_transaction' not in st.session_state:
        st.session_state.editing_transaction = None
    if 'deleting_transaction' not in st.session_state:
        st.session_state.deleting_transaction = None
    if 'editing_expense' not in st.session_state:
        st.session_state.editing_expense = None
    if 'deleting_expense' not in st.session_state:
        st.session_state.deleting_expense = None

    # Sidebar navigation
    st.sidebar.markdown("""
    <div style='background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center;'>
        <h2>🚀 Navigation</h2>
    </div>
    """, unsafe_allow_html=True)

    # Navigation with session state
    app_mode = st.sidebar.selectbox(
        "Choose Application",
        ["🏠 Dashboard", "👥 Employee Ledger", "💰 Expense Management", "📊 Reports & Analytics", "📁 Data Management", "⚙️ Settings"],
        index=["🏠 Dashboard", "👥 Employee Ledger", "💰 Expense Management", "📊 Reports & Analytics", "📁 Data Management", "⚙️ Settings"].index(st.session_state.current_page)
    )

    # Update current page
    st.session_state.current_page = app_mode

    # Quick actions in sidebar - FIXED: Now working properly
    st.sidebar.markdown("### ⚡ Quick Actions")
    if st.sidebar.button("➕ Add Employee", use_container_width=True, key="sidebar_add_emp"):
        st.session_state.current_page = "👥 Employee Ledger"
        st.session_state.active_tab = "➕ Add Employee"
        st.rerun()
        
    if st.sidebar.button("💸 Add Transaction", use_container_width=True, key="sidebar_add_trans"):
        st.session_state.current_page = "👥 Employee Ledger"
        st.session_state.active_tab = "💸 Record Transaction"
        st.rerun()
        
    if st.sidebar.button("💰 Add Expense", use_container_width=True, key="sidebar_add_exp"):
        st.session_state.current_page = "💰 Expense Management"
        st.session_state.expense_active_tab = "➕ Add Expense"
        st.rerun()

    # Footer in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style='text-align: center; color: #666;'>
        <h4>🚀 DatanexSolution</h4>
        <p>For any query please feel free to contact:</p>
        <p><strong>📞 +92-3207429422</strong></p>
    </div>
    """, unsafe_allow_html=True)

    # Render the selected page
    if st.session_state.current_page == "🏠 Dashboard":
        render_dashboard(ledger, expense_tracker, pdf_generator)
    elif st.session_state.current_page == "👥 Employee Ledger":
        render_employee_ledger(ledger, pdf_generator)
    elif st.session_state.current_page == "💰 Expense Management":
        render_expense_dashboard(expense_tracker, ledger, pdf_generator)
    elif st.session_state.current_page == "📊 Reports & Analytics":
        render_reports_analytics(ledger, expense_tracker, pdf_generator)
    elif st.session_state.current_page == "📁 Data Management":
        render_data_management(ledger, expense_tracker)
    else:  # Settings
        render_settings(settings_manager)

if __name__ == "__main__":
    main()
    render_footer()
