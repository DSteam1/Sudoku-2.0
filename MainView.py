from Tkinter import Frame, Button, LEFT, END, Label, Listbox
import tkMessageBox


class MainView:
    """
        Main UI responsible for handling user inputs and sudoku board viewing
    """
    def __init__(self, container, main_ui, games):
        self.main_ui = main_ui
        self.games = games

        self.frame_left = Frame(container)
        self.frame_left.pack(side=LEFT, padx=20, pady=20)

        games_txt = Label(self.frame_left, text="Available games:")
        games_txt.pack()

        self.games_lb = Listbox(self.frame_left)
        self.games_lb.pack()
        self.fill_games()

        self.enterButton = Button(self.frame_left, text="Refresh", command=self.get_games)
        self.enterButton.pack(side=LEFT, padx=10, pady=10)

        self.connectButton = Button(self.frame_left, text="Connect", command=self.connect)
        self.connectButton.pack(side=LEFT, padx=10, pady=10)

        frame_right = Frame(container)
        frame_right.pack(side=LEFT, padx=20, pady=20)

        self.nicknameLabel = Label(frame_right, text="Amount of players:")
        self.nicknameLabel.pack()

        self.players_lb = Listbox(frame_right)
        for i in range(2, 5):  # Possible amounts of players
            self.players_lb.insert(i, str(i))
        self.players_lb.pack()

        self.enterButton = Button(frame_right, text="Create new game", command=self.create_new_game)
        self.enterButton.pack(padx=10, pady=10)

    def hide(self, widget):
        widget.pack_forget()

    def get_games(self):
        self.games = self.main_ui.get_games()

    def fill_games(self):
        self.games_lb.delete(0, END)
        if self.games == ['']:  # Handle empty list
            return
        for idx, val in enumerate(self.games):  # Insert all games to the list
            self.games_lb.insert(idx, "Game " + str(val))
        self.games_lb.pack()

    def connect(self):
        selected_game_idx = self.games_lb.curselection()

        if len(selected_game_idx) == 0:
            tkMessageBox.showinfo("Error", "No game selected")
        else:
            selected_game = str.split(self.games_lb.get(selected_game_idx))[1]
            self.main_ui.game_open = True
            self.main_ui.join_game(selected_game)

    def create_new_game(self):
        player_count_idx = self.players_lb.curselection()
        if len(player_count_idx) == 0:
            tkMessageBox.showinfo("Error", "Select the amount of players")
            return
        else:
            player_count = self.players_lb.get(player_count_idx)
            self.main_ui.game_open = True
            self.main_ui.create_game(player_count)

    def display_join_fault(self):
        tkMessageBox.showinfo("Error", "Couldn't join game")
        self.main_ui.get_games()

    def display_game_full(self):
        tkMessageBox.showinfo("Error", "Game already full")
        self.main_ui.get_games()
