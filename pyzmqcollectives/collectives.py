#  Copyright (c) 2021 Christopher Taylor
#
#  Distributed under the Boost Software License, Version 1.0. (See accompanying
#  file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
#
import os, traceback, functools, pickle

from io import BytesIO
from math import ceil, log
from time import sleep
from random import uniform
from zmq import *

class ExpBackoff(object):
    def __init__(self, retries = 10, backoff_amt = 0.01):
        self.retries = retries
        self.retry_count = 0
        self.backoff_amt = backoff_amt # ms (10 sec)

    def value(self):
        if self.retry_count == self.retries:
            return -1
        else:
            self.retry_count += 1

        return ( self.backoff_amt * 2 ** self.retry_count + uniform(0, 1) )

    def reset(self):
        self.retry_count = 0


class BasicParams(object):
    def __init__(self):
        if 'PYZMQ_COLLECTIVES_RANK' in os.environ:
            self.rank = int(os.environ['PYZMQ_COLLECTIVES_RANK'])

        if 'PYZMQ_COLLECTIVES_NRANKS' in os.environ:
            self.nranks = int(os.environ['PYZMQ_COLLECTIVES_NRANKS'])

        if 'PYZMQ_COLLECTIVES_ADDRESSES' in os.environ:
            self.addresses = os.environ['PYZMQ_COLLECTIVES_ADDRESSES'].split(',')

class BasicTcpBackend(object):
    def __init__(self, bparams):
        self.rank = bparams.rank
        self.nranks = bparams.nranks 
        self.addresses = bparams.addresses

    def initialize(self):
        return

    def finalize(self):
        return

    def send(self, rank, data):
        ctx = Context.instance()
        sock = ctx.socket(PAIR)
        sock.setsockopt(IMMEDIATE, 1)
        sock.connect("tcp://" + self.addresses[rank])
        cont = True
        while cont:
            try:
                rc = sock.send_pyobj(data)
                if rc != None:
                    sock.disconnect("tcp://" + self.addresses[rank])
                    sock.connect("tcp://" + self.addresses[rank])
                else:
                    cont = False 

            except Exception as e:
                sock.disconnect("tcp://" + self.addresses[rank])
                sock.connect("tcp://" + self.addresses[rank])
                continue

        sock.disconnect("tcp://" + self.addresses[rank])
        sock.close()

    def recv(self, rank):
        ctx = Context.instance()
        sock = ctx.socket(PAIR)
        sock.bind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
        val = None

        try:
            val = sock.recv_pyobj()
        except Exception as e:
            print( (str(e),), e )
            
        sock.unbind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
        sock.close()
        return val
 
class Params(BasicParams):
    def __init__(self, backoff_retries=1000, backoff_amt=0.01):
        BasicParams.__init__(self)
        self.backoff_retries = backoff_retries
        self.backoff_amt = backoff_amt

class TcpBackend(object):
    def __init__(self, params):
        self.rank = params.rank
        self.nranks = params.nranks 
        self.addresses = params.addresses
        self.backoff_retries = params.backoff_retries
        self.backoff_amt = params.backoff_amt

    def initialize(self):
        return

    def finalize(self):
        return

    def send(self, rank, data):
        backoff = ExpBackoff(retries=self.backoff_retries, backoff_amt=self.backoff_amt)
        cont = True

        ctx = Context.instance()
        sock = ctx.socket(PUSH)
        sock.setsockopt(IMMEDIATE, 1)
        sock.setsockopt(LINGER, -1)
        sock.setsockopt(DELAY_ATTACH_ON_CONNECT, 1)
        sock.setsockopt(SNDHWM , 0)
        sock.connect("tcp://" + self.addresses[rank])
        poller = Poller()
        poller.register(sock, POLLOUT)

        while cont:
            try:
                rc = backoff.value()
                if rc == -1:
                    poller.unregister(sock)
                    sock.disconnect("tcp://" + self.addresses[rank])
                    sock.close()
                    raise Exception("Backoff exceeded retry count!")

                sock.send_pyobj(data)
                socks = dict(poller.poll(rc))
                if sock in socks and socks[sock] == POLLOUT:
                    cont = False
                continue
            except Exception as e:
                print( (str(e),), e )
                rc = backoff.value()
                if rc == -1:
                    poller.unregister(sock)
                    sock.disconnect("tcp://" + self.addresses[rank])
                    sock.close()
                    raise Exception("Backoff exceeded retry count!")

                sock.connect("tcp://" + self.addresses[rank])
                continue

        poller.unregister(sock)
        sock.disconnect("tcp://" + self.addresses[rank])
        sock.close()

    def recv(self, rank):
        backoff = ExpBackoff(retries=self.backoff_retries, backoff_amt=self.backoff_amt)
        val = None
        cont = True

        ctx = Context.instance()
        sock = ctx.socket(PULL)
        sock.setsockopt(RCVHWM , 0)
        sock.bind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
        poller = Poller()
        poller.register(sock, POLLIN)

        while cont:
            try:
                rc = backoff.value()
                if rc == -1:
                    cont = False
                    poller.unregister(sock)
                    sock.unbind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
                    sock.close()
                    raise Exception("Backoff exceeded retry count!")
 
                socks = dict(poller.poll(rc))
                if sock in socks and socks[sock] == POLLIN:
                    val = sock.recv_pyobj()
                    cont = False
                continue
            except Exception as e:
                print( (str(e),), e )
                rc = backoff.value()
                if rc == -1:
                    poller.unregister(sock)
                    sock.unbind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
                    sock.close()

                sock.connect("tcp://" + self.addresses[rank])
                continue
           
        poller.unregister(sock)
        sock.unbind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
        sock.close()
        return val

class Collectives(object):
    def __init__(self, backend):
        self.backend = backend

    def initialize(self):
        self.backend.initialize()

    def finalize(self):
        self.backend.finalize()

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            # return False # uncomment to pass exception through
        self.finalize()
        return True

    def broadcast(self, data, root=0):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        k = rank_n // 2
        notrecv = True
        if root > 0:
            rank_me = ((self.backend.nranks-self.backend.rank) + root) % self.backend.nranks
        else:
            rank_me = self.backend.rank

        for i in range(logp):
            twok = 2 * k
            if (rank_me % twok) == 0:
                self.backend.send(rank_me+k, data)
            elif notrecv and ((rank_me % twok) == k):
                data = self.backend.recv(rank_me-k)
                notrecv = False
            k >>= 1

        return data

    def reduce(self, data, init, fn, root=0):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        mask = 0x1
        rank_me = self.backend.rank
        if root > 0:
            rank_me = ((root+1) + (self.backend.rank+1)) % (self.backend.nranks)
        not_sent = True

        local_result = functools.reduce(fn, data, init)

        for i in range(logp):
            if (mask & rank_me) == 0:
                src = rank_me | mask
                if (src < rank_n) and not_sent:
                    data = self.backend.recv(src)
                    local_result = fn(local_result, data)
            elif not_sent:
                parent = rank_me & (~mask)
                self.backend.send(parent, local_result)
                not_sent = False

            mask <<= 1

        return local_result

    def barrier(self):
        v = self.reduce([0,], 0, lambda x, y: x + y)
        v = self.broadcast(v)

    def gather(self, data, root=0):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        rank_me = self.backend.rank
        if root > 0:
            rank_me = ((root+1) + (self.backend.rank+1)) % (self.backend.nranks)
        mask = 0x1
        block_sz = len(data) // rank_n

        ret = list()
        buffers = list()
        if rank_me != 0:
            bio = BytesIO()
            pickle.dump(data, bio)
            buffers.append(bio.getvalue())

        ret.append(data)

        for i in range(logp):
            if (mask & rank_me) == 0:
                if (rank_me | mask) < rank_n:
                    rbuf = self.backend.recv(rank_me)
                    bio = BytesIO(rbuf)
                    ldata = pickle.load(bio)
                    for ld in ldata:
                        buffers.append(ld)
                    bio.close()
            else:
                parent = rank_me & (~mask)
                bio = BytesIO()
                pickle.dump(buffers, bio)
                self.backend.send(parent, bio.getvalue())

            mask <<= 1

        if rank_me < 1:
            for buf in buffers:
                ibuf = BytesIO(buf)
                local_data = pickle.load(ibuf)
                ret.append(local_data)
                ibuf.close()

        return ret

    def scatter(self, data, root=0):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        rank_me = self.backend.rank
        if root > 0:
            rank_me = ((root+1) + (self.backend.rank+1)) % (self.backend.nranks)

        k = rank_n // 2
        block_sz = len(data) // rank_n
        not_recv = True

        ret = list()
        buffers = list()
        for i in range(logp):
            twok = 2 * k
            if (rank_me % twok) == 0:
                if len(buffers) < 1:
                    if not_recv:
                        not_recv = False
                        ret.append(data[:block_sz])
                    beg = ((rank_me + k) % rank_n) * block_sz
                    end = ((rank_n - (rank_me % rank_n)) * block_sz) + 1
                    bio = BytesIO()
                    pickle.dump(data[beg:end], bio)
                    buffers.append(bio.getvalue())
                    bio.close()

                bio = BytesIO()
                pickle.dump(buffers, bio)
                self.backend.send(rank_me+k, bio.getvalue())
                bio.close()
            elif not_recv and ((rank_me % twok) == k):
                val = self.backend.recv(rank_me-k)
                bio = BytesIO(val)
                vals = pickle.load(bio)
                for v in vals:
                    vbio = BytesIO(v)
                    rv = pickle.load(vbio)[:block_sz]
                    ret.append(rv)
                    vbio.close()
                not_recv = False
                bio.close()
            k >>= 1
            rank_n >>= 1
        return ret

    def scan(self, data, init, fn, root=0):
        '''
        this implementation performs a reduction (using init
        and fn), then a modified binomial tree broadcast is
        performed; the left hand side of the tree recieves
        the value of init and the right hand side recieves
        the local value computed by the reduction
        '''
        val = self.reduce(data, init, fn, root)
        xmt_data = [init, val]

        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        k = rank_n // 2
        notrecv = True
        xmt_idx = 1
 
        if root > 0:
            rank_me = ((self.backend.nranks-self.backend.rank) + root) % self.backend.nranks
        else:
            rank_me = self.backend.rank

        for i in range(logp):
            twok = 2 * k
            if (rank_me % twok) == 0:
                self.backend.send(rank_me+k, xmt_data[xmt_idx])
                if xmt_idx == 1:
                    xmt_idx = 0
            elif notrecv and ((rank_me % twok) == k):
                val = self.backend.recv(rank_me-k)
                for i in range(len(data)):
                    data[i] = fn(val, data[i])
                notrecv = False
            k >>= 1

        return data


