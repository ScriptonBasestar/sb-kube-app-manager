# sbkube Makefile
# Main Makefile - imports all targets from .make/ directory

# Include all Makefile fragments
include .make/help.mk
include .make/install.mk
include .make/dev.mk
include .make/build.mk
include .make/test.mk
include .make/lint.mk
include .make/ci.mk
include .make/status.mk
include .make/clean.mk
