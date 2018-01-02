# Basic Sudoku implementation from http://newcoder.io/gui/intro/

from Tkinter import Tk, Canvas, Frame, Button, BOTH, TOP, BOTTOM
import tkFont

MARGIN = 10  # Pixels around the board
SIDE = 50  # Width of every board cell.
WIDTH = HEIGHT = MARGIN * 2 + SIDE * 9  # Width and height of the whole board


class SudokuError(Exception):
    """
    An application specific error.
    """
    pass

class SudokuUI(Frame):
    """
    The Tkinter UI, responsible for drawing the board and accepting user input.
    """
    def __init__(self, parent, game, main_ui):
        self.game = game
        self.main_ui = main_ui
        Frame.__init__(self, parent)
        self.parent = parent

        self.boardFont = tkFont.Font(family="Helvetica", size=20)

        self.row, self.col = -1, -1

        self.__initUI()


    def __initUI(self):
        """
        Initialises the Sudoku board
        """
        self.pack(fill=BOTH)
        self.canvas = Canvas(self,
                             width=WIDTH,
                             height=HEIGHT,
                             highlightthickness=0)
        self.canvas.pack(fill=BOTH, side=TOP)

        self.__draw_grid()
        self.draw_puzzle()

        self.canvas.bind("<Button-1>", self.__cell_clicked)
        self.canvas.bind("<Key>", self.__key_pressed)

    def __draw_grid(self):
        """
        Draws grid divided with blue lines into 3x3 squares
        """
        for i in xrange(10):
            color = "black" if i % 3 == 0 else "gray"

            x0 = MARGIN + i * SIDE
            y0 = MARGIN
            x1 = MARGIN + i * SIDE
            y1 = HEIGHT - MARGIN
            self.canvas.create_line(x0, y0, x1, y1, fill=color)

            x0 = MARGIN
            y0 = MARGIN + i * SIDE
            x1 = WIDTH - MARGIN
            y1 = MARGIN + i * SIDE
            self.canvas.create_line(x0, y0, x1, y1, fill=color)

    def draw_puzzle(self):
        """
        Deletes all the numbers and draws them from scratch
        """
        self.canvas.delete("numbers")
        for i in xrange(9):
            for j in xrange(9):
                answer = self.game.puzzle[i][j]
                can_edit = self.game.heatmap[i][j] == 2
                x = MARGIN + j * SIDE + SIDE / 2
                y = MARGIN + i * SIDE + SIDE / 2
                if answer != 0:
                    coords = str(i) + " " + str(j)
                    color = "sea green" if can_edit else "black"
                    self.canvas.create_text(
                        x, y, text=answer, tags=["numbers", coords], fill=color,
                        font=self.boardFont)

    def draw_update(self, i, j, number):
        tag = str(i) + " " + str(j)
        #self.canvas.delete(tag)
        x = MARGIN + j * SIDE + SIDE / 2
        y = MARGIN + i * SIDE + SIDE / 2
        if number != 0:
            self.canvas.create_text(
                x, y, text=number, tags=["numbers", tag], fill="sea green",
                font=self.boardFont)


    def __draw_cursor(self):
        """
        Hides the highlighted border of a the selected square
        """
        self.canvas.delete("cursor")
        if self.row >= 0 and self.col >= 0:
            x0 = MARGIN + self.col * SIDE + 1
            y0 = MARGIN + self.row * SIDE + 1
            x1 = MARGIN + (self.col + 1) * SIDE - 1
            y1 = MARGIN + (self.row + 1) * SIDE - 1
            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                outline="DeepSkyBlue2", tags="cursor"
            )

    def draw_victory(self, content):
        """
        Draws the circle containing the result of the game
        """
        x0 = y0 = MARGIN + SIDE * 2
        x1 = y1 = MARGIN + SIDE * 7
        self.canvas.create_oval(
            x0, y0, x1, y1,
            tags="victory", fill="dark orange", outline="orange"
        )
        # create text
        x = y = MARGIN + 4 * SIDE + SIDE / 2
        self.canvas.create_text(
            x, y,
            text=content, tags="victory",
            fill="white", font=("Arial", 12)
        )

    def __cell_clicked(self, event):
        """
        Handles cell clicking
        """
        if self.game.game_over:
            return
        x, y = event.x, event.y
        if MARGIN < x < WIDTH - MARGIN and MARGIN < y < HEIGHT - MARGIN:
            self.canvas.focus_set()

            # get row and col numbers from x,y coordinates
            row, col = (y - MARGIN) / SIDE, (x - MARGIN) / SIDE

            # if cell was selected already - deselect it
            if (row, col) == (self.row, self.col):
                self.row, self.col = -1, -1
            elif self.game.heatmap[row][col] == 2:
                self.row, self.col = row, col
        else:
            self.row, self.col = -1, -1

        self.__draw_cursor()

    def __key_pressed(self, event):
        """
        Handles key-presses
        """
        if self.game.game_over:
            return
        if self.row >= 0 and self.col >= 0 and event.char in "1234567890" and event.char != "":
            self.main_ui.insert_number(self.row, self.col, int(event.char))

    def __clear_answers(self):
        self.game.start()
        self.canvas.delete("victory")
        self.__draw_puzzle()


class SudokuBoard(object):
    """
    Sudoku Board representation
    """
    def __init__(self, board_string):
        self.board = self.__create_board(board_string)

    def __create_board(self, board_string):
        board = []
        nrs = board_string.split(',')
        line = []
        for n in nrs:
            if(len(line) == 9):
                board.append(line)
                line = []
                line.append(int(n))
            else:
                line.append(int(n))
        board.append(line)

        if len(board) != 9:
            raise SudokuError("Each sudoku puzzle must be 9 lines long.")

        for a in board:
            if len(a) != 9:
                raise SudokuError("Each line in the sudoku puzzle must be 9 chars long.")

        return board

class SudokuGame(object):
    """
    A Sudoku game, in charge of storing the state of the board and checking
    whether the puzzle is completed.
    """
    def __init__(self, board_string, heatmap):
        self.board_file = board_string
        self.start_puzzle = SudokuBoard(board_string).board
        self.heatmap = SudokuBoard(heatmap).board

    def start(self):
        self.game_over = False
        self.puzzle = []
        for i in xrange(9):
            self.puzzle.append([])
            for j in xrange(9):
                self.puzzle[i].append(self.start_puzzle[i][j])