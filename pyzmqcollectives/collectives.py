#  Copyright (c) 2021 Christopher Taylor
#
#  Distributed under the Boost Software License, Version 1.0. (See accompanying
#  file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
#
import os
import functools
import pickle
import json
from io import StringIO, BytesIO
from math import ceil, log
from zmq import *

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

    def initialize(self, param):
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
                    sock.disconnect("tcp://" + self.addresses[rank])
                    sock.close()
                    cont = False 
            except Exception as e:
                print( (str(e),), e ) 
                sock.disconnect("tcp://" + self.addresses[rank])
                sock.connect("tcp://" + self.addresses[rank])
                continue

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
            pass

        sock.unbind("tcp://" + self.addresses[self.rank]) #.split(':')[1])
        sock.close()
        return val
 
class Collectives(object):
    def __init__(self, backend):
        self.backend = backend

    def initialize(self, p):
        self.backend.initialize(p)

    def finalize(self):
        self.backend.finalize()

    def broadcast(self, data, root=0):
        print('broadcast')
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        k = rank_n // 2
        notrecv = True
        if root > 0:
            rank_me = ((self.backend.nranks-self.backend.rank) + root) % self.backend.nranks
            print('rankme', rank_me, self.backend.rank, root)
        else:
            rank_me = self.backend.rank

        for i in range(logp):
            twok = 2 * k
            if (rank_me % twok) == 0:
                print('xmt', rank_me, rank_me+k)
                self.backend.send(rank_me+k, data)
            elif notrecv and ((rank_me % twok) == k):
                print('rcv', rank_me, rank_me-k)
                data = self.backend.recv(rank_me-k)
                notrecv = False
            k >>= 1

        return data

    def reduce(self, data, init, fn, root=0):
        print('reduce')
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
                print('src', src)
                if (src < rank_n) and not_sent:
                    data = self.backend.recv(src)
                    print(type(data))
                    local_result = fn(local_result, data)
            elif not_sent:
                parent = rank_me & (~mask)
                self.backend.send(parent, local_result)
                not_sent = False

            mask <<= 1

        return local_result

    def barrier(self):
        print('barrier')
        v = self.reduce([0,], 0, lambda x, y: x + y)
        v = self.broadcast(v)

    def gather(self, data, root=0):
        print('gather')
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
        print('scatter')
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
