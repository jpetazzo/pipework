# Pipework

**_Software-Defined Networking for Linux Containers_**

Pipework lets you connect together containers in arbitrarily complex scenarios. 
Pipework uses cgroups and namespace and works with "plain" LXC containers 
(created with `lxc-start`), and with the awesome [Docker](http://www.docker.io/).

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Things to note](#things-to-note)
  - [vCenter / vSphere / ESX / ESXi](#vcenter--vsphere--esx--esxi)
  - [Virtualbox](#virtualbox)
  - [Docker](#docker)
- [LAMP stack with a private network between the MySQL and Apache containers](#lamp-stack-with-a-private-network-between-the-mysql-and-apache-containers)
- [Docker integration](#docker-integration)
- [Peeking inside the private network](#peeking-inside-the-private-network)
- [Setting container internal interface](#setting-container-internal-interface)
- [Setting host interface name](#setting-host-interface-name)
- [Using a different netmask](#using-a-different-netmask)
- [Setting a default gateway](#setting-a-default-gateway)
- [Connect a container to a local physical interface](#connect-a-container-to-a-local-physical-interface)
- [Let the Docker host communicate over macvlan interfaces](#let-the-docker-host-communicate-over-macvlan-interfaces)
- [Wait for the network to be ready](#wait-for-the-network-to-be-ready)
- [Add the interface without an IP address](#add-the-interface-without-an-ip-address)
- [Add a dummy interface](#add-a-dummy-interface)
- [DHCP](#dhcp)
- [DHCP Options](#dhcp-options)
- [Specify a custom MAC address](#specify-a-custom-mac-address)
- [Virtual LAN (VLAN)](#virtual-lan-vlan)
- [Control routes](#routes)
- [Support Open vSwitch](#support-open-vswitch)
- [Support InfiniBand IPoIB](#support-infiniband-ipoib)
- [Cleanup](#cleanup)
- [Integrating pipework with other tools](#integrating-pipework-with-other-tools)
- [About this file](#about-this-file)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

### Things to note

#### vCenter / vSphere / ESX / ESXi
**If you use vCenter / VSphere / ESX / ESXi,** set or ask your administrator
to set *Network Security Policies* of the vSwitch as below:

- Promiscuous mode:    **Accept**
- MAC address changes: **Accept**
- Forged transmits:    **Accept**

After starting the guest OS and creating a bridge, you might also need to
fine-tune the `br1` interface as follows:

- `brctl stp br1 off` (to disable the STP protocol and prevent the switch
  from disabling ports)
- `brctl setfd br1 2` (to reduce the time taken by the `br1` interface to go
  from *blocking* to *forwarding* state)
- `brctl setmaxage br1 0`

#### Virtualbox
**If you use VirtualBox**, you will have to update your VM network settings.
Open the settings panel for the VM, go the the "Network" tab, pull down the
"Advanced" settings. Here, the "Adapter Type" should be `pcnet` (the full
name is something like "PCnet-FAST III"), instead of the default `e1000`
(Intel PRO/1000). Also, "Promiscuous Mode" should be set to "Allow All".

If you don't do that, bridged containers won't work, because the virtual
NIC will filter out all packets with a different MAC address.  If you are
running VirtualBox in headless mode, the command line equivalent of the above
is `modifyvm --nicpromisc1 allow-all`.  If you are using Vagrant, you can add
the following to the config for the same effect:

```Ruby
config.vm.provider "virtualbox" do |v|
  v.customize ['modifyvm', :id, '--nictype1', 'Am79C973']
  v.customize ['modifyvm', :id, '--nicpromisc1', 'allow-all']
end
```

Note: it looks like some operating systems (e.g. CentOS 7) do not support
`pcnet` anymore. You might want to use the `virtio-net` (Paravirtualized
Network) interface with those.


#### Docker

**Before using Pipework, please ask on the [docker-user mailing list](
https://groups.google.com/forum/#!forum/docker-user) if there is a "native"
way to achieve what you want to do *without* Pipework.**

In the long run, Docker will allow complex scenarios, and Pipework should
become obsolete.

If there is really no other way to plumb your containers together with
the current version of Docker, then okay, let's see how we can help you!

The following examples show what Pipework can do for you and your containers.


### LAMP stack with a private network between the MySQL and Apache containers

Let's create two containers, running the web tier and the database tier:

    APACHE=$(docker run -d apache /usr/sbin/httpd -D FOREGROUND)
    MYSQL=$(docker run -d mysql /usr/sbin/mysqld_safe)

Now, bring superpowers to the web tier:

    pipework br1 $APACHE 192.168.1.1/24

This will:

- create a bridge named `br1` in the docker host;
- add an interface named `eth1` to the `$APACHE` container;
- assign IP address 192.168.1.1 to this interface,
- connect said interface to `br1`.

Now (drum roll), let's do this:

    pipework br1 $MYSQL 192.168.1.2/24

This will:

- not create a bridge named `br1`, since it already exists;
- add an interface named `eth1` to the `$MYSQL` container;
- assign IP address 192.168.1.2 to this interface,
- connect said interface to `br1`.

Now, both containers can ping each other on the 192.168.1.0/24 subnet.


### Docker integration

Pipework can resolve Docker containers names. If the container ID that
you gave to Pipework cannot be found, Pipework will try to resolve it
with `docker inspect`. This makes it even simpler to use:

    docker run -name web1 -d apache
    pipework br1 web1 192.168.12.23/24


### Peeking inside the private network

Want to connect to those containers using their private addresses? Easy:

    ip addr add 192.168.1.254/24 dev br1

Voilà!


### Setting container internal interface ##
By default pipework creates a new interface `eth1` inside the container. In case you want to change this interface name like `eth2`, e.g., to have more than one interface set by pipework, use:

`pipework br1 -i eth2 ...`

**Note:**: for InfiniBand IPoIB interfaces, the default interface name is `ib0` and not `eth1`.


### Setting host interface name ##
By default pipework will create a host-side interface with a fixed prefix but random suffix. If you would like to specify this interface name use the `-l` flag (for local):

`pipework br1 -i eth2 -l hostapp1 ...`


### Using a different netmask

The IP addresses given to `pipework` are directly passed to the `ip addr`
tool; so you can append a subnet size using traditional CIDR notation.

I.e.:

    pipework br1 $CONTAINERID 192.168.4.25/20

Don't forget that all containers should use the same subnet size;
pipework is not clever enough to use your specified subnet size for
the first container, and retain it to use it for the other containers.


### Setting a default gateway

If you want *outbound* traffic (i.e. when the containers connects
to the outside world) to go through the interface managed by
Pipework, you need to change the default route of the container.

This can be useful in some usecases, like traffic shaping, or if
you want the container to use a specific outbound IP address.

This can be automated by Pipework, by adding the gateway address
after the IP address and subnet mask:

    pipework br1 $CONTAINERID 192.168.4.25/20@192.168.4.1


### Connect a container to a local physical interface

Let's pretend that you want to run two Hipache instances, listening on real
interfaces eth2 and eth3, using specific (public) IP addresses. Easy!

    pipework eth2 $(docker run -d hipache /usr/sbin/hipache) 50.19.169.157/24
    pipework eth3 $(docker run -d hipache /usr/sbin/hipache) 107.22.140.5/24

Note that this will use `macvlan` subinterfaces, so you can actually put
multiple containers on the same physical interface.


### Let the Docker host communicate over macvlan interfaces

If you use macvlan interfaces as shown in the previous paragraph, you
will notice that the host will not be able to reach the containers over
their macvlan interfaces. This is because traffic going in and out of
macvlan interfaces is segregated from the "root" interface.

If you want to enable that kind of communication, no problem: just
create a macvlan interface in your host, and move the IP address from
the "normal" interface to the macvlan interface. 

For instance, on a machine where `eth0` is the main interface, and has
address `10.1.1.123/24`, with gateway `10.1.1.254`, you would do this:

    ip addr del 10.1.1.123/24 dev eth0
    ip link add link eth0 dev eth0m type macvlan mode bridge
    ip link set eth0m up
    ip addr add 10.1.1.123/24 dev eth0m
    route add default gw 10.1.1.254

Then, you would start a container and assign it a macvlan interface
the usual way:

    CID=$(docker run -d ...)
    pipework eth0 $CID 10.1.1.234/24@10.1.1.254


### Wait for the network to be ready

Sometimes, you want the extra network interface to be up and running *before*
starting your service. A dirty (and unreliable) solution would be to add
a `sleep` command before starting your service; but that could break in
"interesting" ways if the server happens to be a bit slower at one point.

There is a better option: add the `pipework` script to your Docker image,
and before starting the service, call `pipework --wait`. It will wait
until the `eth1` interface is present and in `UP` operational state,
then exit gracefully.

If you need to wait on an interface other than eth1, pass the -i flag like
this:

    pipework --wait -i ib0


### Add the interface without an IP address

If for some reason you want to set the IP address from within the
container, you can use `0/0` as the IP address. The interface will
be created, connected to the network, and assigned to the container,
but without configuring an IP address:

    pipework br1 $CONTAINERID 0/0


### Add a dummy interface

If for some reason you want a dummy interface inside the container, you can add it like any other interface. Just set the host interface to the keyword dummy. All other options - IP, CIDR, gateway - function as normal.

    pipework dummy $CONTAINERID 192.168.21.101/24@192.168.21.1

Of course, a gateway does not mean much in the context of a dummy interface, but there it is.

### DHCP

You can use DHCP to obtain the IP address of the new interface. Just
specify the name of the DHCP client that you want to use instead
on an IP address; for instance:

    pipework eth1 $CONTAINERID dhclient

You can specify the following DHCP clients:

- dhclient
- udhcpc
- dhcpcd
- dhcp

The first three are "normal" DHCP clients. They have to be installed
on your host for this option to work. The last one works
differently: it will run a DHCP client *in a Docker container*
sharing its network namespace with your container. This allows
to use DHCP configuration without worrying about installing the
right DHCP client on your host. It will use the Docker `busybox`
image and its embedded `udhcpc` client.

The value of $CONTAINERID will be provided to the DHCP client to use
as the hostname in the DHCP request. Depending on the configuration of
your network's DHCP server, this may enable other machines on the network
to access the container using the $CONTAINERID as a hostname; therefore,
specifying $CONTAINERID as a container name rather than a container id
may be more appropriate in this use-case.

You need three things for this to work correctly:

- obviously, a DHCP server (in the example above, a DHCP server should
  be listening on the network to which we are connected on `eth1`);
- a DHCP client (either `udhcpc`, `dhclient` or `dhcpcp`) must be installed
  on your Docker *host* (you don't have to install it in your containers,
  but it must be present on the host), unless you specify `dhcp` as
  the client, in which case the Docker `busybox` image should be
  available;
- the underlying network must support bridged frames.

The last item might be particularly relevant if you are trying to
bridge your containers with a WPA-protected WiFi network. I'm not 100%
sure about this, but I think that the WiFi access point will drop frames
originating from unknown MAC addresses; meaning that you have to go
through extra hoops if you want it to work properly.

It works fine on plain old wired Ethernet, though.

#### Lease Renewal

All of the DHCP options - udhcpc, dhcp, dhclient, dhcpcd - exit or are killed by pipework when they are done assigning a lease. This is to prevent zombie processes from existing after a container exits, but the dhcp client still exists.

However, if the container is long-running - longer than the life of the lease - then the lease will expire, no dhcp client renews the lease, and the container is stuck without a valid IP address.

To resolve this problem, you can cause the dhcp client to remain alive. The method depends on the dhcp client you use.

* dhcp: see the next section [DHCP Options](#dhcp-options)
* dhclient: use DHCP client `dhclient-f`
* udhcpc: use DHCP client `udhcpc-f`
* dhcpcd: not yet supported.


**Note:** If you use this option *you* will be responsible for finding and killing those dhcp client processes in the future. pipework is a one-time script; it is not intended to manage long-running processes for you.

In order to find the processes, you can look for pidfiles in the following locations:

* dhcp: see the next section [DHCP Options](#dhcp-options)
* dhclient: pidfiles in `/var/run/dhclient.$GUESTNAME.pid`
* udhcpc: pidfiles in `/var/run/udhcpc.$GUESTNAME.pid`
* dhcpcd: not yet supported

`$GUESTNAME` is the name or ID of the guest as you passed it to pipework on instantiation.


### DHCP Options

You can specify extra DHCP options to be passed to the DHCP client
by adding them with a colon. For instance:

    pipework eth1 $CONTAINERID dhcp:-f

This will tell Pipework to setup the interface using the DHCP client
of the Docker `busybox` image, and pass `-f` as an extra flag to this
DHCP client. This flag instructs the client to remain in the foreground
instead of going to the background. Let's see what this means.

*Without* this flag, a new container is started, in which the DHCP
client is executed. The DHCP client obtains a lease, then goes to
the background. When it goes to the background, the PID 1 in this
container exits, causing the whole container to be terminated.
As a result, the "pipeworked" container has its IP address, but
the DHCP client has gone. On the up side, you don't have any
cleanup to do; on the other, the DHCP lease will not be renewed,
which could be problematic if you have short leases and the
server and other clients don't validate their leases before using
them.

*With* this flag, a new container is started, it runs the DHCP
client just like before; but when it obtains the lease, it
remains in the foreground. As a result, the lease will be
properly renewed. However, when you terminate the "pipeworked"
container, you should also take care of removing the container
that runs the DHCP client. This can be seen as an advantage
if you want to reuse this network stack even if the initial
container is terminated.


### Specify a custom MAC address

If you need to specify the MAC address to be used (either by the `macvlan`
subinterface, or the `veth` interface), no problem. Just add it as the
command-line, as the last argument:

    pipework eth0 $(docker run -d haproxy) 192.168.1.2/24 26:2e:71:98:60:8f

This can be useful if your network environment requires whitelisting
your hardware addresses (some hosting providers do that), or if you want
to obtain a specific address from your DHCP server. Also, some projects like
[Orchestrator](https://github.com/cvlc/orchestrator) rely on static
MAC-IPv6 bindings for DHCPv6:

    pipework br0 $(docker run -d zerorpcworker) dhcp fa:de:b0:99:52:1c

**Note:** if you generate your own MAC addresses, try remember those two
simple rules:

- the lowest bit of the first byte should be `0`, otherwise, you are
  defining a multicast address;
- the second lowest bit of the first byte should be `1`, otherwise,
  you are using a globally unique (OUI enforced) address.

In other words, if your MAC address is `?X:??:??:??:??:??`, `X` should
be `2`, `6`, `a`, or `e`. You can check [Wikipedia](
http://en.wikipedia.org/wiki/MAC_address) if you want even more details.

If you want a consistent MAC address across container restarts, but don't want to have to keep track of the messy MAC addresses, ask pipework to generate an address for you based on a specified string, e.g. the hostname. This guarantees a consistent MAC address:

    pipework eth0 <container> dhcp U:<some_string>

pipework will take *some_string* and hash it using MD5. It will then take the first 40 bits of the MD5 hash, add those to the locally administered prefix of 0x02, and create a unique MAC address.

For example, if your unique string is "myhost.foo.com", then the MAC address will **always** be `02:72:6c:cd:9b:8d`.

This is particularly useful in the case of DHCP, where you might want the container to stop and start, but always get the same address. Most DHCP servers will keep giving you a consistent IP address if the MAC address is consistent.

**Note:**  Setting the MAC address of an IPoIB interface is not supported.

### Virtual LAN (VLAN)

If you want to attach the container to a specific VLAN, the VLAN ID can be
specified using the `[MAC]@VID` notation in the MAC address parameter.

**Note:** VLAN attachment is currently only supported for containers to be
attached to either an Open vSwitch bridge or a physical interface. Linux
bridges are currently not supported.

The following will attach container zerorpcworker to the Open vSwitch bridge
ovs0 and attach the container to VLAN ID 10.

    pipework ovsbr0 $(docker run -d zerorpcworker) dhcp @10

### Control Routes

If you want to add/delete/replace routes in the container, you can run any iproute2 route command via pipework.

All you have to do is set the interface to be `route`, followed by the container ID or name, followed by the route command.

Here are some examples.

    pipework route $CONTAINERID add 10.0.5.6/24 via 192.168.2.1
    pipework route $CONTAINERID replace default via 10.2.3.5.78

Everything after the container ID (or name) will be run as an argument to `ip route` inside the container's namespace. Use the iproute2 man page.

### Support Open vSwitch

If you want to attach a container to the Open vSwitch bridge, no problem.

    ovs-vsctl list-br
    ovsbr0
    pipework ovsbr0 $(docker run -d mysql /usr/sbin/mysqld_safe) 192.168.1.2/24

If the ovs bridge doesn't exist, it will be automatically created


### Support InfiniBand IPoIB

Passing an IPoIB interface to a container is supported.  The IPoIB device is
created as a virtual device, similarly to how macvlan devices work.  The
interface also supports setting a partition key for the created virtual device.

The following will attach a container to ib0

    pipework ib0 $CONTAINERID 10.10.10.10/24

The following will do the same but connect it to ib0 with pkey 0x8001

    pipework ib0 $CONTAINERID 10.10.10.10/24 @8001

### Gratuitous ARP

If `arping` is installed, it will be used to send a gratuitous ARP reply
to the container's neighbors. This can be useful if the container doesn't
emit any network traffic at all, and seems unreachable (but suddenly becomes
reachable after it generates some traffic).

Note, however, that Ubuntu/Debian distributions contain two different `arping`
packages. The one you want is `iputils-arping`.


### Cleanup

When a container is terminated (the last process of the net namespace exits),
the network interfaces are garbage collected. The interface in the container
is automatically destroyed, and the interface in the docker host (part of the
bridge) is then destroyed as well.


### Integrating pipework with other tools

@dreamcat4 has built an amazing fork of pipework that can be integrated
with other tools in the Docker ecosystem, like Compose or Crane.
It can be used in "one shot," to create a bunch of network connections
between containers; it can run in the background as a daemon, watching
the Docker events API, and automatically invoke pipework when containers
are started, and it can also expose pipework itself through an API.

For more info, check the [dreamcat4/pipework](https://hub.docker.com/r/dreamcat4/pipework/)
image on the Docker Hub.


### About this file

This README file is currently the only documentation for pipework. When
updating it (specifically, when adding/removing/moving sections), please
update the table of contents. This can be done very easily by just running:

    docker-compose up

This will build a container with `doctoc` and run it to regenerate the
table of contents. That's it!
