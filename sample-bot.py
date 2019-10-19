#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
import _thread

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="SPIDERMAN"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = False

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=0
prod_exchange_hostname="production"
exchange = None

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

list_lock = False
msg_list = []

def lock_list():
    global list_lock
    while list_lock:
        pass
    list_lock = True

def unlock_list():
    global list_lock
    list_lock = False

# ~~~~~============== NETWORKING CODE ==============~~~~~


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):
    while True:
        msg = ""
        try:
            msg = json.loads(exchange.readline())
        except:
            continue
        print(msg)
        lock_list()
        msg_list.append(msg)
        print("in read:", msg_list)
        unlock_list()

# ~~~~~============== MAIN LOOP ==============~~~~~

order_id = 0

def add_item(symbol, dir, price, size):
    global exchange
    global order_id
    order_id += 1
    write_to_exchange(exchange, {"type": "add", "order_id": order_id, "symbol": symbol,
                                 "dir": dir, "price": price, "size": size})

def main():
    global exchange
    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    _thread.start_new_thread(read_from_exchange, (exchange, ))
    #current_msg.append(read_from_exchange(exhange))
    while True:
        lock_list()
        # print(msg_list)
        base = 1000
        for msg in msg_list:
            if "type" in msg and msg["type"] == "book" and msg['symbol'] == 'BOND':
                min_seller = 1000000
                for seller in msg['sell']:
                    if seller[0] > min_seller and seller[0] > 1000:
                        min_seller = seller[0]
                    delta = (seller[0] - base - 0.01) / 2
                for buy_info in msg['sell']:
                    if buy_info[0] >= base + delta:
                        add_item("BOND", "BUY", base + delta, buy_info[1])
                    else:
                        add_item("BOND", "BUY", buy_info[0], buy_info[1])
                    add_item("BOND", "SELL", base, buy_info[1])
                #for sell_info in msg['buy']:
                #    if sell_info[0] <= base - delta:
                #        add_item("BOND", "SELL", base - delta, sell_info[1])
                #    else:
                #        add_item('BOND', 'SELL', sell_info[0], sell_info[1])
        msg_list.clear()
        unlock_list()

if __name__ == "__main__":
    main()
