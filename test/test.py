#  Copyright (c) 2021 Christopher Taylor
#
#  Distributed under the Boost Software License, Version 1.0. (See accompanying

#  file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
#
from pyzmqcollectives import *
import sys, time, zmq

def client():

    port = "5556"
    if len(sys.argv) > 1:
        port =  sys.argv[1]
        int(port)

    if len(sys.argv) > 2:
        port1 =  sys.argv[2]
        int(port1)

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect ("tcp://localhost:%s" % port)
    if len(sys.argv) > 2:
        socket.connect ("tcp://localhost:%s" % port1)

    #  Do 10 requests, waiting each time for a response
    for request in range (1,10):
        socket.send_string("Hello")
        #  Get the reply.
        message = socket.recv()

def server():
    port = "5556"
    if len(sys.argv) > 1:
        port =  sys.argv[1]
        int(port)

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:%s" % port)
    #socket.bind("tcp://*:%s" % port)

    while True:
        #  Wait for next request from client
        message = socket.recv()
        print("Received request: ", message)
        time.sleep (1)  
        socket.send_string("World from %s" % port)

if __name__ == "__main__":
    # test 0MQ
    '''
    if p.rank == 0:
        server()
    else:
        client()
    '''

    # test different ways
    # of invoking collectives
    #
    p = Params()

    '''
    be = BasicTcpBackend(p)

    c = Collectives(be)
    c.initialize()

    v = 0
    if be.rank == 0:
        v = 1

    v = c.broadcast(v) #, root=3)
    print(v)
    c.barrier()
    v = c.reduce([1,1,1,1], 0, lambda x, y : x + y)
    c.barrier()
    print(v)

    v = c.gather([1,1,1,1])
    c.barrier()
    print(v)

    v = c.scatter([1,1,1,1,2,2,2,2])
    c.barrier()
    print(v)

    print(p.rank, v)
    c.finalize()
    '''
    be = TcpBackend(p)

    with Collectives(be) as c:
        v = 0
        if be.rank == 0:
            v = 1

        v = c.broadcast(v) #, root=3)
        print(v)
        c.barrier()
        v = c.reduce([1,1,1,1], 0, lambda x, y : x + y)
        v = c.reduce([1,1,1,1], 0, lambda x, y : x + y)
        v = c.reduce([1,1,1,1], 0, lambda x, y : x + y)
        print(v, 'barrier')
        c.barrier()
        print(v, 'barrier')

        v = c.gather([1,1,1,1])
        c.barrier()
        print(v)

        v = c.scatter([1,1,1,1,2,2,2,2])
        c.barrier()
        print(v)

        print(p.rank, v)
