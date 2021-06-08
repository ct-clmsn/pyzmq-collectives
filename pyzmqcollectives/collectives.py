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
import zmq

class BasicParams(object):
    def __init__(self):
        if 'PYZMQ_COLLECTIVES_RANK' in os.environ:
            self.rank = int(os.environ['PYZMQ_COLLECTIVES_RANK'])

        if 'PYZMQ_COLLECTIVES_NRANKS' in os.environ:
            self.nranks = int(os.environ['PYZMQ_COLLECTIVES_NRANKS'])

        if 'PYZMQ_COLLECTIVES_ADDRESSES' in os.environ:
            self.addresses = os.environ['PYZMQ_COLLECTIVES_ADDRESSES'].split(',')

class BasicTcpBackend(object):
    def __init__(self, bparam):
        self.rank = bparam.rank
        self.nranks = bparam.nranks
        self.ctx = zmq.Context()

        self.rep = self.ctx.socket(zmq.ROUTER)
        self.rep.identity = ("%d" % (self.rank,)).encode('utf-8')
        self.rep.probe_router = 1

        self.req = self.ctx.socket(zmq.ROUTER)
        self.req.identity = ("%d" % (self.rank,)).encode('utf-8')
        self.req.probe_router = 1

    def initialize(self, params):
        self.rep.bind( ("tcp://%s" % (params.addresses[self.rank],)) )

        for i in range(self.nranks):
            if i == self.rank:
                for j in range(self.nranks):
                    if self.rank != j:
                        self.req.connect( ("tcp://%s" % (params.addresses[j],)) )
                        self.req.recv_multipart()
            else:
                self.rep.recv_multipart()

    def finalize(self):
        self.rep.close()
        self.req.close()
        self.ctx.term()

    def send(self, rank, data):
        bio = BytesIO()
        rbio = StringIO()
        pickle.dump(data, bio)
        json.dump(rank, rbio)
        self.req.send_multipart([ bytes(rbio.getvalue(), encoding='raw_unicode_escape'), bio.getvalue() ])
        bio.close()
        rbio.close()

    def recv(self, rank):
        rcv = self.rep.recv_multipart()
        rank, bufv = rcv[0], rcv[1]
        bio = BytesIO(bufv)
        return pickle.load(bio)

class Collectives(object):
    def __init__(self, backend):
        self.backend = backend

    def initialize(self, p):
        self.backend.initialize(p)

    def finalize(self):
        self.backend.finalize()

    def broadcast(self, data):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        k = rank_n // 2
        notrecv = True
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

    def reduce(self, data, init, fn):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        mask = 0x1
        rank_me = self.backend.rank
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

    def gather(self, data):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        rank_me = self.backend.rank
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

    def scatter(self, data):
        rank_n = self.backend.nranks
        logp = (int)(ceil(log(self.backend.nranks)/log(2.)))
        rank_me = self.backend.rank
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
