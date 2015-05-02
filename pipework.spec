Name: pipework
Version: 20150123
Release: 1%{?dist}
Summary: Software-Defined Networking for Linux Containers
License: Apache License, Version 2.0
URL: https://github.com/jpetazzo/pipework
Source0: https://github.com/jpetazzo/pipework/archive/master.zip

BuildArch: noarch
Requires: /bin/sh
Requires: iproute
Requires: docker-io

%description
Pipework lets you connect together containers in arbitrarily complex scenarios.
Pipework uses cgroups and namespace and works with "plain" LXC containers
(created with lxc-start), and with the awesome Docker.

%prep
%setup -q -n pipework-master

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/usr/bin
install -m 755 pipework $RPM_BUILD_ROOT/usr/bin/pipework

%files
/usr/bin/pipework

%changelog
* Fri Jan 23 2015 Oleg Gashev <oleg@gashev.net> - 20150123
- Initial package.
