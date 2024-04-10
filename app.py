import pymongo
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import random
from PIL import Image
import base64
import os
import io
from random import randint

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
mongoDB_connection = pymongo.MongoClient(os.getenv('MONGO_URI'))
database = mongoDB_connection["voting_system"]
voters_collection, candidates_collection, votes_collection = database["voters"], database["candidates"], database["votes"]


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


class Vote:
    def __init__(self, voter_id, candidate_id):
        self.voter_id = voter_id
        self.candidate_id = candidate_id


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/voter_registration')
def voter_registration():
    return render_template('voter_registration.html')


@app.route('/candidate_registration')
def candidate_registration():
    return render_template('candidate_registration.html')


@app.route('/image_capture')
def image_capture():
    return render_template('image_capture.html')


@app.route('/voting')
def voting():
    candidates = candidates_collection.find()  # Fetch all candidates from the database
    return render_template('voting.html', candidates = candidates)


@app.route('/voting_results')
def voting_results():
    candidates_data, colors, winner = dashboard()
    votes = list(votes_collection.find())

    # Check if there are no votes
    if candidates_data is None or votes is None:
        return render_template('voting_results.html', candidates = None, backgroundColors = None,
                               votes = None)  # Render the template with no votes

    return render_template('voting_results.html', candidates = candidates_data, backgroundColors = colors,
                           winner = winner, votes = votes)  # Render the template with voting results


@app.route('/submit_voter_registration', methods = ['POST'])
def submit_voter_registration():
    full_name = request.form.get('name')
    adhaar_id = request.form.get('AdhaarId')
    image_data = request.form.get('imageData')
    fingerprint_data = request.form.get('fingerprintData')

    try:
        voter_id = generate_voter_id()
        new_voter = Voter(voter_id, full_name, adhaar_id, image_data, fingerprint_data)
        voters_collection.insert_one(new_voter.__dict__)

        # Use flash to send the success message
        flash(f'Voter Registration Success!\nVoter Id: {voter_id}\nName: {full_name}\nAadhaar Number: {adhaar_id}', 'success')

        return redirect(url_for('voter_registration'))

    except Exception as e:
        print(f"Exception: {e}")
        # Use flash to send an error message
        flash('An error occurred during registration. Please try again.', 'error')
        return redirect(url_for('voter_registration'))


@app.route('/submit_candidate_registration', methods = ['POST'])
def submit_candidate_registration():
    full_name = request.form.get('name')
    party_name = request.form.get('partyName')
    image = request.files['image']  # Retrieve the candidate image file

    # Generate Voter ID Number for candidate (not necessary but kept for consistency)
    candidate_id = generate_voter_id()

    # Save the candidate information to MongoDB for candidates
    image_data = save_image(image)  # Save the candidate image and retrieve its data

    # Encode the image data to base64
    image_data_base64 = base64.b64encode(image_data).decode('utf-8')

    new_candidate = Candidate(candidate_id, full_name, party_name, image_data_base64)
    candidates_collection.insert_one(new_candidate.__dict__)

    # Use flash to send the success message
    flash(f'Candidate Registration Success!\nName: {full_name}\nParty Name: {party_name}',
          'success')
    return redirect(url_for('candidate_registration'))


@app.route('/submit_vote', methods = ['POST'])
def submit_vote():
    voter_id = request.form.get('voterId')  # Get the voter ID from the form
    candidate_id = request.form.get('candidateID')  # Get the candidate ID from the form

    # Check if the voter has already voted
    if votes_collection.find_one({'voter_id': voter_id}):
        return redirect(url_for('voting', message = 'You have already voted!'))

    # Insert the vote into the votes collection
    new_vote = Vote(voter_id, candidate_id)
    votes_collection.insert_one(new_vote.__dict__)

    # Redirect the user to the voting results page
    return redirect(url_for('voting', message = 'Voted Successfully!'))


def generate_voter_id():
    # Get the current timestamp to add to the voter ID
    timestamp_part = datetime.now().strftime("%Y%m")

    # Generate a random 4-digit number
    random_digits = str(random.randint(1000, 9999))

    # Combine the parts to create the final voter ID
    voter_id = f"{timestamp_part}{random_digits}"

    return voter_id


# Function to save image
def save_image(image_file):
    # Open the image using PIL
    image = Image.open(image_file.stream)

    # Convert the image to RGB mode (compatible with JPEG)
    image = image.convert('RGB')

    # Save the image as JPEG
    with io.BytesIO() as output:
        image.save(output, format = "JPEG")
        image_data = output.getvalue()

    return image_data


def dashboard():
    candidates_data = {}

    # Fetch all candidates from the candidates collection
    candidates = list(candidates_collection.find())

    # Generate random colors for each candidate
    colors = ['rgba({}, {}, {}, 0.5)'.format(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in
              range(len(candidates))]

    # Iterate over each candidate and initialize their vote count
    for candidate in candidates:
        candidate_party = f"{candidate['name']} ({candidate['party_name']})"
        candidates_data[candidate_party] = 0

    # Fetch all votes from the votes collection
    votes = list(votes_collection.find())

    # Iterate over each vote and aggregate the vote count for each candidate
    for vote in votes:
        candidate_id = vote['candidate_id']
        candidate = candidates_collection.find_one({'candidate_id': candidate_id})
        if candidate:
            candidate_party = f"{candidate['name']} ({candidate['party_name']})"
            if candidate_party in candidates_data:
                candidates_data[candidate_party] += 1

    # Find the winner(s)
    winner = get_winner(candidates_data)

    return candidates_data, colors, winner  # Return the dictionary containing candidate data, colors, and winner


def get_winner(candidates_data):
    if not candidates_data:
        return None

    # Find the candidate(s) with the most votes
    max_votes = max(candidates_data.values())
    winners = [candidate for candidate, votes in candidates_data.items() if votes == max_votes]

    return winners


if __name__ == '__main__':
    app.run(debug = True)
