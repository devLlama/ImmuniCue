import json
import googlemaps
import datetime
import time

CURRENT_DATE = datetime.date.today()

#Change these variables to match your setup.
GOOGLE_MAPS_API_KEY = ""
VACCINES_PATH = ""
GOVERNMENT_PATH = ""
OUTPUT_JSON_PATH = ""
NOTIFICATIONS_JSON_PATH = ""

#This function takes in a person's date of birth and the current date and outputs their age.
def calculate_age(dob, current_date):
    dob_components = dob.split('/')
    birth_month = int(dob_components[0])
    birth_day = int(dob_components[1])
    birth_year = int(dob_components[2])

    age = current_date.year - birth_year - 1
    if (birth_month < current_date.month) or (birth_month == current_date.month and birth_day <= current_date.day):
        age += 1
    return age

#Takes in a person's date of birth and a target age and outputs the date of the birthday that will make them the target age.
#Ex: A date of birth or 01/01/2000 and target_age of 20 will output 01/01/2020 because that persons 20th birtday is on 01/01/2020.
def calculate_specific_birthday(dob, target_age):
    dob_components = dob.split('/')
    birth_month = int(dob_components[0])
    birth_day = int(dob_components[1])
    birth_year = int(dob_components[2])
    target_year = birth_year + target_age
    return f"{birth_month}/{birth_day}/{target_year}"

#Takes in a person's address and outputs the hospital that is closest to them.
def get_closest_hospital(address):
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    geocode_result = gmaps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        latitude = location['lat']
        longitude = location['lng']
        #Queries up hospitals near the inputted adress.
        places_result = gmaps.places_nearby(
            location=(latitude, longitude),
            rank_by='distance',
            type='hospital'
        )
        if places_result['results']:
            closest_hospital = places_result['results'][0]
            hospital_name = closest_hospital['name']
            hospital_address = closest_hospital['vicinity']
            hospital_lat = closest_hospital['geometry']['location']['lat']
            hospital_lng = closest_hospital['geometry']['location']['lng']
            distance_result = gmaps.distance_matrix(
                origins=(latitude, longitude),
                destinations=(hospital_lat, hospital_lng),
                mode='driving'
            )
            if distance_result['rows'][0]['elements'][0]['status'] == 'OK':
                distance = distance_result['rows'][0]['elements'][0]['distance']['text']
            else:
                distance = "N/A"
        else:
            hospital_name = hospital_address = distance = "N/A"
    else:
        hospital_name = hospital_address = distance = "N/A"
    return hospital_name, hospital_address, distance

#Reads the government data file, parses it and adds somemore information. This is then saved as a .json
def proccess_input_and_write_to_json():
    government_data = []
    with open(GOVERNMENT_PATH) as government_file:
        data = government_file.readlines()
        for line in data:
            name, DOB, address, phone_number = line.split("\t")
            age = calculate_age(DOB, CURRENT_DATE)
            hospital_info = get_closest_hospital(address)
            government_data.append({
                "name": name,
                "DOB": DOB,
                "address": address,
                "phone_number": phone_number.replace("\n", ""),
                "age": age,
                "hospital_info": hospital_info
            })
    with open(OUTPUT_JSON_PATH, "w") as json_file:
        json.dump(government_data, json_file, indent=4)
    print(f"Data has been written to {OUTPUT_JSON_PATH}")

#Turns a .json file and converts it to an array.
def read_data_from_json():
    with open(OUTPUT_JSON_PATH, "r") as json_file:
        loaded_data = json.load(json_file)
    return loaded_data

#Reads the vaccine data file and converts it into an array.
vaccine_data = []
with open(VACCINES_PATH) as vaccines_file:
    data = vaccines_file.readlines()
    for line in data:
        age, vaccine = line.split("\t")
        vaccine_data.append([age, vaccine.replace("\n", "")])
    vaccine_data = vaccine_data[:-1]

#Takes in a persons birthday as a string and gets the date 2 weeks after and outputs it. This is used as the date that the reminder is sent.
def calculate_reminder_date(birthday_str):
    birthday_components = birthday_str.split("/")
    birthday_date = datetime.date(int(birthday_components[2]), int(birthday_components[0]), int(birthday_components[1]))
    reminder_date = birthday_date + datetime.timedelta(weeks=2)
    return reminder_date

#Uses all the info that is inputted and generates a schedule of when to send messages and of what to put in them. This is then put into a .json file.
def generate_vaccine_notifications():
    notifications = []
    people_data = read_data_from_json()
    for person in people_data:
        name = person["name"]
        dob = person["DOB"]
        age = person["age"]
        phone_number = person["phone_number"]
        hospital_info = person["hospital_info"]
        hospital_name = hospital_info[0]
        hospital_address = hospital_info[1]
        distance = hospital_info[2]

        vaccines_needed = []
        for vaccine in vaccine_data:
            vaccine_age = int(vaccine[0])
            if vaccine_age > age:  # Only future vaccines
                birthday_for_vaccine = calculate_specific_birthday(dob, vaccine_age)
                reminder_date = calculate_reminder_date(birthday_for_vaccine).strftime('%m/%d/%Y')
                vaccines_needed.append({
                    "vaccine_name": vaccine[1],
                    "required_age": vaccine_age,
                    "reminder_date": reminder_date,
                    "birthday_for_vaccine": birthday_for_vaccine
                })

        # Create the notification dictionary
        notification = {
            "name": name,
            "phone_number": phone_number,
            "current_age": age,
            "vaccines": vaccines_needed if vaccines_needed else [],  # Empty list if no vaccines
            "hospital": {
                "name": hospital_name,
                "address": hospital_address,
                "distance": distance
            }
        }
        notifications.append(notification)

    # Write the notifications array to a JSON file
    with open(NOTIFICATIONS_JSON_PATH, "w") as json_file:
        json.dump(notifications, json_file, indent=4)
    print(f"Notifications have been written to {NOTIFICATIONS_JSON_PATH}")

    return notifications

#Takes the notification .json and articulates the data into real messages that can be sent out.
#The data from the JSON can be used with an SMS messaging service to send real SMS messages to people.
#Instead of using an SMS system I created this function to print out the messsages into the python output window.
def print_notifications_from_schedule():
    # Read the notifications from the JSON file
    with open(NOTIFICATIONS_JSON_PATH, "r") as json_file:
        notifications = json.load(json_file)

    # Print each notification in a human-readable format with the new message structure
    for notification in notifications:
        print(f"Phone: {notification['phone_number']}")

        if notification['vaccines']:
            for vaccine in notification['vaccines']:
                print(f"Send Date: {vaccine['reminder_date']}")
                print(f"Dear {notification['name']},")
                print(
                    f"This is a friendly reminder that your {vaccine['vaccine_name']} vaccine "
                    f"is recommended at age {vaccine['required_age']}.\n"
                    f"Please schedule your vaccination soon.\n"
                )
                print(
                    f"We recommend visiting your nearest hospital:\n"
                    f" - Hospital: {notification['hospital']['name']}\n"
                    f" - Address: {notification['hospital']['address']}\n"
                    f" - Distance: {notification['hospital']['distance']}\n"
                    f"Stay healthy and take care!\n"
                )

            print("-" * 50)


# Configuration 1: Comment out configuration 2 and use configuration 1 if you don't already have the government data encoded into a .json file.
proccess_input_and_write_to_json()
notifications_array = generate_vaccine_notifications()
print_notifications_from_schedule()

# Configuration 2: Comment out configuration 1 and use configuration 2 if you already have the government data encoded into a .json file.
notifications_array = generate_vaccine_notifications()
print_notifications_from_schedule()