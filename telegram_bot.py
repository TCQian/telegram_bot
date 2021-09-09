from telegram.ext import Updater, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
import gspread
from oauth2client.service_account import ServiceAccountCredentials

sheet1 = "Attendance list"
sheet2 = "Timeslot availability"
"""
col = sheet.col_values(int)
row = sheet.row_values(int)
cell = sheet.cell(1,2).value
insertRow = [..., ..., ...]
sheet.insert_row(insertRow, 4)
sheet.delete_row(int)
sheet.update_cell(int, int, "...")
"""

OPTION, REGISTER, SELECT_TIMESLOT, SELECTED, UPDATE, UPDATE_ID = range(6)

def start(update, context):
    """Send a message when the command /start is issued."""
    reply = "Hi, what would you like to do?"
    reply_keyboard = [['Register', 'Update Student ID or Selected Time Slots', 'Check My Selected Time Slots']]
    update.message.reply_text(reply, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return OPTION

def option(update, context):
    user_reply = update.message.text
    student_name = update.message.chat.username

    if user_reply == "Register":
        update.message.reply_text(
            "Please provide your student ID!",
            reply_markup=ReplyKeyboardRemove()
        )
        return REGISTER

    elif user_reply == 'Update Student ID or Selected Time Slots':
        reply_keyboard = [['Student ID', 'Activity Time Slots']]
        update.message.reply_text(
            "What do you want to update?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return UPDATE
    else:
        # must have at least 1 activity
        name_col = sheet1.col_values(1)
        for i in range(1, len(name_col)): # 1, 2
            if name_col[i] == student_name:
                row_index = i + 1
                activity_row = sheet1.row_values(1)
                timeslot_row = sheet1.row_values(row_index)
                reply_format = ""
                for j in range(2, len(activity_row)):
                    if j >= len(timeslot_row) or timeslot_row[j] == "":
                        reply_format += activity_row[j] + ": Not yet selected\n"
                    else:
                        reply_format += activity_row[j] + ": " + timeslot_row[j] + "\n"

                update.message.reply_text("Here's your selected timeslots:\n" + reply_format, reply_markup=ReplyKeyboardRemove())
                return ConversationHandler.END

        update.message.reply_text(
            "You have yet to register your student ID! Please do so using the /start command",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

def update_id_or_timeslot(update, context):
    user_reply = update.message.text
    if user_reply == "Student ID":
        update.message.reply_text(
            "Please provide your student ID!",
            reply_markup=ReplyKeyboardRemove()
        )
        return UPDATE_ID

    else:
        # get activities
        activity_col = sheet2.col_values(1)
        activity_keyboard = []
        for i in range(1, len(activity_col)):
            if activity_col[i] != '':
                activity_keyboard.append([InlineKeyboardButton(activity_col[i], callback_data=str(i))]) # I use the index starting point of timeslot
        activity_keyboard.append([InlineKeyboardButton("I'm Done :D", callback_data="DONE")])
        reply_markup = InlineKeyboardMarkup(activity_keyboard)

        # prompt user to select which activitiy to choose
        update.message.reply_text(
            "Please choose an activity to select it's time slot",
            reply_markup=reply_markup
        )
        return SELECT_TIMESLOT

def update_id(update, context):
    student_id = update.message.text
    student_name = update.message.chat.username
    update.message.reply_text("Re-registering...")

    name_col = sheet1.col_values(1) # ["name", "student1", "student2"]
    student_id_col = sheet1.col_values(2)

    for i in range(1, len(name_col)): # 1, 2
        if name_col[i] == student_name:
            sheet1.update_cell(i + 1, 2, student_id)
            update.message.reply_text("Registered!")
            return ConversationHandler.END

    update.message.reply_text("You have yet to register your student ID...")
    return ConversationHandler.END

def register(update, context):
    """register for student number"""
    student_id = update.message.text
    student_name = update.message.chat.username

    update.message.reply_text("Registering...")

    name_col = sheet1.col_values(1) # ["name", "student1", "student2"]
    student_id_col = sheet1.col_values(2)
    to_update_or_not = True
    for i in range(1, len(name_col)): # 1, 2
        if name_col[i] == student_name:
            to_update_or_not = False
            break

    # insert into google sheet
    if to_update_or_not:
        sheet1.insert_row([student_name, student_id], len(name_col) + 1)
        update.message.reply_text("Registered!")
    else:
        update.message.reply_text("You have already registered your student ID!")

    # get activities
    activity_col = sheet2.col_values(1)
    activity_keyboard = []
    for i in range(1, len(activity_col)):
        if activity_col[i] != '':
            activity_keyboard.append([InlineKeyboardButton(activity_col[i], callback_data=str(i))]) # I use the index starting point of timeslot
    activity_keyboard.append([InlineKeyboardButton("I'm Done :D", callback_data="DONE")])
    reply_markup = InlineKeyboardMarkup(activity_keyboard)

    # prompt user to select which activitiy to choose
    update.message.reply_text(
        "Please choose an activity to select it's time slot",
        reply_markup=reply_markup
    )
    return SELECT_TIMESLOT

def select_timeslot(update, context):
    if update.callback_query.data == "DONE":
        update.callback_query.edit_message_text("Thank you! Have a good day :)")
        return ConversationHandler.END

    selected_activity_index = int(update.callback_query.data)
    selected_activity = sheet2.col_values(1)[selected_activity_index]
    number_of_timeslot = int(sheet2.col_values(2)[selected_activity_index])
    timeslot_keyboard = []
    timeslot_col = sheet2.col_values(3)
    capacity_col = sheet2.col_values(4)
    for i in range(selected_activity_index, selected_activity_index + number_of_timeslot):
        timeslot = timeslot_col[i]
        capacity = capacity_col[i]
        if int(capacity) < 20:
            button = timeslot + ": left " + str(20 - int(capacity))
            timeslot_keyboard.append([InlineKeyboardButton(button, callback_data=str(str(selected_activity_index) + " " + selected_activity + " " + timeslot))])

    reply_markup = InlineKeyboardMarkup(timeslot_keyboard)
    message_reply_text = 'Select one of the timing options'
    update.callback_query.edit_message_text(message_reply_text, reply_markup=reply_markup)

    return SELECTED

def selected(update, context):
    student_name = update.callback_query.message.chat.username
    name_col = sheet1.col_values(1)
    data = update.callback_query.data.split(" ")
    selected_activity_sheet2_index = int(data[0])
    selected_activity = data[1]
    selected_timeslot = data[2]
    selected_activity_col_index = sheet1.row_values(1).index(selected_activity) + 1
    for i in range(1, len(name_col)):
        if name_col[i] == student_name:
            if sheet1.cell(i + 1, selected_activity_col_index).value != None:
                update.callback_query.edit_message_text("Previous time slot: " + sheet1.cell(i + 1, selected_activity_col_index).value + " for activity " + selected_activity + " has already been selected.")
                update.callback_query.message.reply_text("Updating your new selection...")
                old_time_slot = sheet1.cell(i + 1, selected_activity_col_index).value
                if increment_capacity(selected_activity_sheet2_index, selected_timeslot):
                    decrement_capacity(selected_activity_sheet2_index, old_time_slot)
                    sheet1.update_cell(i + 1, selected_activity_col_index, selected_timeslot)
                    update.callback_query.message.reply_text("Done! Time slot: " + selected_timeslot + " registered!")
                else:
                    update.callback_query.message.reply_text("Sorry, the time slot is full")

            else:
                if increment_capacity(selected_activity_sheet2_index, selected_timeslot):
                    sheet1.update_cell(i + 1, selected_activity_col_index, selected_timeslot)
                    update.callback_query.edit_message_text("Done! Time slot: " + selected_timeslot + " registered!")
                else:
                    update.callback_query.edit_message_text("Sorry, the time slot is full.")

            # get activities
            activity_col = sheet2.col_values(1)
            activity_keyboard = []
            for i in range(1, len(activity_col)):
                if activity_col[i] != '':
                    activity_keyboard.append([InlineKeyboardButton(activity_col[i], callback_data=str(i))]) # I use the index starting point of timeslot
            activity_keyboard.append([InlineKeyboardButton("I'm Done :D", callback_data="DONE")])
            reply_markup = InlineKeyboardMarkup(activity_keyboard)

            # prompt user to select which activitiy to choose
            update.callback_query.message.reply_text(
                "Please choose an activity to select it's time slot",
                reply_markup=reply_markup
            )

            return SELECT_TIMESLOT

    # user pressed update at /start ... what a dumbass
    update.callback_query.edit_message_text("Please register your student ID first!")
    return ConversationHandler.END

def increment_capacity(selected_activity_sheet2_index, timeslot):
    timeslot_col = sheet2.col_values(3)
    capacity_col = sheet2.col_values(4)
    number_of_timeslots = int(sheet2.col_values(2)[selected_activity_sheet2_index])
    for i in range(selected_activity_sheet2_index, selected_activity_sheet2_index + number_of_timeslots):
        if timeslot_col[i] == timeslot and int(capacity_col[i]) < 20:
            capacity = int(capacity_col[i]) + 1
            sheet2.update_cell(i + 1, 4, str(capacity))
            return True
    return False

def decrement_capacity(selected_activity_sheet2_index, timeslot):
    timeslot_col = sheet2.col_values(3)
    capacity_col = sheet2.col_values(4)
    number_of_timeslots = int(sheet2.col_values(2)[selected_activity_sheet2_index])
    for i in range(selected_activity_sheet2_index, selected_activity_sheet2_index + number_of_timeslots):
        if timeslot_col[i] == timeslot:
            capacity = int(capacity_col[i]) - 1
            sheet2.update_cell(i + 1, 4, str(capacity))
            return

# default answer
def default(update, context):
    update.message.reply_text("Hi, please use /start to interact with me :)")
    return ConversationHandler.END

def main():
    updater = Updater('1663709573:AAFMIo2C0k6v1yqOi6NHbe85JINNUsfveDA')
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            OPTION: [MessageHandler(Filters.regex('^(Register|Update Student ID or Selected Time Slots|Check My Selected Time Slots)$'), option)],
            UPDATE: [MessageHandler(Filters.regex('^(Student ID|Activity Time Slots)$'), update_id_or_timeslot)],
            UPDATE_ID: [MessageHandler(Filters.all, update_id)],
            REGISTER: [MessageHandler(Filters.all, register)],
            SELECT_TIMESLOT: [CallbackQueryHandler(select_timeslot)],
            SELECTED: [CallbackQueryHandler(selected)],
        },
        fallbacks=[MessageHandler(Filters.all, default)],
    )
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.all, default))
    connect_google_sheet()
    updater.start_polling()
    updater.idle()

def connect_google_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)
    global sheet1
    sheet1 = client.open("registration_form").worksheet('Sheet1')
    global sheet2
    sheet2 = client.open("registration_form").worksheet('Sheet2')

if __name__ == '__main__':
    main()