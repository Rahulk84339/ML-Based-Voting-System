import pymongo
from flask import Flask, render_template, request
from datetime import datetime
import random
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
mongoDB_connection = pymongo.MongoClient("mongodb+srv://<username>:<password>@cluster0.cynvddz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
database = mongoDB_connection["voting_system"]

class Voter:
    def __init__(self, voter_id, full_name, adhaar_id, face_data, fingerprint_data):
        self.voter_id = voter_id
        self.fullName = full_name
        self.adhaar_id = adhaar_id
        self.face_data = face_data
        self.fingerprint_data = fingerprint_data

class Candidate:
    def __init__(self, candidate_id, name, party_name, symbol_path):
        self.candidate_id = candidate_id
        self.name = name
        self.party_name = party_name
        self.symbol_path = symbol_path

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/voter_registration')
def voter_registration():
    return render_template('voter_registration.html')

@app.route('/candidate_registration')
def candidate_registration():
    return render_template('candidate_registration.html')

@app.route('/voting_results')
def voting_results():
    return render_template('voting_results.html')

@app.route('/submit_voter_registration', methods=['POST'])
def submit_voter_registration():
    full_name = request.form.get('name')
    adhaar_id = request.form.get('AdhaarId')

    try:
        # Generate Voter ID Number
        voter_id = generate_voter_id()

        # Save the generated voter ID to MongoDB for voters
        voters_collection = database["voters"]
        new_voter = Voter(voter_id, full_name, adhaar_id, face_data, fingerprint_data)
        voters_collection.insert_one(new_voter.__dict__)

        # Render the display template directly with the generated voter ID
        return render_template('display_voter_id.html', voter_id=voter_id, full_name=full_name, adhaar_id=adhaar_id)

    except Exception as e:
        # Print the exception for debugging
        print(f"Exception: {e}")
        raise e

@app.route('/submit_candidate_registration', methods=['POST'])
def submit_candidate_registration():
    full_name = request.form.get('name')
    party_name = request.form.get('partyName')
    symbol = request.files['symbol']

    # Generate Voter ID Number for candidate (not necessary but kept for consistency)
    voter_id = generate_voter_id()

    # Save the candidate information to MongoDB for candidates
    candidates_collection = database["candidates"]
    symbol_path = save_symbol(symbol)
    new_candidate = Candidate(voter_id, full_name, party_name, symbol_path)
    candidates_collection.insert_one(new_candidate.__dict__)

    # Render the display template directly with the generated voter ID
    return render_template('display_candidate_info.html', voter_id=voter_id, full_name=full_name, party_name=party_name, symbol_path=new_candidate.symbol_path)

def generate_voter_id():
    # Get the current timestamp to add to the voter ID
    timestamp_part = datetime.now().strftime("%Y%m")

    # Generate a random 4-digit number
    random_digits = str(random.randint(1000, 9999))

    # Combine the parts to create the final voter ID
    voter_id = f"{timestamp_part}{random_digits}"

    return voter_id

def save_symbol(symbol_file):
    # Ensure the 'symbols' directory exists
    symbols_directory = 'static/symbols'
    os.makedirs(symbols_directory, exist_ok=True)

    # Save the uploaded symbol file and return the file path
    symbol_path = os.path.join(symbols_directory, secure_filename(symbol_file.filename))
    symbol_file.save(symbol_path)
    return symbol_path

if __name__ == '__main__':
    app.run(debug=True)
