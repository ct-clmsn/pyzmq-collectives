<!-- Copyright (c) 2021 Christopher Taylor                                          -->
<!--                                                                                -->
<!--   Distributed under the Boost Software License, Version 1.0. (See accompanying -->
<!--   file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)        -->

# [pyzmq-collectives](https://github.com/ct-clmsn/pyzmq-collectives)

This library implements a [SPMD](https://en.m.wikipedia.org/wiki/SPMD) (single program
multiple data) model and collective communication algorithms (Robert van de Geijn's
Binomial Tree) in Python using [PyZMQ](https://github.com/zeromq/jeromq). The library provides log2(N)
algorithmic performance for each collective operation over N compute hosts.

Collective communication algorithms are used in HPC (high performance computing) / Supercomputing
libraries and runtime systems such as [MPI](https://www.open-mpi.org) and [OpenSHMEM](http://openshmem.org).

Documentation for this library can be found on it's [wiki](https://github.com/ct-clmsn/pyzmq-collectives/wiki).
Wikipedia has a nice summary about collectives and SPMD programming [here](https://en.wikipedia.org/wiki/Collective_operation).

### Algorithms Implemented

* [Broadcast](https://en.wikipedia.org/wiki/Broadcast_(parallel_pattern))
* [Reduction](https://en.wikipedia.org/wiki/Broadcast_(parallel_pattern))
* [Scatter](https://en.wikipedia.org/wiki/Collective_operation#Scatter_[9])
* [Gather](https://en.wikipedia.org/wiki/Collective_operation#Gather_[8])
* [Barrier](https://en.wikipedia.org/wiki/Barrier_(computer_science))

### Configuring Distributed Program Execution

This library requires the use of environment variables
to configure distributed runs of SPMD applications.

Users are provided 2 Backend types for Collective operations
over TCP. The first Backend type is a BasicTcpBackend. The
BasicTcpBackend does not perform heartbeats to determine if
a remote process has failed. The second Backend type is
TcpBackend. The TcpBackend spins up an I/O thread to manage
data exchanges from the application and a modified implementation
of Pieter Hintjens ['Paranoid Pirate' heartbeat algorithm](https://www.oreilly.com/library/view/zeromq/9781449334437/). The heartbeat implementation should provide some form of remote
process fault detection.

Users are required to supply each of the following environment
variables to correctly run programs:

* PYZMQ_COLLECTIVES_NRANKS
* PYZMQ_COLLECTIVES_RANK
* PYZMQ_COLLECTIVES_ADDRESSES

PYZMQ_COLLECTIVES_NRANKS - unsigned integer value indicating
how many processes (instances or copies of the program)
are running.

PYZMQ_COLLECTIVES_RANK - unsigned integer value indicating
the process instance this program represents. This is
analogous to a user provided thread id. The value must
be 0 or less than PYZMQ_COLLECTIVES_NRANKS.

PYZMQ_COLLECTIVES_ADDRESSES - should contain a ',' delimited
list of ip addresses and ports. The list length should be
equal to the integer value of PYZMQ_COLLECTIVES_NRANKS. An
example for a 2 rank application name `app` is below:

```
PYZMQ_COLLECTIVES_NRANKS=2 PYZMQ_COLLECTIVES_RANK=0 PYZMQ_COLLECTIVES_ADDRESSES=127.0.0.1:5555,127.0.0.1:5556 ./app

PYZMQ_COLLECTIVES_NRANKS=2 PYZMQ_COLLECTIVES_RANK=1 PYZMQ_COLLECTIVES_ADDRESSES=127.0.0.1:5555,127.0.0.1:5556 ./app
```

In this example, Rank 0 maps to 127.0.0.1:5555 and Rank 1
maps to 127.0.0.1:5556.

TcpBackend users may modify the behavior of the hearbeat
implementation by changing the following environment
variables:

* PYZMQ_COLLECTIVES_LIVENESS
* PYZMQ_COLLECTIVES_INTERVAL
* PYZMQ_COLLECTIVES_INTERVAL_INIT

PYZMQ_COLLECTIVES_LIVENESS - unsigned integer value defining
how many times a heartbeat can be missed before failure is
determined.

PYZMQ_COLLECTIVES_INTERVAL - unsigned integer value defining
how many milliseconds to wait before communicating a
heartbeat.

PYZMQ_COLLECTIVES_INTERVAL_INIT - unsigned integer value defining
the inital number of milliseconds to wait before communicating a
heartbeat.

HPC batch scheduling systems like [Slurm](https://en.m.wikipedia.org/wiki/Slurm_Workload_Manager),
[TORQUE](https://en.m.wikipedia.org/wiki/TORQUE), [PBS](https://en.wikipedia.org/wiki/Portable_Batch_System),
etc. provide mechanisms to automatically define these
environment variables when jobs are submitted.

### Implementation Notes

Users should make sure to deploy distributed jobs with a power of 2,
or log2(N), instances of an application developed with this library.

Currently a TCP/IP backend is implemented. TCP is a chatty protocol (lots of
network traffic is generated) and will have an adverse impact on performance.
That said, TCP is highly available and reliable.

### License

Boost 1.0

### Author

Christopher Taylor

### Dependencies

* [pip](https://pypi.org/project/pip/)
* [pyzmq](https://github.com/zeromq/pyzmq)
* [python](https://python.org/
