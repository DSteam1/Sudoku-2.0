#!/usr/bin/env python
import pika
import uuid
import Pyro4
import time
from mtTkinter import *
from utils import init_logging
import OtherViews as OV
import MainView as MV
import GameView as GV
from mtTkinter import *
from threading import Thread
LOG = init_logging()

_WIDTH = 666
_HEIGHT = 300
_GAME_HEIGHT = 600
_GAME_WIDTH = 800

ROOMS = "R"
GAME_OBJ = "O"
GAME_ID = "D"

class Consumer(Thread):
    def __init__(self, channel, app):
        Thread.__init__(self)
        self.channel = channel
        self.daemon = True
        self.app = app

    def run(self):
        self.channel.start_consuming()

class Application():
    def __init__(self):
        self.root = Tk()
        self.root.minsize(width=_WIDTH, height=_HEIGHT)

        self.root.title("Sudoku")

        self.frame_container = Frame(self.root)
        self.frame_container.place(relx=0.5, rely=0.5, anchor=CENTER)

        self.existing_main_view = None
        self.existing_game_view = None
        self.game_started = False
        self.game_open = False
        self.user_id = None

        self.rmq_exchange = None
        self.rmq_host = None
        self.rmq_port = None
        
        self.nickname_view()

        self.root.mainloop()

        # After exiting from main loop
        self.leave_game()
        self.disconnect()


    def connect(self):
        credentials = pika.PlainCredentials('DSHW2', 'DSHW2')
        parameters = pika.ConnectionParameters(self.rmq_host, self.rmq_port)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        #declare exchange
        self.channel.exchange_declare(exchange=self.rmq_exchange, exchange_type='topic')

        #queue for lobby messages - when someone creates a new game then all users will be notified through a lobby
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        self.channel.queue_bind(exchange=self.rmq_exchange,
                                queue=queue_name,
                                routing_key="c_lobby.*")

        self.channel.basic_consume(self.callback,
                                   queue=queue_name,
                                   no_ack=True)

        #queue for personal messages - all messages sent personally to this user will go here
        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.user_callback, no_ack=True,
                                   queue=self.callback_queue)

        self.consumer = Consumer(self.channel, self)
        self.consumer.start()

        self.proceed_to_main_view()

    def proceed_to_main_view(self):
        self.main_view([])
        return

    #MESSAGE RESPONSES

    #handles lobby messages
    def callback(self, ch, method, props, body):
        rk = method.routing_key
        if (rk == "c_lobby.new_game"):
            LOG.info("Received the name of a new game")
            #ugly ugly ugly check, should be handled differently
            if(self.existing_main_view != None):
                games = self.existing_main_view.games
                games.append(body)
                self.update_main_view(games)
        if(rk == "c_lobby.game_removed"):
            LOG.info("Received id of removed game: " + body)
            if (self.existing_main_view != None): #ugly ugly ugly
                LOG.info("Removed game from list")
                games = self.existing_main_view.games
                games.remove(body)
                self.update_main_view(games)


    #handles personal messages
    def user_callback(self, ch, method, props, body):
        parts = body.split(";")
        if(parts[0] == ROOMS):
            LOG.info("Received a list of games")
            if (parts[1] == ""):
                LOG.info("No games :(")
            else:
                games = parts[1].split(",")
                self.update_main_view(games)
        if(parts[0] == GAME_OBJ):
            if(parts[2] == ""):
                LOG.info("Could not join game")
                self.game_join_fault()
            else:
                LOG.info("Received the uri of a game")
                self.game_id = parts[1]
                self.remote_game = Pyro4.Proxy(parts[2])

                #make queue for receiving messages about game updates
                self.game_update_queue(self.game_id)

                self.proceed_to_game_view()

    #handles game specific messages
    def game_callback(self, ch, method, props, body):
        rk = method.routing_key
        prefix = "game." + self.game_id + "."
        if (rk == prefix + "state"):
            LOG.info("Received state of a game")
            self.update_game_view(body, "", "")
        if(rk == prefix + "scores"):
            LOG.info("Received scores of a game")
            if self.game_open:
                scores = body.split(";")
                self.update_game_view("", "", scores)
                LOG.info("Updated scores in UI")
        if (rk == prefix + "player_joined"):
            LOG.info("Received name of the new player")
            if self.game_open:
                self.add_player_to_game_view(body)
                LOG.info("Updated player names in UI")
        if (rk == prefix + "has_started"):
                LOG.info("Received 'game has started' message")
                if self.game_open:
                    self.start_game()
        if (rk == prefix + "over"):
                LOG.info("Received 'game over' message")
                if self.game_open:
                    self.show_end(body)

    #MESSAGES
    #create queue for receiving updates about current game - when user joins with a game it binds itself to a queue where
    #are sent all game specific messages
    def game_update_queue(self, id):
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        self.channel.queue_bind(exchange=self.rmq_exchange,
                                queue=queue_name,
                                routing_key="game."+id+".*")

        self.channel.basic_consume(self.game_callback,
                                   queue=queue_name,
                                   no_ack=True)

        LOG.info("Set queue for receiving game updates")

        # asks to create a new game

    def create_game(self, nr_of_players):
        self.channel.basic_publish(exchange=self.rmq_exchange,
                                   routing_key="s_lobby.new_game",
                                   body=str(nr_of_players))
        LOG.info("Asked to create a new game")

    #asks to join a game
    def join_game(self, id):
        self.corr_id = str(uuid.uuid4())
        msg = self.nickname + " " + str(id)
        self.channel.basic_publish(exchange=self.rmq_exchange,
                                   routing_key="user.join",
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue,
                                       correlation_id=self.corr_id,
                                   ),
                                   body=msg)
        LOG.info("Asked to join a game")

    #asks for a list of available rooms
    def get_games(self):
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange=self.rmq_exchange,
                                   routing_key='user.rooms',
                                   properties=pika.BasicProperties(
                                       reply_to=self.callback_queue,
                                       correlation_id=self.corr_id,
                                   ),
                                   body="")
        LOG.info("Asked for a list of games")

    #LOGIC, using remote game object

    def proceed_to_game_view(self):
        state = self.remote_game.get_board_state()
        heatmap = self.remote_game.get_board_heatmap()
        scores = self.remote_game.get_scores()
        scores = scores.split(";")
        self.has_started = self.remote_game.get_has_started()
        self.game_view(state, heatmap, scores)
        if(self.has_started):
            self.start_game()

    def insert_number(self, row, column, digit):
        LOG.info("Inserting number.")
        ok = self.remote_game.insert_number(int(row), int(column), int(digit), self.nickname)
        if(ok):
            LOG.info("Insertion successful.")
        else:
            LOG.info("Insertion failed.")

    def leave_game(self):
        self.game_open = False
        ok = self.remote_game.leave(self.nickname)
        self.existing_game_view = None
        self.main_view([])
        if(ok):
            LOG.info("Left game")
        else:
            LOG.warn("Hmmmm")

    # Small functions for modifying views

    def start_game(self):
        self.game_started = True
        if self.existing_game_view is not None:
            self.existing_game_view.hide_waiting_txt()

    def show_end(self, winner):
        msg = "Game over. Player "+ winner + " won."
        self.existing_game_view.show_end(msg)

    # VIEWS

    def nickname_view(self):
        self.window_resize(_WIDTH, _HEIGHT)
        self.empty_frame(self.frame_container)
        OV.NicknameView(self.frame_container, self)

    def server_address_view(self):
        self.window_resize(_WIDTH, _HEIGHT)
        self.empty_frame(self.frame_container)
        OV.ServerAddressView(self.frame_container, self)

    def main_view(self, games):
        self.selected_game = None
        self.window_resize(_WIDTH, _HEIGHT)
        self.empty_frame(self.frame_container)
        self.existing_main_view = MV.MainView(self.frame_container, self, games)
        self.get_games()

    def update_main_view(self, games):
        if self.existing_main_view is None:
            self.main_view(games)
        else:
            self.existing_main_view.games = games
            self.existing_main_view.fill_games()

    def game_view(self, state, types, scores = ""):
        self.window_resize(_GAME_WIDTH, _GAME_HEIGHT)
        self.empty_frame(self.frame_container)
        self.existing_game_view = GV.GameView(self.frame_container, self, state, types, scores, self.game_started)
        self.existing_main_view = None

    def update_game_view(self, state, types, scores):
        if self.existing_game_view is None:
            self.game_view(state, types, scores)
        else:
            if state != "":
                self.existing_game_view.update_board(state, types)
            if scores != "":
                self.existing_game_view.fill_players(scores)

    def add_player_to_game_view(self, player):
        if self.existing_game_view is not None:
            data = player+":0"
            self.existing_game_view.add_player(data)

    def game_join_fault(self):
        if self.existing_main_view is not None:
            self.existing_main_view.display_join_fault()

    def empty_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def window_resize(self, width, height):
        self.root.minsize(width=width, height=height)

Application()