from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQ
app = Flask(__name__)
# ======================
# Database Configuration
# ======================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "expenses.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ======================
# Database Model
# ======================
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "amount": self.amount,
        }


# ======================
# Create DB (first run)
# ======================
with app.app_context():
    db.create_all()


# ======================
# Routes
# ======================

@app.route("/")
def home():
    """Default route -> opens index.html"""
    return render_template("index.html")


@app.route("/expenses")
def expense_page():
    """Open expense.html page"""
    return render_template("Expense.html")


@app.route("/api/expenses", methods=["GET", "POST"])
def handle_expenses():
    """GET all expenses or POST new expense"""
    if request.method == "POST":
        data = request.json
        new_expense = Expense(
            category=data["category"],
            description=data["description"],
            amount=float(data["amount"]),
        )
        db.session.add(new_expense)
        db.session.commit()
        return jsonify({"message": "Expense added successfully!"}), 201

    # GET all expenses
    expenses = Expense.query.all()
    return jsonify([e.to_dict() for e in expenses])


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    """Delete an expense by ID"""
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"message": "Expense deleted!"})


# ======================
# Run App
# ======================
if __name__ == "__main__":
    app.run(debug=True)
