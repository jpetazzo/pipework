# Pipework: Software-Defined Networking for Linux Containers

Pipework lets you connect together containers in arbitrarily complex scenarios.

It is best used along with [docker](http://www.docker.io/), but you can also
use it with "plain" LXC containers.

Let's start with some examples of what it can do.
We'll use docker for simplicity.


## LAMP stack with a private network between the MySQL and Apache containers

Let's create two containers, running the web tier and the database tier:

    APACHE=$(docker run -d apache /usr/sbin/httpd -D FOREGROUND)
    MYSQL=$(docker run -d mysql /usr/sbin/mysqld_safe)

Now, bring superpowers to the web tier:

    pipework br1 $APACHE 192.168.1.1

This will:
- create a bridge named `br1` in the docker host;
- add an interface named `eth1` to the `$APACHE` container;
- assign IP address 192.168.1.1 to this interface,
- connect said interface to `br1`.

Now (drum roll), let's do this:

    pipework br1 $MYSQL 192.168.1.2

This will:
- not create a bridge named `br1`, since it already exists;
- add an interface named `eth1` to the `$MYSQL` container;
- assign IP address 192.168.1.2 to this interface,
- connect said interface to `br1`.

Now, both containers can ping each other on the 192.168.1.0/24 subnet.


## Peeking inside the private network

Want to connect to those containers using their private addresses? Easy:

    ifconfig br1 192.168.1.254

Voilà!


## Connect a container to a local physical interface

Let's pretend that you want to run two Hipache instances, listening on real
interfaces eth2 and eth3, using specific (public) IP addresses. Easy!

    pipework eth2 $(docker run -d hipache /usr/sbin/hipache) 50.19.169.157
    pipework eth3 $(docker run -d hipache /usr/sbin/hipache) 107.22.140.5

Note that this will use `macvlan` subinterfaces, so you can actually put
multiple containers on the same physical interface.

    
## Cleanup

When a container is terminated (the last process of the net namespace exits),
the network interfaces are garbage collected. The interface in the container
is automatically destroyed, and the interface in the docker host (part of the
bridge) is then destroyed as well.


## Future improvement: AVAHI / DHCP auto-configuration

I'm considering providing a "network configurator" docker image. This image
will let you configure a container extra interface (eth1) using DHCP or AVAHI,
without actually having a DHCP client or AVAHI daemon in the container itself.
