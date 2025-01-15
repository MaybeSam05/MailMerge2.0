from flask import Flask, render_template, request, redirect, url_for
from services.email_service import send_email

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        name = request.form.get('name')
        return f"Hello, {name}!"
    return render_template('submit.html')


@app.route('/send')
def send():
    send_email("test@example.com", "Subject", "Body")
    return "Email sent"


if __name__ == "__main__":
    app.run(debug=True)

# use smtp library