from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)
##Test
# ---------- MySQL CONNECTION ----------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="vijihema",   # your MySQL root password
    database="irctc_db"    # your database name
)

cursor = db.cursor()

# ---------- CREATE TABLE ----------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(100)
)
""")
db.commit()

# ---------- REGISTER API ----------
@app.route('/register', methods=['POST'])
def register():
    try:
        # Read JSON data
        data = request.get_json(force=True)  # force=True avoids header errors

        username = data['username']
        email = data['email']
        password = data['password']

        # Insert into MySQL
        sql = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
        cursor.execute(sql, (username, email, password))
        db.commit()

        return jsonify({"message": "User registered successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# ---------- LOGIN API ----------
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(force=True)

        email = data['email']
        password = data['password']

        # Check user in database
        sql = "SELECT * FROM users WHERE email=%s AND password=%s"
        cursor.execute(sql, (email, password))
        user = cursor.fetchone()

        if user:
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"message": "Sorry, the given data is not matched"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 400

#-----------choosing the source and destination-----------
    
@app.route('/train-types', methods=['POST'])
def get_train_types():
    data = request.get_json(force=True)

    source = data['source_city']
    destination = data['destination_city']

    sql = """
    SELECT DISTINCT train_type 
    FROM trains 
    WHERE source_city=%s AND destination_city=%s
    LIMIT 10
    """
    cursor.execute(sql, (source, destination))
    result = cursor.fetchall()

    train_types = [row[0] for row in result]

    return jsonify({"train_types": train_types}), 200


#-----------------train-details-----------

@app.route('/train-details', methods=['POST'])
def get_train_details():
    data = request.get_json(force=True)

    source = data['source_city']
    destination = data['destination_city']
    train_type = data['train_type']

    sql = """
    SELECT train_name, departure_time, arrival_time, available_seats
    FROM trains
    WHERE source_city=%s AND destination_city=%s AND train_type=%s
    """
    cursor.execute(sql, (source, destination, train_type))
    trains = cursor.fetchall()

    train_list = []
    for t in trains:
        train_list.append({
            "train_name": t[0],
            "departure_time": str(t[1]),
            "arrival_time": str(t[2]),
            "available_seats": t[3]
        })

    return jsonify({"trains": train_list}), 200



#---------------book-ticket-------------

@app.route('/book-ticket', methods=['POST'])
def book_ticket():
    try:
        data = request.get_json(force=True)

        user_id = data['user_id']
        train_id = data['train_id']
        ticket_type = data['ticket_type']   # Sleeper / AC / General
        seats_required = int(data['seats'])

        # Check available seats
        cursor.execute(
            "SELECT available_seats FROM trains WHERE train_id=%s",
            (train_id,)
        )
        result = cursor.fetchone()

        if not result:
            return jsonify({"message": "Train not found"}), 404

        available_seats = result[0]

        if available_seats < seats_required:
            return jsonify({"message": "Not enough seats available"}), 400

        # Insert booking
        cursor.execute(
            """
            INSERT INTO bookings (user_id, train_id, ticket_type, seats_booked)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, train_id, ticket_type, seats_required)
        )

        # Update seats
        cursor.execute(
            """
            UPDATE trains 
            SET available_seats = available_seats - %s
            WHERE train_id = %s
            """,
            (seats_required, train_id)
        )

        db.commit()

        return jsonify({"message": "Ticket booked successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    


#------------view a booked ticket-------------

@app.route('/my-bookings/<int:user_id>', methods=['GET'])
def my_bookings(user_id):
    cursor.execute(
        """
        SELECT b.booking_id, t.train_name, b.ticket_type, b.seats_booked, b.booking_time
        FROM bookings b
        JOIN trains t ON b.train_id = t.train_id
        WHERE b.user_id = %s
        """,
        (user_id,)
    )

    data = cursor.fetchall()

    bookings = []
    for row in data:
        bookings.append({
            "booking_id": row[0],
            "train_name": row[1],
            "ticket_type": row[2],
            "seats": row[3],
            "booking_time": str(row[4])
        })

    return jsonify({"bookings": bookings}), 200


#---------edit the train-------------

@app.route('/update-train/<int:train_id>', methods=['PUT'])
def update_train(train_id):
    try:
        data = request.get_json(force=True)

        train_name = data['train_name']
        train_type = data['train_type']
        source_city = data['source_city']
        destination_city = data['destination_city']
        departure_time = data['departure_time']
        arrival_time = data['arrival_time']
        total_seats = data['total_seats']
        available_seats = data['available_seats']

        cursor.execute("""
            UPDATE trains SET
            train_name=%s,
            train_type=%s,
            source_city=%s,
            destination_city=%s,
            departure_time=%s,
            arrival_time=%s,
            total_seats=%s,
            available_seats=%s
            WHERE train_id=%s
        """, (
            train_name, train_type, source_city, destination_city,
            departure_time, arrival_time, total_seats, available_seats,
            train_id
        ))

        db.commit()

        return jsonify({"message": "Train updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    

#-------cancle the train----------


@app.route('/delete-train/<int:train_id>', methods=['DELETE'])
def delete_train(train_id):
    try:
        # Step 1: Delete all bookings for this train
        cursor.execute(
            "DELETE FROM bookings WHERE train_id=%s",
            (train_id,)
        )

        # Step 2: Delete the train
        cursor.execute(
            "DELETE FROM trains WHERE train_id=%s",
            (train_id,)
        )

        db.commit()
        return jsonify({"message": "Train and all related bookings deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# ---------- RUN APP ----------
if __name__ == '__main__':
    app.run(debug=True)
