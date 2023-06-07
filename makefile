## makefile automates the build and deployment for python projects

PROJ_TYPE =		python
PROJ_MODULES =		git python-resources python-cli python-doc python-doc-deploy
ENTRY =			./datdesc

include ./zenbuild/main.mk


.PHONY:			inttest
inttest:
			mkdir -p target/lat
			$(ENTRY) test-resources/config target/lat
