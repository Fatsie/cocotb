# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

TOPLEVEL_LANG ?= vhdl
TOPLEVEL := test
VHDL_SOURCES := test.vhdl
MODULE := test_issue3769

ifneq ($(filter $(SIM),ius xcelium),)
COMPILE_ARGS += -v93
endif

ifneq ($(shell echo $(TOPLEVEL_LANG) | tr A-Z a-z),vhdl)
all:
	@echo "Skipping test since only VHDL is supported"
clean::
else
ifeq ($(SIM),xcelium)
.PHONY: override_for_this_test
# This test is expected to fail until a fix exists.
override_for_this_test:
	if $(MAKE) all; then echo "Expected this to fail"; false; else echo "Failed as expected"; fi
endif
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
