from SudokuBoard import *
from Tkinter import Tk, Canvas, Frame, Button, BOTH, TOP, BOTTOM, LEFT, RIGHT, END,  Label, CENTER, Listbox, Entry
import tkMessageBox
import os, sys, re
from AnnounceListener import AnnounceListener

USERNAMES_FILE = "usernames.txt"

class ServerAddressView:

    def __init__(self, container, application):
        self.container = container
        self.application = application

        # LEFT CONTAINER
        self.frame_left = Frame(container)
        self.frame_left.pack(side=LEFT, padx=20, pady=20)
        exchange_label = Label(self.frame_left, text="Server info")
        exchange_label.pack(side=TOP, pady=10)

        # Exchange name row
        frame_row1 = Frame(self.frame_left)
        frame_row1.pack(side=TOP, padx=20, pady=5)
        exchange_label = Label(frame_row1, text="Name:")
        exchange_label.pack(side=LEFT)
        self.exchangeEntry = Entry(frame_row1, bd=5)
        self.exchangeEntry.pack(side=LEFT)

        # Hostname row
        frame_row2 = Frame(self.frame_left)
        frame_row2.pack(side=TOP, padx=20, pady=5)
        host_label = Label(frame_row2, text="Host:  ")
        host_label.pack(side=LEFT)
        self.hostEntry = Entry(frame_row2, bd=5)
        self.hostEntry.pack(side=LEFT)

        # Port row
        frame_row3 = Frame(self.frame_left)
        frame_row3.pack(side=TOP, padx=20, pady=5)
        port_label = Label(frame_row3, text="Port:  ")
        port_label.pack(side=LEFT)
        self.portEntry = Entry(frame_row3, bd=5)
        self.portEntry.pack(side=LEFT)

        # Connect button
        self.enterButton = Button(self.frame_left, text="Connect", command=self.handle_enter)
        self.enterButton.pack(side=BOTTOM, padx=20, pady=20)

        # RIGHT CONTAINER
        self.frame_right = Frame(container)
        self.frame_right.pack(side=LEFT, padx=20, pady=20)

        servers_label = Label(self.frame_right, text="Available servers:")
        servers_label.pack(pady=10)
        self.servers_lb = Listbox(self.frame_right)
        self.servers_lb.pack()
        self.servers_lb.bind('<<ListboxSelect>>', self.fill_serverinfo)

        pad = Label(self.frame_right, text="")
        pad.pack(side=BOTTOM, pady=10)

        # Default values
        self.exchangeEntry.insert(0, "sudoku")
        self.hostEntry.insert(0, "127.0.0.1")
        self.portEntry.insert(0, "5672")

        # Automatic server discovery
        self.servers_list = []
        self.announce_listener = AnnounceListener(self.servers_lb, self.servers_list)
        self.announce_listener.start()


    def handle_enter(self):  # Handle proceed button
        exchange = self.exchangeEntry.get()
        host = self.hostEntry.get()
        port = self.portEntry.get()

        self.application.rmq_exchange = exchange
        self.application.rmq_host = host
        self.application.rmq_port = port

        self.application.connect()

    def fill_nickname(self, evt):
        w = evt.widget
        idx = int(w.curselection()[0])
        self.entry.delete(0, END)
        self.entry.insert(0, w.get(idx))

    def fill_serverinfo(self, evt):
        if self.servers_lb.size() == 0: return
        w = evt.widget
        idx = int(w.curselection()[0])
        # Exchange name
        self.exchangeEntry.delete(0, END)
        self.exchangeEntry.insert(0, self.servers_list[idx][0])
        # Host name
        self.hostEntry.delete(0, END)
        self.hostEntry.insert(0, self.servers_list[idx][1])
        # Port
        self.portEntry.delete(0, END)
        self.portEntry.insert(0, self.servers_list[idx][2])

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