<!-- Copyright (c) 2021 Christopher Taylor                                          -->
<!--                                                                                -->
<!--   Distributed under the Boost Software License, Version 1.0. (See accompanying -->
<!--   file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)        -->

# [pyzmq-collectives](https://github.com/ct-clmsn/pyzmq-collectives)

This library implements [SPMD](https://en.m.wikipedia.org/wiki/SPMD) (single program
multiple data) collective communication algorithms (Robert van de Geijn's
Binomial Tree) in Python using [PyZMQ](https://github.com/zeromq/pyzmq). The library provides log2(N)
algorithmic performance for each collective operation over N compute hosts.

Collective communication algorithms are used in HPC (high performance computing) / Supercomputing
libraries and runtime systems such as [OpenMPI](https://www.open-mpi.org) and [OpenSHMEM](http://openshmem.org).

Documentation for this library can be found on it's [wiki](https://github.com/ct-clmsn/pyzmq-collectives/wiki).
Wikipedia has a nice summary about collectives and SPMD programming [here](https://en.wikipedia.org/wiki/Collective_operation).

### Algorithms Implemented

* [Broadcast](https://en.wikipedia.org/wiki/Broadcast_(parallel_pattern))
* [Reduction](https://en.wikipedia.org/wiki/Broadcast_(parallel_pattern))
* [Scatter](https://en.wikipedia.org/wiki/Collective_operation#Scatter_[9])
* [Gather](https://en.wikipedia.org/wiki/Collective_operation#Gather_[8])
* [Scan](https://en.wikipedia.org/wiki/Collective_operation#Prefix-Sum/Scan_[6])
* [Barrier](https://en.wikipedia.org/wiki/Barrier_(computer_science))

### Installing

```
./setup.py install --user
```

### How to use this library

Create a 'Params' object. Create a 'Backend' object using the
'Params' object as an input. Using the 'with' clause, users
create a collective communication context (providing the 'Backend'
object as an input) to perform the collective communication pattern.

Point-to-Point/Rank-to-Rank/Process-to-Process) communications can
be performed by calling send and recv on the 'Backend' object.

```
p = Params()
b = TcpBackend(p)

with Collectives(b) as c:
    c.barrier()
```

### Configuring Distributed Program Execution

This library requires the use of environment variables
to configure distributed runs of SPMD style applications.

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
list of IP addresses and ports. The list length should be
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
environment variables when jobs are submitted. Cloud scheduling
systems (Kubernetes, Nomad, etc) offer a similar capability.
Container users (Docker, Singularity, etc) can configure their
images to execute jobs using these environment variables.

### Implementation Notes

## Who is this library for?

Several environments the author has worked in lack MPI (OpenMPI,
MPICH, etc) installations and/or installing an MPI implementation
is not feasible for a variety of reasons (admin rules, institutional
inertia, compilers are ancient, etc). It is the author's opinion
that 0MQ has a simple and pervasive enough install base (several
Free/Open Source software products use 0MQ under the hood) and has
enough support from the commerical GNU/Linux distribution vendor space
that finding or getting 0MQ on a system should be a trivial affair.

If you are a person that works in a 'Python Shop', needs SPMD
programming, and all the options you want or need (OpenMPI, MPICH,
etc) are not available then this library is for you.

## What can I do with this library?

Do you work in the large scale data analysis or machine learning
problem space? Do you work on scientific computing problems? Do
you work with Numpy, Scipy, Scikit-Learn, Pandas, Arrow, PySparkling,
Gensim, NLTK, PyCUDA, Numba, PyTorch, Theano, Tensorflow, PyOpenCL,
OpenCV2, or database technologies (SQL) and want to scale the size
of the problems you'd like to solve? If you are a cloud developer
working with data stored on the hadoop file system, this library
combines nicely with [snakebite](https://github.com/spotify/snakebite), [pywebhdfs](https://github.com/ProjectMeniscus/pywebhdfs), [hdfs3](https://github.com/dask/hdfs3), [pyhdfs](https://github.com/jingw/pyhdfs).

This library allows you the ability to write programs, in the SPMD
programming style, with the aforementioned libraries, that utilize
a cluster of machines.

This library combined with the [marshal](https://docs.python.org/3/library/marshal.html) or [dill](https://dill.readthedocs.io/en/latest/dill.html) libraries let's you do weird things
like [send functions](https://stackoverflow.com/questions/1253528/is-there-an-easy-way-to-pickle-a-python-function-or-otherwise-serialize-its-cod) or [send lambdas](https://stackoverflow.com/questions/25348532/can-python-pickle-lambda-functions) as part of a distributed
computation.

## What is SPMD?

SPMD (single-program many data) is a parallel programming style that
requires users to conceptualize a network of computers as a large
single machine. Multicore processors are a reduced version of this
concept. Each core on the processor in your machine talks to other
cores over a network in your processor through memory access instructions.

The SPMD programming style re-enforces the notion that processors
communicate over a network instead of through the internal
interconnect. In academic terms, the machine model or
abstraction for this enviornment is called PRAM (parallel random
access machine). SPMD style can be used when writing multithreaded
programs for this library SPMD is being used to program clusters
of machines.

## Why use this over Dask and friends?

Several common data analytic or machine learning libraries that offer
distributed computing features and capabilities are implemented using
a 'microservices' model. The 'microservices' model means several
distributed 'follower' processes of a program run in an event loop.
Part of that event loop requires talking to a 'leader' in order to make
progress on the user's program (the leader assigns work to the followers).

In some cases, the followers are blocking or can only do a limited amount
of work before waiting to communicate with the leader for further
instruction. This seems like a reasonable approach but it also has the
side-effect of inducing several points of latency and performance loss; the
followers are not making progress on the problem as they are blocked on
the leader to tell them what to do. Additional latency is added into the
mix when several TCP/IP connections are made between leader and followers
(and visa versa).

Under the SPMD model, all instances of the program are running simultaneously
(or near simultaneously) on different compute hosts and immediately make progress
toward solving the problem. The only time communication occurs is when
information needs to be sent to different machines to make progress. There are
no leaders and followers because all distributed processes know what to do - the
instructions are in the program the distributed processes are executing.

The author's years of experience working data analytics and machine learning
problems left an impression that regex, numpy, scipy, and a collective
communication library are fundamental and necessary tools for practitioners.
Several of the more commonly used libraries require as much, if not more,
effort to learn when compared to learning SPMD programming. In some cases,
the more commonly used libraries are providing repackaged versions of this
existing programming model. This library fills the collective library niche,
when other traditional solutions are not readily available.

## How many processs/nodes should I deploy?

Users should make sure to deploy distributed jobs with a power of 2,
or log2(N), instances of an application developed with this library.

## Why use 0MQ tcp protocol?

Currently a TCP/IP backend is implemented. TCP is a chatty protocol
(lots of network traffic is generated) and will have an adverse impact
on performance. That said, TCP is highly available and reliable.

## How scalable is it?

In the interest of providing a scalable solution, each time a communication
operation is invoked, a couple of things happen on the sender and receiver
side. For the sender: a socket is created, a connection is made, data is
transferred, a connection is closed, and the socket is closed. For the
receiver: a socket is created, a port is bound to the socket, data is
received, the socket unbinds, the socket is closed. This implementation
can be considered heavy handed due to all the operating system calls and
interactions it requires.

The reasoning for this particular implementation decision has to deal with
scalability concerns. If a sufficiently large enough number of machines are
applied to execute an application, then program initialization will take a
non-trivial amount of time - all the machines will need to create N**2
(where N is the total number of machines) sockets, socket connections, and
socket handshakes. A separate thread/process for communication would be
required along with fairly complicated queue management logic (imagine a queue
built on top of 0MQ).

Additionally, there is an overhead cost at the operating system level. Each
socket consumes a file descriptor. Operating system instances are configured
with a hard upper bound on the number of file descriptors that can be provided
to all applications running in the operating system. The popularity of using
file descriptors to manage synchronization (ie: using file descriptors as
semaphores for asynchronous function completion, etc) has created several
instances of "file descriptor leaks" or an over consumption of file descriptors
leading to program and operating system crashes.

The trade off is presented in this implementation. This library consumes 1
socket every time a communication occurs at the expense and cost of connection
initialization overhead. Program initialization is faster, the solution is
significantly more scalable (ie: no need to over-exhaust operating system
resources like file descriptors; note this is a scalability versus communication
performance trade-off!), and it creates an incentive to minimize the number of
communication events (communication means waiting longer for a solution and more
opportunities for program failure).

## Limitations? Future Support/Features?

* Data transferred by this library should be capable of being pickled.
* Currently all binomial communication is implemented with rank 0 as the root
of the binomial tree.
* Does not currently provide startup script for local/distributed SPMD program
execution (consider mpi-run or mpi-exec)

* Future improvements will allow users to pick which rank serves as root.
* Needs to provide users with utility functions that simplify partitioning data
* Will provide future functionality that makes SPMD programming more approachable.
* Command line versions of the environment variable flags will be added in a
future release.

### License

Boost 1.0

### Author

Christopher Taylor

### Dependencies

* [pip](https://pypi.org/project/pip/)
* [pyzmq](https://github.com/zeromq/pyzmq)
* [python](https://python.org)
