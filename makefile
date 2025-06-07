#@meta {author: "Paul Landes"}
#@meta {desc: "automate build and deploy of the project", date: "2025-06-07"}


## Build
#
PROJ_TYPE =		python
PROJ_MODULES =		python/doc


## Includes
#
include ./zenbuild/main.mk


## Targets
#
# integration test
.PHONY:			testint
testint:
			@echo "running integration test"
			@mkdir -p target/lat
			@make pyinvoke ARG="table test-resources/config target/lat"
			( cd target/lat ; \
			  for i in * ; do \
				diff $$i ../../test-resources/gold/$$i ; \
			  done )

.PHONY:			testall
testall:		test testint
