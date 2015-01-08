#!/usr/bin/python3

import amqp
import pprint

def on_message(msg):
    print(msg.delivery_info)
    print(msg.properties)
    pprint.pprint(msg.body)
    print("--")

# connect
_conn = amqp.Connection(host="172.16.4.20", userid="guest",
    password="guest", virtual_host="/")

_exchange_name = "imp"

_channel = _conn.channel()
_channel.exchange_declare(exchange=_exchange_name, type="topic")

result = _channel.queue_declare(exclusive=True)
queue_name = result[0]

_channel.queue_bind(exchange=_exchange_name, queue=queue_name,
                       routing_key="#")

_channel.basic_consume(queue=queue_name, callback=on_message, no_ack=True)

while _channel.callbacks:
    _channel.wait()

_channel.close()
_conn.close()

