<!-- Copyright (c) 2021 Christopher Taylor                                          -->
<!--                                                                                -->
<!--   Distributed under the Boost Software License, Version 1.0. (See accompanying -->
<!--   file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)        -->

# [pyzmq-collectives](https://github.com/ct-clmsn/pyzmq-collectives)

This library implements a [SPMD](https://en.m.wikipedia.org/wiki/SPMD) (single program
multiple data) model and collective communication algorithms (Robert van de Geijn's
Binomial Tree) in Python using [PyZMQ](https://github.com/zeromq/pyzmq). The library provides log2(N)
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

HPC batch scheduling systems like [Slurm](https://en.m.wikipedia.org/wiki/Slurm_Workload_Manager),
[TORQUE](https://en.m.wikipedia.org/wiki/TORQUE), [PBS](https://en.wikipedia.org/wiki/Portable_Batch_System),
etc. provide mechanisms to automatically define these
environment variables when jobs are submitted.

### Implementation Notes

## Who is this library for?

It is the author's opinion that 0MQ is has a simple and fairly pervasive
install base (several Free/Open Source software products use 0MQ under the
hood). Several environments the author has worked in lack MPI (OpenMPI,
MPICH, etc) installations or installing an MPI implementation is not
feasible for a variety of reasons. If you are a person that needs SPMD
programming and all the options you want or need are not available then
this library is for you.

## How many processs/nodes should I deploy?

Users should make sure to deploy distributed jobs with a power of 2,
or log2(N), instances of an application developed with this library.

## Why use 0MQ tcp protocol?

Currently a TCP/IP backend is implemented. TCP is a chatty protocol (lots of
network traffic is generated) and will have an adverse impact on performance.
That said, TCP is highly available and reliable.

## How scalable is it?

In the interest of providing a scalable solution, each time a communication
operation is invoked, a couple of things happen on the sender and receiver
side. For the sender: a socket is created, a connection is made, data is
transferred, a connection is closed, and the socket is closed. For the
receiver: a socket is created, a port is bound to the socket, data is
received, the socket unbinds, the socket is closed.

The reasoning for this particular implementation decision has to deal with
scalability concerns. If a sufficiently large enough number of machines are
involved with the application, then the program initialization will take a
non-trivial amount of time - all the machines will need to create N**2
(where N is the total number of machine) sockets, socket connections, and
socket handshakes.

Additionally, there is an overhead cost at the operating system level. Each
socket consumes a file descriptor. Operating system instances are configured
with a hard upper bound on the number of file descriptors that can be provided
to all applications running in the operations system. The popularity of using
file descriptors to manage synchronization (ie: using file descriptors as
semaphores for asynchronous function completion, etc) has created several
instances of "file descriptor leaks" or an over consumption of file descriptors
leading to program and operating system crashes.

The trade off is presented in this implementation. This library consumes 1
socket every time a communication occurs at the expense and cost of connection
initialization. Program initialization is faster, the solution is significantly
more scalable (ie: no need to over-exhaust operating system resources like file
descriptors), and it creates an incentive to minimize the number of communication
events (which is what one should always aim to achieve).

### License

Boost 1.0

### Author

Christopher Taylor

### Dependencies

* [pip](https://pypi.org/project/pip/)
* [pyzmq](https://github.com/zeromq/pyzmq)
* [python](https://python.org/
