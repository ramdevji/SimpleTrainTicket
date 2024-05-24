from sanic import Sanic, response
from sanic.request import Request
from sanic_ext import openapi
from datetime import datetime, timedelta
import asyncio

app = Sanic("TrainBookingSystem")

# due to time constraint (to setup database) i am using in memory ram storage
# we can use any database storage technique like rdms/nosql
trains = []
bookings = []
email_duration = 30


# dummy email sending function
async def send_email(to_email, subject, body):
    # here we can use third party system to send mails.
    return


async def schedule_email(booking):
    time_to_departure = booking["departure_time"] - datetime.now()
    send_time = time_to_departure - timedelta(minutes=email_duration)
    if send_time.total_seconds() > 0:
        await send_reminder(booking)


async def send_reminder(booking):
    email_subject = "Train Departure Reminder"
    email_body = (f"Dear {booking['passenger_name']},\nYour train {booking['train_name']} "
                  f"is scheduled to depart "
                  f"at {booking['departure_time']}. Your seat number "
                  f"is {booking['seat_number']}.")
    await send_email(booking["email"], email_subject, email_body)


def find_train(train_id):
    for train in trains:
        if train["train_id"] == train_id:
            return train
    return None


@app.route("/trains", methods=["POST"])
@openapi.body({"application/json": {"name": str, "seats": int, "departure_time": str}})
async def add_train(request: Request):
    data = request.json
    train_id = len(trains) + 1
    train = {
        "train_id": train_id,
        "name": data["name"],
        "seats": data["seats"],
        "available_seats": data["seats"],
        "departure_time": datetime.fromisoformat(data["departure_time"])
    }
    trains.append(train)
    return response.json({"message": "Train added successfully", "train": train}, status=201)


@app.route("/trains", methods=["GET"])
async def get_trains(request):
    return response.json(trains)


@app.route("/book", methods=["POST"])
@openapi.body({"application/json": {"train_id": int, "passenger_name": str, "email": str, "seats": int}})
async def book_ticket(request: Request):
    data = request.json
    train_id = data.get("train_id")
    passenger_name = data.get("passenger_name")
    email = data.get("email")
    seats = data.get("seats", 1)

    train = find_train(train_id)
    if not train:
        return response.json({"error": "Train not found"}, status=404)

    if train["available_seats"] < seats:
        return response.json({"error": "Not enough seats available"}, status=400)

    train["available_seats"] -= seats
    booking_id = len(bookings) + 1
    seat_number = train["seats"] - train["available_seats"] + 1
    booking = {
        "booking_id": booking_id,
        "train_id": train_id,
        "train_name": train["name"],
        "passenger_name": passenger_name,
        "email": email,
        "seats": seats,
        "seat_number": seat_number,
        "departure_time": train["departure_time"]
    }
    bookings.append(booking)

    # send emails - this can be run in background
    await asyncio.create_task(schedule_email(booking))

    return response.json({"message": "Booking successful", "booking": booking}, status=201)


@app.route("/bookings", methods=["GET"])
async def get_bookings(request):
    return response.json(bookings)


@app.route("/booking/<booking_id:int>", methods=["GET"])
async def get_booking(request, booking_id):
    for booking in bookings:
        if booking["booking_id"] == booking_id:
            return response.json(booking)
    return response.json({"error": "Booking not found"}, status=404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
