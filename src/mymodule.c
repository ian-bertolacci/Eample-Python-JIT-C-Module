#include <Python.h>

// Lots of this adapted from https://docs.python.org/3/extending/extending.html

#if PY_MAJOR_VERSION < 3
  #error "Cannot build using Python version < 3."
#endif

// Implementation of mymodule.run()
static PyObject *mymodule_hello_world(PyObject *module, PyObject *args) {
  printf( "Hello, World!\n" );
  Py_RETURN_NONE;
}

// Create namespace mapping between module's python methods and the C functions implementing them.
static PyMethodDef mymodule_methods[] = {
  // Map start -> mymodule_hello_world
  {
    // method name
    .ml_name  = "hello_world",
    // Actual method
    .ml_meth  = (PyCFunction) mymodule_hello_world,
    // Flags for method arguments
    .ml_flags = METH_NOARGS,
    // Pointer to documentation for method
    .ml_doc   = NULL
  },

  // Termination sentinal (ends the list)
  { NULL, NULL, 0, NULL }
};

static struct PyModuleDef mymodule_module_definition = {
  // Start sentinal?
  .m_base = PyModuleDef_HEAD_INIT,
  // name of module
  .m_name = "mymodule",
  // Pointer to module documentation string, may be NULL */
  .m_doc  = NULL,
  // Size of per-interpreter state of the module; -1 indicates the module keeps state in global variables
  .m_size = -1,
  // module's PyMethodDef array
  .m_methods = mymodule_methods
};

// Function that actually creates the module object for the python interpreter
PyMODINIT_FUNC PyInit_mymodule(void) {
  PyObject *module = PyModule_Create( &mymodule_module_definition );
  return module;
}
