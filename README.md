# Pipework

**_Software-Defined Networking for Linux Containers_**

Pipework lets you connect together containers in arbitrarily complex scenarios. 
Pipework uses cgroups and namespace and works with "plain" LXC containers 
(created with `lxc-start`), and with the awesome [Docker](http://www.docker.io/).

##### Table of Contents
* [Things to note](#notes)  
  * Virtualbox
  * Docker
* [LAMP stack with a private network between the MySQL and Apache containers](#lamp)  
* [Docker integration](#docker_integration)  
* [Peeking inside the private network](#peeking_inside)  
* [Setting container internal interface](#setting_internal)  
* [Setting host interface name](#setting_host)  
* [Using a different netmask](#different_netmask)  
* [Setting a default gateway](#default_gateway)  
* [Connect a container to a local physical interface](#local_physical)  
* [Let the Docker host communicate over macvlan interfaces](#macvlan)  
* [Wait for the network to be ready](#wait_ready)  
* [Add the interface without an IP address](#no_ip)  
* [DHCP](#dhcp)  
* [DHCP Options](#dhcp_options)
* [Specify a custom MAC address](#custom_mac)  
* [Virtual LAN (VLAN)](#vlan)  
* [Support Open vSwitch](#openvswitch)  
* [Support Infiniband](#infiniband)
* [Cleanup](#cleanup)  


<a name="notes"/>
### Things to note

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
  v.customize ['modifyvm', :id, '--nicpromisc1', 'allow-all']
end
```

#### Docker

**Before using Pipework, please ask on the [docker-user mailing list](
https://groups.google.com/forum/#!forum/docker-user) if there is a "native"
way to achieve what you want to do *without* Pipework.**

In the long run, Docker will allow complex scenarios, and Pipework should
become obsolete.

If there is really no other way to plumb your containers together with
the current version of Docker, then okay, let's see how we can help you!

The following examples show what Pipework can do for you and your containers.


<a name="lamp"/>
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


<a name="docker_integration"/>
### Docker integration

Pipework can resolve Docker containers names. If the container ID that
you gave to Pipework cannot be found, Pipework will try to resolve it
with `docker inspect`. This makes it even simpler to use:

    docker run -name web1 -d apache
    pipework br1 web1 192.168.12.23/24


<a name="peeking_inside"/>
### Peeking inside the private network

Want to connect to those containers using their private addresses? Easy:

    ip addr add 192.168.1.254/24 dev br1

Voilà!

<a name="setting_internal"/>
### Setting container internal interface ##
By default pipework creates a new interface `eth1` inside the container. In case you want to change this interface name like `eth2`, e.g., to have more than one interface set by pipework, use:

`pipework br1 -i eth2 ...`

**Note:**: for infiniband IPoIB interfaces, the default interface name is `ib0` and not `eth1`.

<a name="setting_host"/>
### Setting host interface name ##
By default pipework will create a host-side interface with a fixed prefix but random suffix. If you would like to specify this interface name use the `-l` flag (for local):

`pipework br1 -i eth2 -l hostapp1 ...`

<a name="different_netmask"/>
### Using a different netmask

The IP addresses given to `pipework` are directly passed to the `ip addr`
tool; so you can append a subnet size using traditional CIDR notation.

I.e.:

    pipework br1 $CONTAINERID 192.168.4.25/20

Don't forget that all containers should use the same subnet size;
pipework is not clever enough to use your specified subnet size for
the first container, and retain it to use it for the other containers.


<a name="default_gateway"/>
### Setting a default gateway

If you want *outbound* traffic (i.e. when the containers connects
to the outside world) to go through the interface managed by
Pipework, you need to change the default route of the container.

This can be useful in some usecases, like traffic shaping, or if
you want the container to use a specific outbound IP address.

This can be automated by Pipework, by adding the gateway address
after the IP address and subnet mask:

    pipework br1 $CONTAINERID 192.168.4.25/20@192.168.4.1


<a name="local_physical"/>
### Connect a container to a local physical interface

Let's pretend that you want to run two Hipache instances, listening on real
interfaces eth2 and eth3, using specific (public) IP addresses. Easy!

    pipework eth2 $(docker run -d hipache /usr/sbin/hipache) 50.19.169.157/24
    pipework eth3 $(docker run -d hipache /usr/sbin/hipache) 107.22.140.5/24

Note that this will use `macvlan` subinterfaces, so you can actually put
multiple containers on the same physical interface.


<a name="macvlan"/>
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


<a name="wait_ready"/>
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

<a name="no_ip"/>
### Add the interface without an IP address

If for some reason you want to set the IP address from within the
container, you can use `0/0` as the IP address. The interface will
be created, connected to the network, and assigned to the container,
but without configuring an IP address:

    pipework br1 $CONTAINERID 0/0


<a name="dhcp"/>
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


<a name="dhcp_options"/>
### DHCP Options

You can specify extra DHCP options to be passed to the DHCP client
by adding them with a semi-colon. For instance:

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


<a name="custom_mac"/>
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

**Note:**  Setting the MAC address of an IPoIB interface is not supported.
<a name="vlan"/>
### Virtual LAN (VLAN)

If you want to attach the container to a specific VLAN, the VLAN ID can be
specified using the `[MAC]@VID` notation in the MAC address parameter.

**Note:** VLAN attachment is currently only supported for containers to be
attached to either an Open vSwitch bridge or a physical interface. Linux
bridges are currently not supported.

The following will attach container zerorpcworker to the Open vSwitch bridge
ovs0 and attach the container to VLAN ID 10.

    pipework ovsbr0 $(docker run -d zerorpcworker) dhcp @10

<a name="openvswitch"/>
### Support Open vSwitch

If you want to attach a container to the Open vSwitch bridge, no problem.

    ovs-vsctl list-br
    ovsbr0
    pipework ovsbr0 $(docker run -d mysql /usr/sbin/mysqld_safe) 192.168.1.2/24

If the ovs bridge doesn't exist, it will be automatically created

<a name="infiniband"/>
### Support Infiniband IPoIB

Passing an IPoIB interface to a container is supported.  However, the entire device
is moved into the network namespace of the container.  It therefore becomes hidden
from the host.  

To provide infiniband to multiple containers, use SR-IOV and pass
the virtual function devices to the containers.
  
<a name="cleanup"/>
### Cleanup

When a container is terminated (the last process of the net namespace exits),
the network interfaces are garbage collected. The interface in the container
is automatically destroyed, and the interface in the docker host (part of the
bridge) is then destroyed as well.
