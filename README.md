# Sudoku-2.0
Homework 2

Setup process:
The game is written in and requires Python 2.7.
It also requires pika and Pyro4 which can be installed using pip via the following commands:
pip install pika
pip install Pyro4
In addition, it requires a running RabbitMQ instance. RabbitMQ can be downloaded from here:
https://www.rabbitmq.com/download.html
The RabbitMQ installer may suggest one to install additional dependencies (e.g. Erlang/OTP 20.2).

Starting the game:
1) Start RabbitMQ.
2) Run server2.py to start a server.
3) Run one or more instances of client2.py to play the game.