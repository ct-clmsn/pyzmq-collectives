#  Copyright (c) 2021 Christopher Taylor
#
#  Distributed under the Boost Software License, Version 1.0. (See accompanying
#  file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
#
from pyzmqcollectives import *

if __name__ == "__main__":
    p = BasicParams()
    be = BasicTcpBackend(p)

    c = Collectives(be)
    c.initialize(p)

    v = 0
    if be.rank == 0:
        v = 1
    v = c.broadcast(v)
    c.barrier()
    print(v)
    v = c.reduce([1,1,1,1], 0, lambda x, y : x + y)
    c.barrier()
    print(v)

    v = c.gather([1,1,1,1])
    c.barrier()
    print(v)

    v = c.scatter([1,1,1,1,2,2,2,2])
    c.barrier()
    print(v)

    c.finalize()
