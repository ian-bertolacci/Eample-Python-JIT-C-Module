# JIT Compile and Load Python C Module
This is a very simple demonstration of JIT compiling an existing C source and
loading it as a python module.

Depends on Python 3.5 or greater.

# Quickstart
```
./test.py
```

Expected output:
```
Hello, World!
Hello, World!
```

# Overview
Below is the project's file structure, with short descriptions for each file.

Example Python JIT C Module
├── Readme.md
│     This file. Describes project and use.
├── src
│   ├── Makefile
│   │     Unnecessary for this project.
│   │     Can be used to independently compile the module and verify that
│   │     compilation and use works separately from the python example
│   └── mymodule.c
│         The source code defining the Python C module.
│         Requires no additional generation of code or modification for it to
│         compile or be loaded as a Python module
└── test.py
      Script demonstrating how to compile the C source for a Python module and
      load it into the Python interpreter at run-time.
