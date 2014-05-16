NAME=pipework
DESCRIPTION="Software-Defined Networking for Linux Containers"
URL=https://jpetazzo.github.io/
VERSION=0.1.0
VENDOR=jpetazzo
PREFIX=alti
BUILD_NUMBER?=1

all: package

package:
	fpm -s dir -t rpm -v $(VERSION) $(DEP_FLAG) \
		--epoch 1 \
		--name $(PREFIX)-$(NAME) \
		--description $(DESCRIPTION) \
		--vendor $(VENDOR) \
		--url $(URL) \
		--license 'Apache License, Version 2.0' \
		--iteration $(BUILD_NUMBER) \
		--rpm-group 'users' \
		--prefix /usr/sbin \
		pipework

clean:
	rm -f *.rpm
