#!/usr/bin/env python
import pika
import Pyro4
from threading import Thread
from utils import init_logging
from Tkconstants import NO
LOG = init_logging()
from Announcer import Announcer
import board

LOG = init_logging()


ROOMS = "R"
GAME_OBJ = "O"
JOIN_RESPONSE = "J"
LEAVE_RESPONSE = "A"

RMQ_HOST = "127.0.0.1"
RMQ_PORT = 5672
RMQ_EXCHANGE = "sudoku"


#game remote object
@Pyro4.expose
class Game():
    def __init__(self, id, nr_of_players, server):
        self.id = id
        self.nr_of_players = nr_of_players
        self.players = {}
        self.scores = {}
        self.uri = ""
        self.server = server
        self.board = board.Board()
        self.has_started = False
        self.game_ended = False

    def add_player(self, username):
        self.scores[username] = 0
        self.players[username] = username

    def insert_number(self, row, column, digit, username):
        if not self.has_started:
            LOG.info("User tried to insert number but game hasn't started yet. Nothing happens.")
            return False
        score_change = self._update_board(row, column, digit, username)
        if not score_change or score_change < 1:
            LOG.info("Invalid insertion attempt of digit " + str(digit) + " into coordinates " +
                      str(row) + ":" + str(column) + ".")
            self.server.send_game_scores(self._assemble_scores_msg_content(), self.id)
            return False
        else:
            LOG.info("Successful insertion.")
            self.server.send_game_state(self._assemble_board_state(), self.id)
            self.server.send_game_scores(self._assemble_scores_msg_content(), self.id)
            self.complete_game_if_is_complete()
            return True

    def leave(self, user):
        self.players.pop(user)
        self.scores.pop(user)
        LOG.info("Removed client " + user + " from game")
        if len(self.players) == 1 and self.has_started and not self._is_game_complete() and not self.game_ended:
            LOG.info("Only one player remaining. That player wins.")
            winner = self.players.keys()[0]
            self.server.send_game_over_msg(winner, self.id)
            self.server.send_game_scores(self._assemble_scores_msg_content(), self.id)
            self.server.end_game(self.id)
            self.game_ended = True
        elif len(self.players) == 0 and not self._is_game_complete() and not self.game_ended:
            self.server.end_game(self.id)
            self.game_ended = True
        elif len(self.players) >= 1 and not self._is_game_complete():
            self.server.send_game_scores(self._assemble_scores_msg_content(), self.id)
        return True

    def complete_game_if_is_complete(self):
       if self._is_game_complete() and not self.game_ended:
           winning_user = max(self.scores, key=self.scores.get)
           self.server.send_game_over_msg(winning_user, self.id)
           self.server.end_game(self.id)
           self.game_ended = True

    def start_game_if_enough_players(self):
        if len(self.players) >= int(self.nr_of_players):
            self.has_started = True
            self.server.send_start_game_msg(self.id)

    def get_has_started(self):
        return self.has_started

    def get_players(self):
        return self.players

    def get_board_state(self):
        return self._assemble_board_state()

    def get_board_heatmap(self):
        return self._assemble_board_heatmap()

    def get_scores(self):
        return self._assemble_scores_msg_content()

    def _update_board(self, row, column, digit, username):
        score_change = self.board.add_number(column, row, digit)
        if username in self.scores:
            self.scores[username] += score_change
            LOG.info("Score of client with id " + username + " changed by " + str(score_change))
        else:
            LOG.info("Score of client with id " + username + " could not be updated.")
        return score_change

    def _assemble_board_state(self):
        rows = self.board.ROWS
        content = ""
        for row in rows:
            for cell in row:
                content += str(cell.get_value())
                content += ","
        content = content[:-1]
        return content

    def _assemble_board_heatmap(self):
        rows = self.board.ROWS
        content = ""
        for row in rows:
            for cell in row:
                content += str(cell.type)
                content += ","
        content = content[:-1]
        return content

    def _assemble_scores_msg_content(self):
        content = ""
        for user in self.scores:
            content += user + ":" + str(self.scores[user]) + ";"
        content = content[:-1]
        return content

    def _is_game_complete(self):
        complete = self.board.is_solved()
        return complete


class Server:
    def __init__(self):
        self.games = {}
        self.gamenr_counter = 1
        self.users = []
        self.pyro_daemon = self.start_daemon()

        self.announce()  # Start announcing RabbitMQ server address, port and exchange name
        self.connect()

    def announce(self):
        self.announcer = Announcer(RMQ_HOST, RMQ_PORT, RMQ_EXCHANGE)
        self.announcer.setName('Announcer')
        self.announcer.start()
        LOG.info("Announcer started")

    def start_daemon(self):
        daemon = PyroDaemon()
        daemon.start()
        return daemon

    def connect(self):
        #credentials = pika.PlainCredentials('DSHW2', 'DSHW2')
        parameters = pika.ConnectionParameters(RMQ_HOST, RMQ_PORT)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        # declare exchange
        self.channel.exchange_declare(exchange=RMQ_EXCHANGE, exchange_type='topic')

        #binding queue for receiving lobby messages - server and all clients are listening it, when someone creates a new game then
        #a message is sent to server lobby, server lobby then sents the name of the new to clients lobby
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        self.channel.queue_bind(exchange=RMQ_EXCHANGE,
                           queue=queue_name,
                           routing_key="s_lobby.*")


        self.channel.basic_consume(self.lobby_callback,
                              queue=queue_name,
                              no_ack=True)

        #binding queue for receiving user specific messages - these messages contain reply_to (sender)
        #address to which the reply should be sent
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        self.channel.queue_bind(exchange=RMQ_EXCHANGE,
                                queue=queue_name,
                                routing_key="user.*")

        self.channel.basic_consume(self.user_callback,
                                   queue=queue_name,
                                   no_ack=True)

        self.channel.start_consuming()

    #handles user specific messages
    #user specific messages are requesting list of rooms and requesting joining a game
    def user_callback(self, ch, method, props, body):
        rk = method.routing_key
        if (rk == "user.rooms"):
                games = [str(g) for g in self.games]
                ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=pika.BasicProperties(correlation_id= \
                                                             props.correlation_id),
                         body=ROOMS+";"+",".join(games))
                LOG.info("Sent a list of games: " + ROOMS+";"+",".join(games))
        if (rk == "user.join"):
            username, game_id = body.split()
            uri = self.join_game(int(game_id), username)
            ch.basic_publish(exchange='',
                             routing_key=props.reply_to,
                             properties=pika.BasicProperties(correlation_id= \
                                                                 props.correlation_id),
                             body=GAME_OBJ+";"+game_id+";"+uri)
            LOG.info("Sent uri of a game")
        if (rk == "user.lobbyjoin"):
            no_such_user = self.check_users(body)
            if no_such_user:
                self.users.append(body)
            ch.basic_publish(exchange='',
                             routing_key=props.reply_to,
                             properties=pika.BasicProperties(correlation_id= \
                                                                 props.correlation_id),
                             body=JOIN_RESPONSE + ";" + str(no_such_user))
            LOG.info("Client " + body + " tried to join lobby. Responded with " + str(no_such_user))
        if (rk == "user.lobbyleave"):
            self.remove_users(body)
            ch.basic_publish(exchange='',
                             routing_key=props.reply_to,
                             properties=pika.BasicProperties(correlation_id= \
                                                                 props.correlation_id),
                             body=LEAVE_RESPONSE + ";" + str('Ack'))
            LOG.info("Client " + body + " left lobby")
            

    #handles messages sent to lobby - new game creation message is sent to lobby
    def lobby_callback(self, ch, method, props, body):
        rk = method.routing_key
        if(rk == "s_lobby.new_game"):
            game = self.create_game(int(body))
            self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                       routing_key="c_lobby.new_game",
                                       body=str(game))
            LOG.info("Sent the id of a new game")


    #called from lobby_callback
    def create_game(self, nr_of_players):
        id = self.gamenr_counter
        game = Game(id, nr_of_players, self)
        uri = self.pyro_daemon.register(game)
        game.uri = uri.asString()
        game.board.setup_board()
        self.games[id] = game
        self.gamenr_counter += 1
        return id

    #called from user_callback
    def join_game(self, game_id, username):
        if game_id in self.games.keys():
            game = self.games[game_id]
            players = game.get_players()
            # If game is full, send appropriate message
            if int(game.nr_of_players) < len(players) + 1 and username not in players:
                LOG.info("Client " + username + " tried to join full game  " + str(game_id))
                return ""

            #self.server.remove_client_from_games_except(self, game)  # Remove client from all other games
            game.add_player(username)
            LOG.info("Client " + username + " joined game " + str(game_id))

            uri = self.games[game_id].uri

            self.send_player_joined_msg(game_id, username)
            game.start_game_if_enough_players()
            return uri

            #self.send_new_board_state()
            #self.game.broadcast_scores()

    # Checks if username in servers users list 
    def check_users(self, body):
        return not body in self.users
    
    def remove_users(self, body):
        self.users.remove(body)

    # FUNCTIONS SENDING ALL KIND OF GAME RELATED MESSAGES to GAME SPECIFIC LOBBY THAT PLAYERS ARE LISTENING
    def send_player_joined_msg(self, game_id, username):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                   routing_key="game." + str(game_id) + ".player_joined",
                                   body=username)
        LOG.info("Sent name of the new player " + username)

    def send_player_left_msg(self, game_id, username):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                   routing_key="game." + str(game_id) + ".player_left",
                                   body=username)
        LOG.info("Sent name of the player who left " + username)

    def send_game_state(self, state, game_id):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                   routing_key="game."+str(game_id)+".state",
                                   body=state)
        LOG.info("Sent state of a game " + str(game_id))

    def send_game_scores(self, scores, game_id):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                   routing_key="game." + str(game_id) + ".scores",
                                   body=scores)
        LOG.info("Sent scores of a game " + str(game_id))

    def send_start_game_msg(self, game_id):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                   routing_key="game." + str(game_id) + ".has_started",
                                   body="")
        LOG.info("Sent 'game has started' message of game " + str(game_id))

    def send_game_over_msg(self, winner, game_id):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                               routing_key="game." + str(game_id) + ".over",
                               body=winner)
        LOG.info("Sent 'game over' message of game " + str(game_id))

    def send_game_removed_msg(self, game_id):
        self.channel.basic_publish(exchange=RMQ_EXCHANGE,
                                   routing_key="c_lobby.game_removed",
                                   body=str(game_id))
        LOG.info("Sent the id of removed game")

    #removes ended game from a list
    def end_game(self, game_id):
        if game_id in self.games:
            self.games.pop(game_id)
        self.send_game_removed_msg(game_id)
        LOG.info("Ended game " + str(game_id))


class PyroDaemon(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.pyro_daemon = Pyro4.Daemon()

    def register(self, item):
        uri = self.pyro_daemon.register(item)
        LOG.info("Daemon registered new item.")
        return uri

    def unregister(self, item):
        self.pyro_daemon.unregister(item)
        LOG.info("Daemon unregistered an item.")

    def run(self):
        self.pyro_daemon.requestLoop()


Server()