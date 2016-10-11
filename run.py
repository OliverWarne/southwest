from flask import Flask, Response, request, session
from twilio import twiml

import time
import sqlite3

app = Flask(__name__)
app.config.from_object(__name__)
# A secret key is required in order to store session data
secret_key = 'xxxsecretkeyxxx'

@app.route("/")
def hello():
    return "Hello"

@app.route("/twilio", methods=["POST"])
def respond_sms():
    # Grab unix time
    epoch_time = int(time.time())
    # Store the message from the request sent by twilio
    i_msg = request.form.get("Body")
    # Store the number the message was sent from
    from_number = request.values.get("From")
    
    # The counter keeps track of the number of messages from this number in the
    # past 4 hours. If none, default to 0
    counter = session.get('counter', 0)
    counter += 1
    session['counter'] = counter
    # Retrieve the stored state from twilio's servers. Again, default to 0
    state = session.get('state', 0)
    # Record the message in the sqlite db
    sql_write(counter, epoch_time, from_number, i_msg)
    
    # The default message is ERROR. There should not be a point where there is
    # fall through and this happens
    msg = "ERROR"
    
    # If the person texts "RESET_ZER0", reset the state to zero. This is
    # just for debugging purposes
    if "RESET_ZER0" in i_msg:
        state = 0

    if "Call" in i_msg:
        msg = "Okay! A human will call you shortly. Thank you for checking in."
        state = 200  

    if state == 0:
        msg = "Hello. I see that you are currently not checked into the airport X for flight #YYY. Are you currently at the airport? Please reply with Y or N"
        state = 1

    # This is the state of responding to the inital text
    elif state == 1:
        if "Y" in i_msg:
            msg = "You have been checked in!"
            state = 200
        elif "N" in i_msg:
            msg = "Uh oh! Will you be making the flight?"
            state = 2
        else: 
            msg = "I did not understand that, sorry! Please reply with either Y if you will be making the flight, or N if you will not"

    # This is the state of Not checked in
    elif state == 2:
        if "Y" in i_msg:
            msg = "Thanks! If you are not checked in within the hour, a human will be in contact with you."
            state = 200
        elif "N" in i_msg:
            msg = "I'm sorry to hear that. A human will call you shortly in order to resolve any issue"
            state = 400
        else:
            msg = "I did not understand that, sorry! Please reply with either Y if you will be making the flight, or N if you will not"

    # This is the "failure state". This means we need to involve humans
    elif state == 400:
        msg = "There has been an issue with our system. A human will be in contact with you in order to resolve any issue."
        state = 0

    # Prepare and then send a twilio SMS respond
    resp = twiml.Response()
    resp.sms(msg)
    
    # This is the success state. Send a thank you text and switch back to the 
    # beginning state
    if state == 200:
        msg = "Thank you for flying for Southwest! If you have an unresolved issue, please contact (ZZZ)-XXX-YYYY"
        state = 0
        resp.sms(msg)

    # Store the state and time in the session cookie
    session['state'] = state
    session['time'] = epoch_time
    
    return str(resp)
    
# Write the message to the db
def sql_write(m_id, m_time, m_from, m_text, new=False):
    conn = sqlite3.connect('test.db')
    c = conn.cursor()
    if new:
        c.execute('''CREATE TABLE messages
                     (num real, time real, frm text, msg text)''')
    c.execute('''INSERT INTO messages VALUES (?, ?, ?, ?)''',
                (m_id, m_time, m_from, m_text))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    app.secret_key = secret_key
    app.run(debug=True)
