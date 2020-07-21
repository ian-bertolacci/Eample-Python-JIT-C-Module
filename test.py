#!/usr/bin/env python3
import sys, subprocess, os, shutil, glob, itertools, re, datetime, importlib.util

def abspath_listdir( dir ):
  # os.listdir gives path relative to dir
  for dir_rel_file_path in os.listdir( dir ):
    # Yield absolute path to file
    yield os.path.abspath( os.path.join( dir, dir_rel_file_path) )

class ModuleLoader:
  def __init__(self, name, source_dir, install_dir=None, clean_on_context_exit=True):
    self.name = name
    self.source_dir = os.path.abspath( source_dir )
    # Directory where module object will be stored
    self.install_dir = os.path.abspath( install_dir if install_dir != None else os.path.join( os.getcwd(), "install" ) )
    # Full path to module object
    self.module_object_path = os.path.join( self.install_dir, f"{name}.so" )

    # None if module has not been previously built, self.install_dir otherwise
    self.existing_install = None
    # None if module has not been imported, module namespace for this module otherwise
    self.existing_import = None

    # Files and directories to be removed on clean
    self.remove = []
    # For use with the context manager
    # True if cleanup() should occur when exiting the context manager, False otherwise
    self.clean_on_context_exit = clean_on_context_exit

  # load the module. Build and import if necessary, use existing if available
  def load(self):
    if self.existing_install == None:
      self.existing_install = self.build()

    if self.existing_import == None:
      self.existing_import = self.hot_import()

    return self.existing_import


  # Build source into shared object
  def build(self):
    # Does install location exist and is it a directory?
    if os.path.exists( self.install_dir ):
      if not os.path.isdir( self.install_dir ):
        raise RuntimeError( f"Cannot create or use install path \"{self.install_dir}\". It already exists and is not a directory." )
    else:
      os.makedirs( self.install_dir )
      self.remove.append( self.install_dir )

    def check_build( completed_process ):
      if completed_process.returncode != 0:
        raise RuntimeError( f"Failed to execute \"{' '.join( completed_process.args )}\" ({completed_process.returncode})\nstdout:{completed_process.stdout.decode('utf-8')}\nstderr:{completed_process.stderr.decode('utf-8')}" )
      return completed_process

    # Call python3 config to get proper python specific compilation flags
    python3_config_completed_process = check_build( subprocess.run( ["python3-config", "--cflags"], stdout=subprocess.PIPE, stderr=subprocess.PIPE ) )

    # Setup build command
    python3_flags = re.split( "\s+", python3_config_completed_process.stdout.decode("utf-8").strip() )
    build_command = [ "gcc", os.path.join( self.source_dir, f"{self.name}.c" ), "-o", self.module_object_path, "--shared" ] + python3_flags

    # perform build
    build_completed_process = check_build( subprocess.run( build_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE ) )

    self.remove.append( self.module_object_path )

    return self.module_object_path

  # Import module as a module object and return it
  def hot_import(self):
    spec = importlib.util.spec_from_file_location( self.name, self.module_object_path )
    module = importlib.util.module_from_spec( spec )
    spec.loader.exec_module(module)
    return module

  def cleanup(self):
    self.remove.sort()
    self.remove.reverse()
    for thing in self.remove:
      if os.path.isdir( thing ):
          if len( list( abspath_listdir( thing ) ) ) > 0:
            print( f"Cannot remove directory \"{thing}\": directory not empty." )
            # skip and move on
            continue
          os.removedirs( thing )

      elif os.path.isfile(thing):
        os.remove( thing )
        # Note: the above works for both regular files and links

      else:
        print( f"Path to object \"{thing}\" does not exist." )

  def __enter__(self):
    return self.load()

  def __exit__(self, type, value, traceback):
    if self.clean_on_context_exit:
      self.cleanup()


def main( ):
  # Specify my module, load, and cleanup explicitly
  my_module_loader = ModuleLoader( "mymodule", "./src", "./bin" )
  # Build and import, my_module is the module
  my_module = my_module_loader.load()
  # Call hello_world function in module
  my_module.hello_world()
  # Cleanup the module, including deleting generated files.
  # Note: Not sure what happens with the module object.
  # I would assume nothing, since it's already loaded in to memory
  # but it could be invalid to use it afterwards
  my_module_loader.cleanup()

  # Manage module state with context manager, which loads/cleans on entry/exit
  with ModuleLoader( "mymodule", "./src", "./bin" ) as m:
    m.hello_world()


if __name__ == "__main__":
  main( )
