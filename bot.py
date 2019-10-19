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
from fractions import Fraction as frac

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name = "SPIDERMAN"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index = 0
prod_exchange_hostname = "production"
exchange = None

port = 25000 + (test_exchange_index if test_mode else 0)
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
market_price = {
    "BDU": 0,
    "ALI": 0,
    "TCT": 0
}
rate = 0.99
delta_for_stocks = 2
selling_stocks = {
    "BDU": 0,
    "ALI": 0,
    "TCT": 0
}
buying_stocks = {
    "BDU": 0,
    "ALI": 0,
    "TCT": 0
}
to_sell_stocks = {
    "BDU": 0,
    "ALI": 0,
    "TCT": 0
}
to_buy_stocks = {
    "BDU": 0,
    "ALI": 0,
    "TCT": 0
}
processing_stocks = {}


def add_item(symbol, dir, price, size):
    global exchange
    global order_id
    order_id += 1
    write_to_exchange(exchange, {"type": "add", "order_id": order_id, "symbol": symbol,
                                 "dir": dir, "price": price, "size": size})
    processing_stocks[order_id] = {"symbol": symbol, "dir": dir, "size": size}


pause_flag = False


def read_from_os():
    global pause_flag
    while True:
        s = input()
        if s == "p":
            pause_flag = True
        if s == "c":
            pause_flag = False
        # if s == "ALI" or s == "BDU" or s == "TCT":


def get_minmax():
    mn = pow(2, 30)
    mx = -mn
    for msg in msg_list:
        for seller in msg['sell']:
            mn = min(mn, seller[0])
        for buyer in msg['buy']:
            mx = max(mx, buyer[0])
    return mn, mx


def handle_bond():
    for msg in msg_list:
        if msg['symbol'] == 'bond':
            for buy_info in msg['sell']:
                if buy_info[0] < base:
                    add_item("BOND", "BUY", buy_info[0], buy_info[1])
                add_item("BOND", "SELL", base, buy_info[1])


stock_cnt = {'ALI': 0, 'BDU': 0, 'TCT': 0}
stock_cnt_tmp = dict()

def handle_stock(msg):
    symbol = msg['symbol']
    price = market_price[symbol]
    for buy_info in msg['SELL']:
        if stock_cnt_tmp[symbol] > 20:
            break
        add_item(msg["symbol"], "BUY", min(price * rate, buy_info[0]), min(buy_info[1], 10))
        stock_cnt_tmp[symbol] += min(buy_info[1], 10)
    for sell_info in msg['BUY']:
        add_item(symbol, 'SELL', max(sell_info[0], price), sell_info[1])
    market_price[symbol] = price


def handle_ack(msg):
    _order_id = msg['order_id']
    symbol = msg['symbol']
    if processing_stocks[_order_id]["dir"] == "SELL":
        to_sell_stocks[symbol] += processing_stocks[_order_id]["size"]
    elif processing_stocks[_order_id]["dir"] == "BUY":
        to_buy_stocks[symbol] += processing_stocks[_order_id]["size"]

def handle_fill(msg):
    t = msg['order_id']
    symbol = msg['symbol']
    if processing_stocks[t]["dir"] == "SELL":
        stock_cnt[symbol] -= processing_stocks[t]['size']
        selling_stocks[symbol] += processing_stocks[t]['size']
    elif processing_stocks[_order_id]["dir"] == "BUY":
        stock_cnt[symbol] += processing_stocks[t]["size"]
        buying_stocks[symbol] += processing_stocks[t]['size']
    r1, r2 = 0, 0
    if to_sell_stocks[symbol] == 0:
        r1 = pow(10, 9)
    else:
        r1 = selling_stocks[symbol] / to_sell_stocks[symbol]
    if to_buy_stocks[symbol] == 0:
        r2 = pow(10, 9)
    else:
        r2 = buying_stocks[symbol] / to_buy_stocks[symbol]
    if r1 > r2:
        market_price[symbol] *= 1.01
    else:
        market_price[symbol] *= 0.99


def main():
    global exchange
    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    _thread.start_new_thread(read_from_exchange, (exchange,))
    _thread.start_new_thread(read_from_os, ())
    while True:
        lock_list()
        # print(msg_list)
        while pause_flag:
            continue

        handle_bond()
        min_seller, max_buyer = get_minmax()
        global stock_cnt_tmp
        stock_cnt_tmp = stock_cnt
        for msg in msg_list:
            if 'type' in msg:
                if msg['type'] == 'book':
                    symbol = msg['symbol']
                    if symbol in market_price:
                        if market_price[symbol] == 0:
                            market_price[symbol] = max_buyer * 0.99 + (min_seller - max_buyer) / 2
                        handle_stock(msg)
                elif msg['type'] == 'ack':
                    handle_ack(msg)
                elif msg['type'] == 'fill':
                    handle_fill(msg)

        msg_list.clear()
        unlock_list()


if __name__ == "__main__":
    main()
