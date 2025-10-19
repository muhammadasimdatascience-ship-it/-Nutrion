from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from database import db, init_db
from models import Expense
import os
import json
from datetime import datetime, timedelta
from io import BytesIO

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production

# Initialize database
init_db(app)


# Sample data for initialization
def init_sample_data():
    """Initialize with sample data if database is empty"""
    with app.app_context():
        if Expense.query.count() == 0:
            sample_expenses = [
                {
                    'type': 'company',
                    'description': 'Office Supplies',
                    'amount': 150.75,
                    'employee_name': None,
                    'date': '2024-08-27'
                },
                {
                    'type': 'employee',
                    'description': 'Client Lunch',
                    'amount': 85.50,
                    'employee_name': 'Ali Khan',
                    'date': '2024-08-26'
                },
                {
                    'type': 'employee',
                    'description': 'Travel to a conference',
                    'amount': 500.00,
                    'employee_name': 'Sana Butt',
                    'date': '2024-08-25'
                },
                {
                    'type': 'employee',
                    'description': 'Software Subscription',
                    'amount': 120.00,
                    'employee_name': 'Ali Khan',
                    'date': '2024-08-24'
                }
            ]

            for expense_data in sample_expenses:
                expense = Expense.from_dict(expense_data)
                db.session.add(expense)

            db.session.commit()
            print("Sample data initialized")


# Initialize sample data
init_sample_data()


# API Routes
@app.route('/')
def home():
    return jsonify({
        'message': 'Expense Tracker API',
        'version': '1.0',
        'endpoints': {
            'GET /api/expenses': 'Get all expenses',
            'POST /api/expenses': 'Create new expense',
            'DELETE /api/expenses/<id>': 'Delete expense',
            'GET /api/expenses/stats': 'Get expense statistics',
            'GET /api/expenses/employees': 'Get unique employee names'
        }
    })


@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get all expenses with optional filtering"""
    try:
        # Get query parameters for filtering
        expense_type = request.args.get('type', 'all')
        search_term = request.args.get('search', '')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        # Start with base query
        query = Expense.query

        # Apply type filter
        if expense_type != 'all':
            query = query.filter(Expense.type == expense_type)

        # Apply search filter
        if search_term:
            query = query.filter(
                (Expense.description.ilike(f'%{search_term}%')) |
                (Expense.employee_name.ilike(f'%{search_term}%'))
            )

        # Apply date range filter
        if from_date:
            query = query.filter(Expense.date >= from_date)
        if to_date:
            query = query.filter(Expense.date <= to_date)

        # Order by date (newest first)
        expenses = query.order_by(Expense.date.desc()).all()

        return jsonify({
            'success': True,
            'expenses': [expense.to_dict() for expense in expenses]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/expenses', methods=['POST'])
def create_expense():
    """Create a new expense"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['type', 'description', 'amount', 'date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Validate expense type
        if data['type'] not in ['company', 'employee']:
            return jsonify({
                'success': False,
                'error': 'Expense type must be "company" or "employee"'
            }), 400

        # Validate employee name for employee expenses
        if data['type'] == 'employee' and (not data.get('employee_name') or not data['employee_name'].strip()):
            return jsonify({
                'success': False,
                'error': 'Employee name is required for employee expenses'
            }), 400

        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Amount must be positive'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid amount format'
            }), 400

        # Create new expense
        expense = Expense.from_dict(data)
        db.session.add(expense)
        db.session.commit()

        return jsonify({
            'success': True,
            'expense': expense.to_dict(),
            'message': 'Expense added successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """Delete an expense by ID"""
    try:
        expense = Expense.query.get_or_404(expense_id)

        db.session.delete(expense)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Expense deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/expenses/stats', methods=['GET'])
def get_expense_stats():
    """Get expense statistics and totals"""
    try:
        expenses = Expense.query.all()

        # Calculate totals
        company_total = sum(exp.amount for exp in expenses if exp.type == 'company')
        employee_total = sum(exp.amount for exp in expenses if exp.type == 'employee')
        grand_total = company_total + employee_total

        # Get current and previous month totals
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        previous_month = current_month - 1 if current_month > 1 else 12
        previous_year = current_year if current_month > 1 else current_year - 1

        current_month_expenses = sum(
            exp.amount for exp in expenses
            if exp.date and datetime.strptime(exp.date, '%Y-%m-%d').month == current_month
            and datetime.strptime(exp.date, '%Y-%m-%d').year == current_year
        )

        previous_month_expenses = sum(
            exp.amount for exp in expenses
            if exp.date and datetime.strptime(exp.date, '%Y-%m-%d').month == previous_month
            and datetime.strptime(exp.date, '%Y-%m-%d').year == previous_year
        )

        # Expense breakdown by category (simple categorization)
        categories = {}
        for expense in expenses:
            category = expense.description.split(' ')[0]  # Simple categorization
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'total': 0,
                    'average': 0
                }
            categories[category]['count'] += 1
            categories[category]['total'] += expense.amount

        # Calculate averages
        for category in categories:
            if categories[category]['count'] > 0:
                categories[category]['average'] = categories[category]['total'] / categories[category]['count']

        return jsonify({
            'success': True,
            'stats': {
                'company_total': company_total,
                'employee_total': employee_total,
                'grand_total': grand_total,
                'current_month_total': current_month_expenses,
                'previous_month_total': previous_month_expenses,
                'breakdown': categories
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/expenses/employees', methods=['GET'])
def get_employee_names():
    """Get unique employee names for autocomplete"""
    try:
        employee_names = db.session.query(Expense.employee_name).filter(
            Expense.employee_name.isnot(None)
        ).distinct().all()

        names = [name[0] for name in employee_names if name[0]]

        return jsonify({
            'success': True,
            'employees': names
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/expenses/export/csv', methods=['GET'])
def export_csv():
    """Export expenses as CSV"""
    try:
        expenses = Expense.query.all()

        csv_data = "ID,Type,Employee Name,Description,Amount (PKR),Date\n"
        for expense in expenses:
            csv_data += f"{expense.id},{expense.type},{expense.employee_name or ''},\"{expense.description}\",{expense.amount},{expense.date}\n"

        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=expenses_{datetime.now().strftime("%Y-%m-%d")}.csv'
        }

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5003)