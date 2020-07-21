CC=gcc
CC_FLAGS = $(shell python3-config --cflags) -ggdb

SRC_DIR?=.
INSTALL_DIR?=.

MODULE_NAME?=mymodule

LIBRARY=$(INSTALL_DIR)/$(MODULE_NAME).so

all: $(LIBRARY)

$(LIBRARY): %.so : %.c
	$(CC) $^ -o $@ --shared $(CC_FLAGS)

clean:
	- /bin/rm ./*.so ./*.o
