from flask import Flask, render_template, request, redirect, url_for, jsonify
import smtplib
from datetime import datetime, timedelta
import re
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

app = Flask(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler({
    'apscheduler.jobstores.default': SQLAlchemyJobStore(url='sqlite:///jobs.db'),
    'apscheduler.executors.default': {'class': 'apscheduler.executors.pool:ThreadPoolExecutor', 'max_workers': '20'},
    'apscheduler.job_defaults.coalesce': 'false',
    'apscheduler.job_defaults.max_instances': '3',
})

def send_pending_followups():
    """Check and send any pending follow-up emails"""
    conn = sqlite3.connect('followups.db')
    c = conn.cursor()
    
    today = datetime.now().date()
    
    c.execute('''SELECT * FROM followups 
                 WHERE send_date <= ? 
                 AND sent IS NULL''', (today,))
    pending_emails = c.fetchall()
    
    for email in pending_emails:
        try:
            _, sender, receiver, subject, body, send_date, gmail_key = email
            
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, gmail_key)
            
            text = f"Subject: {subject}\n\n{body}"
            server.sendmail(sender, receiver, text)
            
            c.execute('''UPDATE followups 
                        SET sent = 1 
                        WHERE sender = ? 
                        AND receiver = ? 
                        AND send_date = ?''', 
                     (sender, receiver, send_date))
            
            print(f"Follow-up email sent to {receiver}")
            server.quit()
            
        except Exception as e:
            print(f"Error sending email to {receiver}: {str(e)}")
    
    conn.commit()
    conn.close()

# Start the scheduler when the app starts
@app.before_first_request
def init_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            send_pending_followups,
            'interval',
            minutes=1,
            id='send_followups',
            replace_existing=True
        )
        scheduler.start()

def sanitize_input(input_str):
    """Remove special characters from input to prevent issues."""
    if input_str:
        return re.sub(r'[^\w\s@.]+', '', input_str)
    return input_str

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return redirect(url_for('parameters'))
    return render_template('index.html')

@app.route('/parameters', methods=['GET', 'POST'])
def parameters():
    return render_template('parameters.html')

@app.route('/submit', methods=['POST'])
def submit():
    # Step 1: Collect and sanitize Gmail key and user email
    gmail_key = sanitize_input(request.form.get('gmailKey'))
    user_email = sanitize_input(request.form.get('userEmail'))

    # Step 2: Collect and sanitize Replace values
    num_params = int(request.form.get('numParams'))
    replace_values = [sanitize_input(request.form.get(f'replace{i}')) for i in range(1, num_params + 1)]

    # Step 3: Collect and sanitize emails and their parameters
    num_emails = int(request.form.get('numEmails'))
    emails_data = []
    for i in range(1, num_emails + 1):
        email = sanitize_input(request.form.get(f'email{i}'))
        params = [sanitize_input(request.form.get(f'email{i}_param{j}')) for j in range(1, num_params + 1)]
        emails_data.append({"email": email, "parameters": params})

    # Step 4: Collect and sanitize initial and follow-up email data
    initial_subject = sanitize_input(request.form.get('initialSubject'))
    initial_body = sanitize_input(request.form.get('initialBody'))

    followup_subject = sanitize_input(request.form.get('followupSubject'))
    followup_body = sanitize_input(request.form.get('followupBody'))

    followup_days = int(request.form.get('followupDays'))

    # Step 6: Prepare the data for email processing
    data = {
        "user_email": user_email,
        "gmail_key": gmail_key,
        "replace_values": replace_values,
        "emails_data": emails_data,
        "initial_subject": initial_subject,
        "initial_body": initial_body,
        "followup_subject": followup_subject,
        "followup_body": followup_body,
        "followup_days": followup_days
    }

    # Send initial emails and schedule follow-ups
    refined_data = process_data(data)
    initsend(refined_data, user_email, gmail_key)
    
    # Store follow-up email data in database for later sending
    conn = sqlite3.connect('followups.db')
    c = conn.cursor()
    
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS followups
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT,
                  receiver TEXT, 
                  subject TEXT,
                  body TEXT,
                  send_date DATE,
                  gmail_key TEXT,
                  sent BOOLEAN DEFAULT NULL)''')
    
    # Calculate send date for follow-ups
    send_date = (datetime.now() + timedelta(minutes=data['followup_days'])).date()  # Changed from days to minutes
    
    # Store each follow-up email
    for entry in refined_data:
        c.execute('''INSERT INTO followups 
                     (sender, receiver, subject, body, send_date, gmail_key)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_email, 
                  entry['email'],
                  entry['followup_subject'],
                  entry['followup_body'], 
                  send_date,
                  gmail_key))
    
    conn.commit()
    conn.close()

    # Render the success page with relevant info
    return render_template('confirm.html', num_emails=num_emails)

def process_data(data):
    """Format the email data by replacing placeholders."""
    formatted_emails = []

    for email_data in data['emails_data']:
        email = email_data['email']
        params = email_data['parameters']

        initial_subject = data['initial_subject']
        initial_body = data['initial_body']
        followup_subject = data['followup_subject']
        followup_body = data['followup_body']

        for placeholder, value in zip(data['replace_values'], params):
            initial_subject = initial_subject.replace(placeholder, value)
            initial_body = initial_body.replace(placeholder, value)
            followup_subject = followup_subject.replace(placeholder, value)
            followup_body = followup_body.replace(placeholder, value)

        formatted_emails.append({
            'email': email,
            'initial_subject': initial_subject,
            'initial_body': initial_body,
            'followup_subject': followup_subject,
            'followup_body': followup_body
        })

    return formatted_emails

def initsend(data, sender, key):
    """Send initial emails to the recipients."""
    for entry in data:
        receiver = entry['email']
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, key)
        text = f"Subject: {entry['initial_subject']}\n\n{entry['initial_body']}"
        server.sendmail(sender, receiver, text)
        print(f"Initial email sent to {receiver}")
    server.quit()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)  # use_reloader=False prevents duplicate scheduler execution