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
			$(eval dte=$(shell date +'%Y/%m/%d'))
			@mkdir -p target/lat
			@make pyinvoke PY_INVOKE_ARG="-e testcur" \
				ARG="table test-resources/config target/lat"
			@( cd target/lat ; \
			  for i in * ; do \
				sed -i 's@$(dte)@{{DATE}}@' $$i ; \
				truncate -s -1 $$i ; \
				diff $$i ../../test-resources/gold/$$i ; \
			  done )

.PHONY:			testall
testall:		test testint
