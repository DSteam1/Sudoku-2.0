from SudokuBoard import *
from Tkinter import Tk, Canvas, Frame, Button, BOTH, TOP, BOTTOM, LEFT, RIGHT, END,  Label, CENTER, Listbox, Entry
import tkMessageBox
import os, sys, re

USERNAMES_FILE = "usernames.txt"

class ServerAddressView:

    def __init__(self, container, application):
        self.container = container
        self.application = application

        self.nicknameLabel = Label(container, text="Welcome to Sudoku!")
        self.nicknameLabel.pack(side=TOP)

        self.nicknameLabel = Label(self.container, text="Enter Sudoku server address: ")
        self.nicknameLabel.pack(side=LEFT)

        self.entry = Entry(self.container, bd=5)
        self.entry.pack(side=LEFT)

        self.enterButton = Button(self.container, text="Connect", command=self.handle_enter)
        self.enterButton.pack(side=LEFT, padx=20, pady=20)

        self.entry.insert(0, "127.0.0.1")  # should specify default

    def handle_enter(self):  # Handle proceed button
        address = self.entry.get()
        self.application.server = address
        self.application.connect()

    def fill_nickname(self, evt):
        w = evt.widget
        idx = int(w.curselection()[0])
        self.entry.delete(0, END)
        self.entry.insert(0, w.get(idx))


class NicknameView:
    """
        Main UI responsible for handling user inputs and sudoku board viewing
    """
    def __init__(self, container, main_ui):
        self.main_ui = main_ui

        self.nicknameLabel = Label(container, text="Welcome to Sudoku!")
        self.nicknameLabel.pack(side=TOP)

        self.frame_left = Frame(container)
        self.frame_left.pack(side=LEFT, padx=20, pady=20)

        self.nicknameLabel = Label(self.frame_left, text="Enter nickname: ")
        self.nicknameLabel.pack(side=LEFT)

        self.entry = Entry(self.frame_left, bd=5)
        self.entry.pack(side=LEFT)

        self.enterButton = Button(self.frame_left, text="Proceed", command=self.handle_enter)
        self.enterButton.pack(side=LEFT, padx=20, pady=20)

        self.frame_right = Frame(container)
        self.frame_right.pack(side=RIGHT)

        self.nicknameLabel = Label(self.frame_right, text="Previously used names:")
        self.nicknameLabel.pack()

        nickname_lb = Listbox(self.frame_right)
        for idx, val in enumerate(read_usernames()):  # Insert all previously used usernames to list
            nickname_lb.insert(idx, val)
        nickname_lb.pack()
        nickname_lb.bind('<<ListboxSelect>>', self.fill_nickname)

    def handle_enter(self):  # Handle proceed button
        nickname = self.entry.get()
        if self.validate_nickname(nickname):
            save_username(nickname)  # Save new username to file
            self.main_ui.nickname = nickname
            print("Proceeding")
            self.main_ui.server_address_view()  # Show server screen

    def fill_nickname(self, evt):
        w = evt.widget
        if w.size() == 0:
            return
        idx = int(w.curselection()[0])
        self.entry.delete(0, END)
        self.entry.insert(0, w.get(idx))

    def validate_nickname(self, nickname):
        validation = re.findall("^[a-zA-Z0-9]*$", nickname)
        if len(nickname) == 0:
            tkMessageBox.showinfo("Error", "Nickname must be at least 1 character long")
            return False
        elif len(nickname) > 8:
            tkMessageBox.showinfo("Error", "Nickname must be 8 characters or shorter")
            return False
        elif len(validation) == 0 or (len(validation) > 0 and validation[0] != nickname):
            tkMessageBox.showinfo("Error", "Only alphanumeric characters allowed")
            return False
        return True


def get_dir():
    return os.path.dirname(os.path.realpath(sys.argv[0]))


def read_usernames():
    try:
        file_path = get_dir() + '/' + USERNAMES_FILE
        if not os.path.exists(file_path):
            return []  # No such file
        un = []
        with open(file_path, 'r') as f:
            for i in range(10):  # Read max 10 lines
                line = str.strip(f.readline())
                if line == "":
                    break
                un.append(line[:8])  # Append 8 first characters of a line
            f.close()
        return un
    except Exception as ex:
        print("Error reading from file:", ex)
        return []


def save_username(username):
    try:
        usernames = read_usernames()  # Read usernames currently in file
        if username in usernames:
            usernames.remove(username)  # Remove current username
        usernames.insert(0, username)  # Append to start

        file_path = get_dir() + '/' + USERNAMES_FILE
        with open(file_path, 'w') as f:
            for un in usernames:  # Write usernames to file
                f.write(un[:8] + "\n")
            f.close()
    except Exception as ex:
        print("Error writing to file:", ex)