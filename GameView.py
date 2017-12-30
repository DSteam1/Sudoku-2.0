from SudokuBoard import *
from Tkinter import Tk, Canvas, Frame, Button, BOTH, TOP, BOTTOM, LEFT, RIGHT, END,  Label, CENTER, Listbox, Entry
import tkMessageBox

_WIDTH = 666
_HEIGHT = 300
_GAME_HEIGHT = 500
_GAME_WIDTH = 700

class GameView:
    def __init__(self, container, main_ui, digits, types, players, game_started):
        self.main_ui = main_ui

        self.frame_left = Frame(container)
        self.frame_left.pack(side=LEFT, padx=20, pady=20)

        self.scoreFont = tkFont.Font(family="Helvetica", size=15)

        self.game = SudokuGame(digits, types)
        self.game.start()  # Start game
        self.UI = SudokuUI(self.frame_left, self.game, main_ui)  # Display sudoku board

        self.frame_right = Frame(container)
        self.frame_right.pack(side=RIGHT, padx=20, pady=10)

        games_txt = Label(self.frame_right, text="Scoreboard")
        games_txt.pack(side=TOP)

        self.games_lb = Listbox(self.frame_right, bg="gray99", selectbackground="gray99", height=6)
        self.games_lb.bind("<<ListboxSelect>>", self.no_selection)
        self.games_lb.pack()
        self.fill_players(players)

        self.waiting_txt = None
        if not game_started:
            self.waiting_txt = Label(self.frame_right, text="Waiting for players")
            self.waiting_txt.pack(side=TOP)

        self.exitButton = Button(self.frame_right, text="Exit game", command=self.exit_game)
        self.exitButton.pack( padx=10, pady=10)

    def update_board(self, digits, types):
        #ugly hack for handling empty heatmap, not necessary to receive it every time from server
        if(types == ""):
            heatmap_str = ""
            types = self.game.heatmap
            for row in types:
                row = [str(r) for r in row]
                row_str = ",".join(row)
                heatmap_str += row_str + ","
            types = heatmap_str
            types = types[:-1]

        game = SudokuGame(digits, types)
        game.start()  # Start game
        self.UI.destroy()
        self.UI = SudokuUI(self.frame_left, game, self.main_ui)  # Display sudoku board

    def show_end(self, content):
        self.UI.draw_victory(content)

    def fill_players(self, players):
        self.games_lb.delete(0, END)
        for idx, val in enumerate(players):  # Insert all games to the list
            self.games_lb.insert(idx, val)
        self.games_lb.pack()

    def add_player(self, player):
        self.games_lb.insert(END, player)
        self.games_lb.pack()

    def hide_waiting_txt(self):
        if self.waiting_txt is not None:
            self.waiting_txt.pack_forget()

    def no_selection(self, event):
        w = event.widget
        cur = w.curselection()
        if len(cur) > 0:
            w.selection_clear(cur)

    def exit_game(self):
        self.main_ui.leave_game()
