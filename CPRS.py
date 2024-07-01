import sqlite3
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from twilio.rest import Client

credentials = {
    "owner": {"username": "CPR", "password": "12345"}
}

conn = sqlite3.connect('cprs_database.db')
cursor = conn.cursor()


cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobileNumber TEXT,  -- Add this line to create the mobileNumber column
        email TEXT,
        username TEXT UNIQUE,
        password TEXT,
        dob TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        slot_name TEXT,
        start_time TEXT,
        FOREIGN KEY (username) REFERENCES users (username)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        activity TEXT,
        timestamp TEXT,
        FOREIGN KEY (username) REFERENCES users (username)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS parking_slots (
        slot_name TEXT PRIMARY KEY,
        status TEXT,
        color TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS slot_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_name TEXT,
        action TEXT,
        timestamp TEXT
    )
''')

conn.commit()

PRIMARY_COLOR = "#1565C0"  # Dark Blue
SECONDARY_COLOR = "#FFA000"  # Amber
BACKGROUND_COLOR = "#F5F5F5"  # Light Gray
BUTTON_COLOR = "#4CAF50"  # Green
ERROR_COLOR = "#FF5252"  # Red

parking_slots = {}
booking_info = {}
user_page = None
owner_page = None
current_user = None 
selected_slot = None
logout_button = None

def insert_user(name, email, username, password, dob, mobileNumber):  # Added mobileNumber parameter
    cursor.execute('''
        INSERT INTO users (name, email, username, password, dob, mobileNumber) VALUES (?, ?, ?, ?, ?, ?)  -- Added mobileNumber to the INSERT query
    ''', (name, email, username, password, dob, mobileNumber))  # Passed mobileNumber to the execute method
    conn.commit()


def insert_booking(username, slot_name, start_time):
    cursor.execute('''
        INSERT INTO bookings (username, slot_name, start_time) VALUES (?, ?, ?)
    ''', (username, slot_name, start_time))
    conn.commit()

def insert_user_activity(username, activity, timestamp):
    cursor.execute('''
        INSERT INTO user_activities (username, activity, timestamp) VALUES (?, ?, ?)
    ''', (username, activity, timestamp))
    conn.commit()

def initialize_slots():
    global parking_slots

    # Fetch slots from the database
    cursor.execute('SELECT slot_name, action FROM slot_changes')
    slot_changes = cursor.fetchall()

    # Update parking_slots based on slot changes
    for slot_name, action in slot_changes:
        if action == "add" and slot_name not in parking_slots:
            parking_slots[slot_name] = {"status": "free", "color": "green"}
        elif action == "delete" and slot_name in parking_slots:
            del parking_slots[slot_name]

    # Check for slots added during runtime and update the database
    for slot_name, slot_info in parking_slots.items():
        if slot_name not in [change[0] for change in slot_changes]:
            cursor.execute('''
                INSERT INTO slot_changes (slot_name, action, timestamp) VALUES (?, ?, ?)
            ''', (slot_name, "add", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Check for slots deleted during runtime and update the database
    for change in slot_changes:
        if change[0] not in parking_slots and change[1] == "add":
            cursor.execute('''
                DELETE FROM slot_changes WHERE slot_name = ?
            ''', (change[0],))

    conn.commit()

    # Schedule the next update after a delay (e.g., 10 seconds)
    root.after(10000, initialize_slots)



def update_slot_status(slot_name, status):
    cursor.execute('UPDATE parking_slots SET status = ? WHERE slot_name = ?', (status, slot_name))
    conn.commit()

# Function to update a slot's color in the database
def update_slot_color(slot_name, color):
    cursor.execute('UPDATE parking_slots SET color = ? WHERE slot_name = ?', (color, slot_name))
    conn.commit()

def send_bill_message(username, slot_name, start_time, end_time, cost):
    # Fetch the user's mobile number from the database
    cursor.execute('''
        SELECT mobile_number FROM users WHERE username = ?
    ''', (username,))
    mobile_number = cursor.fetchone()[0]  # Assuming the mobile number is stored in the 'mobile_number' column

    # Construct the message
    message = f"Dear {username},\nYour bill for slot {slot_name} is ${cost:.2f}.\nSlot booked from {start_time} to {end_time}.\nThank you for using CPRS!"

    # Initialize Twilio client with your Twilio account SID and auth token
    account_sid = "your_account_sid"
    auth_token = "your_auth_token"
    client = Client(account_sid, auth_token)

    try:
        # Send the message using Twilio
        message = client.messages.create(
            body=message,
            from_="your_twilio_phone_number",
            to=mobile_number
        )
        print("Bill message sent successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")

def login():
    global current_user
    username = username_entry.get()
    password = password_entry.get()
    user_type = user_type_var.get()

    cursor.execute('''
        SELECT * FROM users WHERE username = ? AND password = ? AND lower(username) = ?
    ''', (username, password, username.lower()))
    
    user_data = cursor.fetchone()

    if user_type == "user":
        cursor.execute('''
            SELECT * FROM users WHERE username = ? AND password = ? AND lower(username) = ?
        ''', (username, password, username.lower()))

        user_data = cursor.fetchone()

        if user_data:
            current_user = username  # Set the current user
            show_user_page(username)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")
    elif user_type == "owner":
        if username == credentials["owner"]["username"] and password == credentials["owner"]["password"]:
            current_user = username  # Set the current user
            show_owner_page()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

def show_signup_page():
    global signup_page
    root.withdraw() 

    signup_page = tk.Tk()
    signup_page.title("Sign Up")
    signup_page.geometry("400x300")
    signup_page.configure(bg=BACKGROUND_COLOR)
    
    tk.Label(signup_page, text="Name:", font=("Helvetica", 12), bg=BACKGROUND_COLOR).grid(row=0, column=0, pady=10, sticky="e")
    name_entry = tk.Entry(signup_page, font=("Helvetica", 12))
    name_entry.grid(row=0, column=1, pady=10)

    tk.Label(signup_page, text="Email:", font=("Helvetica", 12), bg=BACKGROUND_COLOR).grid(row=1, column=0, pady=10, sticky="e")
    email_entry = tk.Entry(signup_page, font=("Helvetica", 12))
    email_entry.grid(row=1, column=1, pady=10)

    tk.Label(signup_page, text="Username:", font=("Helvetica", 12), bg=BACKGROUND_COLOR).grid(row=2, column=0, pady=10, sticky="e")
    signup_username_entry = tk.Entry(signup_page, font=("Helvetica", 12))
    signup_username_entry.grid(row=2, column=1, pady=10)

    tk.Label(signup_page, text="Password:", font=("Helvetica", 12), bg=BACKGROUND_COLOR).grid(row=3, column=0, pady=10, sticky="e")
    signup_password_entry = tk.Entry(signup_page, show="*", font=("Helvetica", 12))
    signup_password_entry.grid(row=3, column=1, pady=10)

    tk.Label(signup_page, text="Date of Birth:", font=("Helvetica", 12), bg=BACKGROUND_COLOR).grid(row=4, column=0, pady=10, sticky="e")
    dob_entry = tk.Entry(signup_page, font=("Helvetica", 12))
    dob_entry.grid(row=4, column=1, pady=10)

    tk.Label(signup_page, text="Mobile Number:", font=("Helvetica", 12), bg=BACKGROUND_COLOR).grid(row=5, column=0, pady=10, sticky="e")
    mobile_entry = tk.Entry(signup_page, font=("Helvetica", 12))
    mobile_entry.grid(row=5, column=1, pady=10)


    def sign_up():
       name = name_entry.get()
       email = email_entry.get()
       username = signup_username_entry.get()
       password = signup_password_entry.get()
       dob = dob_entry.get()
       mobile = mobile_entry.get()

       try: 
         insert_user(name, email, username, password, dob, mobile)
         messagebox.showinfo("Sign Up Successful", "User signed up successfully.")
         signup_page.destroy()
         show_login_page()
       except sqlite3.IntegrityError:
          messagebox.showerror("Sign Up Failed", "Username already exists. Please choose a different username.")

    tk.Button(signup_page, text="Sign Up", command=sign_up, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=6, column=0, pady=(10, 20))

    def sign_in():
        signup_page.destroy()
        show_login_page()

    tk.Button(signup_page, text="Sign In", command=sign_in, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=6, column=1, pady=(10, 20))

    signup_page.mainloop()


    def sign_up():
       name = name_entry.get()
       email = email_entry.get()
       username = signup_username_entry.get()
       password = signup_password_entry.get()
       dob = dob_entry.get()
       mobile = mobile_entry.get()

       try: 
         insert_user(name, email, username, password, dob, mobile)
         messagebox.showinfo("Sign Up Successful", "User signed up successfully.")
         signup_page.destroy()
         show_login_page()
       except sqlite3.IntegrityError:
          messagebox.showerror("Sign Up Failed", "Username already exists. Please choose a different username.")


    tk.Button(signup_page, text="Sign Up", command=sign_up, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=0, pady=(10, 20))

    def sign_in():
        signup_page.destroy()
        show_login_page()

    tk.Button(signup_page, text="Sign In", command=sign_in, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=1, pady=(10, 20))

    signup_page.mainloop()

def show_user_page(username):
    global user_page, selected_slot, logout_button
    root.withdraw()  # Hide the login window

    user_page = tk.Tk()
    user_page.title("User Page")
    user_page.geometry("600x400")  # Increased size

    slots_frame = tk.Frame(user_page)
    slots_frame.grid(row=0, column=0, columnspan=len(parking_slots))

    display_slots(username, slots_frame)

    logout_button = tk.Button(user_page, text="Logout", command=logout_user, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF")
    logout_button.grid(row=1, column=0, columnspan=len(parking_slots), pady=(10, 20))

    user_page.protocol("WM_DELETE_WINDOW", logout_user)  # Handle window close event

    user_page.mainloop()

def display_slots(username, frame):
    tk.Label(frame, text="Slots for Parking", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=len(parking_slots), pady=(10, 5))

    for col_index, (slot_name, slot_info) in enumerate(parking_slots.items()):
        button = tk.Button(frame, text=slot_name, font=("Helvetica", 12), width=5, height=2, bg=slot_info["color"])
        button.grid(row=1, column=col_index, padx=10, pady=10)

        # Bind the select_slot function to the button
        button.bind("<Button-1>", lambda event, name=slot_name: select_slot(event, name))

    tk.Label(frame, text="Select a Slot for Booking", font=("Helvetica", 12)).grid(row=2, column=0, columnspan=len(parking_slots), pady=(10, 5))

    if selected_slot is not None and booking_info.get(selected_slot) is not None and username == booking_info[selected_slot]["username"]:
        generate_bill_button = tk.Button(frame, text="Generate Bill", command=lambda: generate_bill(username, selected_slot), font=("Helvetica", 12), width=15, height=2, bg="#FFA000")
        generate_bill_button.grid(row=3, column=0, columnspan=len(parking_slots), pady=(10, 20))

    tk.Button(frame, text="Show User Activities", command=lambda: show_user_activities(username), font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=4, column=0, columnspan=len(parking_slots), pady=(10, 20))

    def confirm_booking():
        global selected_slot
        if selected_slot is not None:
            if parking_slots[selected_slot]["status"] == "free":
                book_slot(username, selected_slot)
        else:
            messagebox.showinfo("Confirm Booking", "No slot selected for booking.")

    confirm_booking_button = tk.Button(frame, text="Confirm Booking", command=confirm_booking, font=("Helvetica", 12), width=15, height=2, bg="#2196F3")
    confirm_booking_button.grid(row=5, column=0, columnspan=len(parking_slots), pady=(10, 20))

def edit_booking():
    global selected_slot
    if selected_slot is not None:
        # If a different slot was previously selected, change its color back to green
        parking_slots[selected_slot]["color"] = "green"


def select_slot(event, slot_name):
    global selected_slot

    if selected_slot == slot_name:
        # If the same slot is clicked again, generate a bill
        generate_bill(username=booking_info[slot_name]["username"], slot_name=selected_slot)
        selected_slot = None  # Reset selected_slot to allow re-selection
    else:
        if selected_slot is not None:
            # If a different slot was previously selected, change its color back to green
            parking_slots[selected_slot]["color"] = "green"

        # Change the color of the newly selected slot to black if it's booked, otherwise change it to yellow
        if parking_slots[slot_name]["status"] == "booked":
            parking_slots[slot_name]["color"] = "black"
        else:
            parking_slots[slot_name]["color"] = "#FFEB3C"

        selected_slot = slot_name

        # Schedule a function call to change the slot color back to green after 1 minute
        root.after(60000, reset_slot_color, slot_name)

def reset_slot_color(slot_name):
    global selected_slot

    # Check if the selected slot is still the same
    if selected_slot == slot_name:
        # Change the color of the slot back to green
        parking_slots[slot_name]["color"] = "green"
        selected_slot = None


def book_slot(username, slot_name):
    global current_user
    if username in [info["username"] for info in booking_info.values()]:
        messagebox.showerror("Booking Error", "You already have a booked slot. Please pay the bill before booking another slot.")
        return

    parking_slots[slot_name]["status"] = "booked"
    parking_slots[slot_name]["color"] = "red"
    booking_info[slot_name] = {"username": username, "start_time": datetime.now()}

    # Insert the booking information into the database
    insert_booking(username, slot_name, booking_info[slot_name]["start_time"].strftime('%Y-%m-%d %H:%M:%S'))

    # Insert user activity into the database
    activity = f"Booked slot {slot_name}"
    insert_user_activity(username, activity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    messagebox.showinfo("Slot Booked", f"Slot {slot_name} booked successfully.")

    # Clear the existing content in the user page
    for widget in user_page.winfo_children():
        widget.destroy()

    # Display slots again with updated information
    display_slots(username, user_page)

    # Place the logout button again
    logout_button.grid(row=4, column=0, columnspan=len(parking_slots) + 1, pady=(10, 20))

    # if username == booking_info[slot_name]["username"]:
    #     # Add button for the owner to view billing details
    #     generate_bill_button = tk.Button(user_page, text="Generate Bill", command=lambda: generate_bill(username, selected_slot), font=("Helvetica", 12), width=15, height=2, bg="#FFA000")
    #     generate_bill_button.grid(row=5, column=0, columnspan=len(parking_slots), pady=(10, 20))

def calculate_billing(start_time):
    end_time = datetime.now()
    duration = end_time - start_time
    minutes = duration.total_seconds() // 60
    cost = minutes * 1  # $1 per minute
    return cost

def generate_bill(username, slot_name):
    global current_user

    if current_user == username:
        if slot_name in booking_info:
            start_time = booking_info[slot_name]["start_time"]
            end_time = datetime.now()
            elapsed_time = end_time - start_time
            minutes = elapsed_time.total_seconds() // 60
            cost = calculate_billing(start_time)

            # Insert user activity into the database
            activity = f"Generated bill for slot {slot_name}"
            insert_user_activity(username, activity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            # Send the bill message
            send_bill_message(username, slot_name, start_time, end_time, cost)

            # Create a new window for displaying the bill
            bill_window = tk.Toplevel()
            bill_window.title("Bill Information")
            bill_window.geometry("400x200")

            # Display bill information in the new window
            tk.Label(bill_window, text=f"Slot {slot_name} Bill", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))
            tk.Label(bill_window, text=f"Booked Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", font=("Helvetica", 12)).grid(row=1, column=0, columnspan=2)
            tk.Label(bill_window, text=f"Released Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}", font=("Helvetica", 12)).grid(row=2, column=0, columnspan=2)
            tk.Label(bill_window, text=f"Duration: {int(minutes)} minutes", font=("Helvetica", 12)).grid(row=3, column=0, columnspan=2)
            tk.Label(bill_window, text=f"Billing Amount: ${cost:.2f}", font=("Helvetica", 12)).grid(row=4, column=0, columnspan=2)

            # Change the color of the booked slot to green after generating the bill
            parking_slots[slot_name]["status"] = "free"
            parking_slots[slot_name]["color"] = "green"

            # Update the user_page content
            update_user_page_content(username)

            # Remove the slot from booking_info
            del booking_info[slot_name]

        else:
            messagebox.showinfo("Generate Bill", "No booking found for the selected slot.")
    else:
        messagebox.showinfo("Generate Bill", "You can only generate a bill for your booked slot.")

def show_user_activities(username):
    # Fetch user activities from the database for the current user
    cursor.execute('''
        SELECT * FROM user_activities WHERE username = ? ORDER BY timestamp DESC
    ''', (username,))
    activities = cursor.fetchall()

    # Create a new window for displaying user activities
    user_activities_window = tk.Toplevel()
    user_activities_window.title("User Activities")
    user_activities_window.geometry("600x400")

    # Add a label for the title
    tk.Label(user_activities_window, text=f"Activities for User: {username}", font=("Helvetica", 14, "bold")).pack(pady=(10, 5))

    # Create a text widget to display activities
    activity_text = tk.Text(user_activities_window, font=("Helvetica", 12), wrap="word")
    activity_text.pack(expand=True, fill="both")

    # Insert activities into the text widget
    for activity_info in activities:
        timestamp = activity_info[3]  # Access timestamp using index 3
        activity = activity_info[2]  # Access activity using index 2
        activity_text.insert(tk.END, f"{timestamp}: {activity}\n")

    # Disable editing in the text widget
    activity_text.config(state=tk.DISABLED)

    # Close the user activities window when the "Close" button is clicked
    close_button = tk.Button(user_activities_window, text="Close", command=user_activities_window.destroy, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF")
    close_button.pack(pady=(10, 20))

def update_user_page_content(username):
    global user_page, selected_slot, logout_button

    # Clear the existing content
    for widget in user_page.winfo_children():
        widget.destroy()

    slots_frame = tk.Frame(user_page)
    slots_frame.grid(row=0, column=0, columnspan=len(parking_slots))

    display_slots(username, slots_frame)

    # Check if the user has a booked slot
    if any(info["username"] == username for info in booking_info.values()):

        logout_button = tk.Button(user_page, text="Logout", command=logout_user, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF")
        logout_button.grid(row=4, column=0, columnspan=len(parking_slots), pady=(10, 20))

    user_page.protocol("WM_DELETE_WINDOW", logout_user)  # Handle window close event

def logout_user():
    global user_page

    if any(info["username"] == current_user for info in booking_info.values()):
        messagebox.showinfo("Logout Error", "Please generate the bill for your booked slot before logging out.")
    else:
        answer = messagebox.askquestion("Logout", "Are you sure you want to logout?")
        if answer == "yes":
            user_page.destroy()
            show_login_page()


def show_owner_page():
    global owner_page, entry_delete_slots

    root.withdraw()  # Hide the login window

    owner_page = tk.Tk()
    owner_page.title("Owner Page")
    owner_page.geometry("600x400")  # Increased size

    if not parking_slots:
        messagebox.showinfo("Add Parking Slots", "It seems there are no parking slots. Please add parking slots.")
        add_parking_slots()

    # Display available slots
    display_owner_slots()
    
    # Buttons for owner actions
    tk.Button(owner_page, text="Edit Slots", command=edit_slots, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=0, pady=(10, 20))
    tk.Button(owner_page, text="Logout", command=logout_owner, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=2, pady=(10, 20))

    owner_page.mainloop()

def add_parking_slots():
    add_slots_entry = tk.Entry(owner_page, font=("Helvetica", 12))
    add_slots_entry.grid(row=3, column=0, pady=(10, 5))
    
    def save_and_display_added_slots():
        try:
            num_slots = int(add_slots_entry.get())
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for i in range(len(parking_slots) + 1, len(parking_slots) + num_slots + 1):
                slot_name = f"A{i}"
                parking_slots[slot_name] = {"status": "free", "color": "green"}

                # Insert into slot_changes table
                cursor.execute('''
                    INSERT INTO slot_changes (slot_name, action, timestamp) VALUES (?, ?, ?)
                ''', (slot_name, "add", timestamp))

            conn.commit()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for slots.")

        # Refresh the owner page after adding slots
        display_owner_slots()

    tk.Button(owner_page, text="Add Slots", command=save_and_display_added_slots, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=3, column=1, pady=(10, 20))

def display_owner_slots():
    # Clear the existing content
    for widget in owner_page.winfo_children():
        widget.destroy()

    tk.Label(owner_page, text="Slots for Parking", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=len(parking_slots) + 1, pady=(10, 5))

    for col_index, (slot_name, slot_info) in enumerate(parking_slots.items()):
        tk.Label(owner_page, text=slot_name, font=("Helvetica", 12), width=5, height=2, bg=slot_info["color"]).grid(row=1, column=col_index, padx=10, pady=10)

    tk.Label(owner_page, text="Booking Information", font=("Helvetica", 12)).grid(row=2, column=0, columnspan=max(1, len(parking_slots)), pady=(10, 5))

    for col_index, (slot_name, slot_info) in enumerate(parking_slots.items()):
        if slot_info["status"] == "booked" and slot_name in booking_info:
            booking_details = booking_info[slot_name]
            tk.Label(owner_page, text=f"Slot {slot_name}: {booking_details['username']} | Start Time: {booking_details['start_time']}", font=("Helvetica", 10)).grid(row=3, column=col_index, padx=10, pady=5)

    # Buttons for owner actions
    tk.Button(owner_page, text="Edit Slots", command=edit_slots, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=0, pady=(10, 20))
    tk.Button(owner_page, text="Logout", command=logout_owner, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=2, pady=(10, 20))

    

def add_slots():
    global edit_slots_entry

    try:
        # Retrieve the entry widget inside the function to get the updated value
        add_slots_entry = edit_slots_entry

        num_slots = int(add_slots_entry.get())
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for i in range(len(parking_slots) + 1, len(parking_slots) + num_slots + 1):
            slot_name = f"A{i}"
            parking_slots[slot_name] = {"status": "free", "color": "green"}

            # Insert into slot_changes table
            cursor.execute('''
                INSERT INTO slot_changes (slot_name, action, timestamp) VALUES (?, ?, ?)
            ''', (slot_name, "add", timestamp))

        conn.commit()
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for slots.")

    # Refresh the owner page after adding slots
    display_owner_slots()


def delete_slots():
    global parking_slots, edit_slots_entry
    try:
        num_slots = int(edit_slots_entry.get())

        if num_slots > 0 and num_slots <= len(parking_slots):
            removed_slots = list(parking_slots.keys())[-num_slots:]
            for slot_name in removed_slots:
                # Update the color in the database before deleting
                update_slot_color(slot_name, "red")

                # Delete the slot from the database
                cursor.execute('''
                    DELETE FROM parking_slots WHERE slot_name = ?
                ''', (slot_name,))

                # Delete the slot from the dictionary
                del parking_slots[slot_name]

                # Insert into slot_changes table
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    INSERT INTO slot_changes (slot_name, action, timestamp) VALUES (?, ?, ?)
                ''', (slot_name, "delete", timestamp))

            conn.commit()  # Add this line to commit the changes to the database

            # Refresh the owner page after deleting the slots
            display_owner_slots()
        else:
            messagebox.showinfo("Invalid Input", "Please enter a valid number of slots to delete.")
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for slots.")


def edit_slots():
    global edit_slots_entry

    # Destroy any existing entry widgets
    if "edit_slots_entry" in locals():
        edit_slots_entry.destroy()

    # Entry for number of slots to add or delete
    tk.Label(owner_page, text="Enter number of slots to edit:", font=("Helvetica", 12)).grid(row=4, column=0, columnspan=2, pady=(10, 5))
    edit_slots_entry = tk.Entry(owner_page, font=("Helvetica", 12))
    edit_slots_entry.grid(row=4, column=2, pady=(10, 5))

    # Buttons for owner actions
    tk.Button(owner_page, text="Add Slots", command=add_slots, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=0, pady=(10, 20))
    
    # Add the "Delete Slots" button and bind it to the delete_slots function
    tk.Button(owner_page, text="Delete Slots", command=delete_slots, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF").grid(row=5, column=1, pady=(10, 20))

def save_edited_slots():
    global edit_slots_entry
    try:
        num_slots_change = int(edit_slots_entry.get())
        current_num_slots = len(parking_slots)

        if num_slots_change > 0:
            for i in range(current_num_slots + 1, current_num_slots + num_slots_change + 1):
                slot_name = f"A{i}"
                parking_slots[slot_name] = {"status": "free", "color": "green"}
        elif num_slots_change < 0:
            removed_slots = list(parking_slots.keys())[current_num_slots + num_slots_change:]
            for slot_name in removed_slots:
                del parking_slots[slot_name]
        else:
            messagebox.showinfo("Slots Edited", "No changes made.")
            return

        messagebox.showinfo("Slots Edited", f"{abs(num_slots_change)} slots {'added' if num_slots_change > 0 else 'removed'} successfully.")

        # Refresh the owner page after editing slots
        display_owner_slots()
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for slots.")

def logout_owner():
    global owner_page
    answer = messagebox.askquestion("Logout", "Are you sure you want to logout?")
    if answer == "yes":
        owner_page.destroy()
        show_login_page()

def show_login_page():
    root.deiconify()  # Show the main window
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)

# Create the main window
root = tk.Tk()
root.title("CPRS Login")
root.geometry("500x450")  # Initial size
root.configure(bg=BACKGROUND_COLOR)
frame = tk.Frame(root, bg=BACKGROUND_COLOR)
frame.place(relx=0.5, rely=0.5, anchor="center")
# Create and place widgets in the frame 
heading_label = tk.Label(frame, text="CPRS", font=("Helvetica", 24, "bold"), bg=BACKGROUND_COLOR, fg=PRIMARY_COLOR)
heading_label.grid(row=0, column=0, columnspan=2, pady=(20, 10)) 
username_label = tk.Label(frame, text="Username:", font=("Helvetica", 12), bg=BACKGROUND_COLOR, fg=PRIMARY_COLOR)
username_label.grid(row=1, column=0, pady=(10, 5), sticky="e") 
username_entry = tk.Entry(frame, font=("Helvetica", 12)) 
username_entry.grid(row=1, column=1, pady=(10, 5)) 
password_label = tk.Label(frame, text="Password:", font=("Helvetica", 12), bg=BACKGROUND_COLOR, fg=PRIMARY_COLOR)
password_label.grid(row=2, column=0, pady=(5, 10), sticky="e") 
password_entry = tk.Entry(frame, show="*", font=("Helvetica", 12))
password_entry.grid(row=2, column=1, pady=(5, 10)) 
user_type_var = tk.StringVar() 
user_type_var.set("user") 
# Default selection 
user_radio = tk.Radiobutton(frame, text="User", variable=user_type_var, value="user", font=("Helvetica", 12), bg=BACKGROUND_COLOR, fg=PRIMARY_COLOR)
user_radio.grid(row=3, column=0, pady=(10, 5), sticky="e") 
owner_radio = tk.Radiobutton(frame, text="Owner", variable=user_type_var, value="owner", font=("Helvetica", 12), bg=BACKGROUND_COLOR, fg=PRIMARY_COLOR)
owner_radio.grid(row=3, column=1, pady=(10, 5), sticky="w") 
login_button = tk.Button(frame, text="Login", command=login, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF")
login_button.grid(row=4, column=0, columnspan=2, pady=(10, 20))
signup_button = tk.Button(frame, text="Sign Up", command=show_signup_page, font=("Helvetica", 12), bg=BUTTON_COLOR, fg="#FFFFFF")
signup_button.grid(row=5, column=0, columnspan=2, pady=(0, 20)) 
win_width = 500 
win_height = 400 
screen_width = root.winfo_screenwidth() 
screen_height = root.winfo_screenheight() 
x = (screen_width - win_width) // 2 
y = (screen_height - win_height) // 2 
root.geometry(f"{win_width}x{win_height}+{x}+{y}") 
initialize_slots()
root.protocol("WM_DELETE_WINDOW", lambda: [conn.close(), root.destroy()])
root.mainloop()