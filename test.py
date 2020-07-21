#!/usr/bin/env python3
import sys, subprocess, os, importlib.util, shutil, glob
import itertools, re, time, datetime, argparse

def indentstr( string, depth=1, indent="  ", split_on="\n", newline="\n", first_line=True, trailing_line=False ):
  indentation = indent*depth
  indented_string = ""
  indented_string += indentation if first_line else ""
  indented_string += re.sub( f"{newline}(?!$)", f"{newline}{indentation}", string )
  indented_string += indentation if trailing_line else ""
  return indented_string


# Like listdir, but with absolute paths
def listabsdir( dir ):
  return [ os.path.abspath( os.path.join( dir, dir_rel_file_path) ) for dir_rel_file_path in os.listdir( dir ) ]


class ModuleLoader:
  def __init__(self, name, source_dir, install_dir=None, clean_on_context_exit=True, verbose=False):
    self.verbose = verbose

    self.name = name
    self.source_dir = os.path.abspath( source_dir )
    # Directory where module object will be stored
    self.install_dir = os.path.abspath( install_dir if install_dir != None else os.path.join( os.getcwd(), "install" ) )
    # Full path to module object
    self.module_object_path = os.path.join( self.install_dir, f"{name}.so" )

    # None if module has not been previously built, self.install_dir otherwise
    # Immediately check for existing module object
    self.existing_install = self.module_object_path if os.path.isfile( self.module_object_path ) else None
    # None if module has not been imported, module namespace for this module otherwise
    self.existing_import = None

    # Files and directories to be removed on clean
    self.remove = []
    # For use with the context manager
    # True if cleanup() should occur when exiting the context manager, False otherwise
    self.clean_on_context_exit = clean_on_context_exit

    if self.verbose and self.existing_install:
      print( f"Detected previous object file {self.existing_install}" )


  # load the module. Build and import if necessary, use existing if available
  def load(self):
    if self.existing_install == None:
      if self.verbose:
        print( "No pre-existing build." )
      self.existing_install = self.build()
    elif self.verbose:
      print( f"Source previously built in {self.existing_install }" )

    if self.existing_import == None:
      if self.verbose:
        print( "No previously imported module." )
      self.existing_import = self.hot_import()
    elif self.verbose:
      print( f"Module already imported." )

    return self.existing_import


  # Build source into shared object
  def build(self):
    # Does install location exist and is it a directory?
    if os.path.exists( self.install_dir ):
      # Path does exist (which is fine) but is not a directory (which is not fine)
      if not os.path.isdir( self.install_dir ):
        raise RuntimeError( f"Cannot create or use install path \"{self.install_dir}\". It already exists and is not a directory." )
      elif self.verbose:
        print( f"Using pre-existing directory {self.install_dir}" )
    # Path does not exist, so create it (and any parent directories that need to be created).
    else:
      if self.verbose:
        print( f"Creating {self.install_dir}" )
      os.makedirs( self.install_dir )
      self.remove.append( self.install_dir )

    # Simple wrapper to make sure exit code was successful, or raise error if it was not.
    def check_build( completed_process, vaid_statuses=set([0]) ):
      stdout = completed_process.stdout.decode('utf-8')
      stderr = completed_process.stderr.decode('utf-8')
      status = "successful" if completed_process.returncode in vaid_statuses else "failed"
      report_str = f"Execution of {' '.join( completed_process.args )} {status} with status {completed_process.returncode}.\n" + indentstr( f"stdout:\n{indentstr(stdout)}\nstderr:\n{indentstr(stderr)}" )
      if completed_process.returncode not in vaid_statuses:
        # raise RuntimeError( f"Execution of {' '.join( completed_process.args )} failed with status {completed_process.returncode}\n" + indentstr( f"stdout:\n{indentstr(stdout)}\nstderr:\n{indentstr(stderr)}" ) )
        raise RuntimeError( report_str )
      if self.verbose:
        sep = "-"*80
        print( f"{sep}\n{report_str}\n{sep}" )
      return completed_process

    # Call python3 config to get proper python specific compilation flags
    if self.verbose:
      print( "Checking Python configuration cflags" )
    python3_config_completed_process = check_build( subprocess.run( ["python3-config", "--cflags"], stdout=subprocess.PIPE, stderr=subprocess.PIPE ) )

    # Setup build command
    python3_flags = re.split( "\s+", python3_config_completed_process.stdout.decode("utf-8").strip() )
    build_command = [ "gcc", os.path.join( self.source_dir, f"{self.name}.c" ), "-o", self.module_object_path, "--shared" ] + python3_flags

    if self.verbose:
      print( "Building Python C module using following command:" )
      print( build_command[0], end="" )
      sources=True # Source(s) come immediately after the command, so can print non flag parts (i.e. strings that do not begin with "-") as source until first flag
      for part in build_command[1:]:
        # flags and sources should go on newline (with continuing slash) and be indented
        flag = part[0] == "-"
        sources = sources and not flag # End source mode when flag appears
        indent = sources or flag

        if indent:
          print( f" \\\n  {part}", end='' )
        # arguments to flags go on same line
        else:
          print( f" {part}",  end='' )
      print()

    # perform build
    build_completed_process = check_build( subprocess.run( build_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE ) )

    self.remove.append( self.module_object_path )

    if self.verbose:
      print( "Build successful" )

    return self.module_object_path


  # Import module as a module object and return it
  def hot_import(self):
    # Load a module specification (or a 'spec') for a file path (much easier than trying to derive some import path)
    # Note: a module spec seems to be just an object that says where the module is, and some caching stuff.
    spec = importlib.util.spec_from_file_location( self.name, self.module_object_path )
    # 'Create' module from spec
    module = importlib.util.module_from_spec( spec )
    # Actually execute and load the module
    spec.loader.exec_module(module)
    # Return the module object which can be used like a regular imported module
    return module


  # Remove any files and directories created by the execution of this ModuleLoader
  #  Note: Does *not* remove directories if they contain files *not* created by this ModuleLoader.
  def cleanup(self):
    # Sort in reverse to get things in bottom-up order.
    # Mostly important to have the files inside a directory come before the directory itself.
    self.remove.sort( reverse=True )

    if self.verbose:
      if len(self.remove) > 0:
        print( f"Removing files:\n" + indentstr( '\n'.join( self.remove ) ) )
      else:
        print( "No files to clean." )

    for thing in self.remove:
      if self.verbose:
        print( f"Removing {thing}" )
      # If path is a directory, make sure it is empty before deleting.
      # This is to ensure that no non-ModuleLoader files,
      # which could be important, are not deleted
      if os.path.isdir( thing ):
          files = listabsdir( thing )
          if len( files  ) > 0:
            if self.verbose:
              file_str = "\n".join( files )
              print( f"  Cannot remove non-empty directory \"{thing}\". Contains:\n{indentstr(file_str)}" )
            # skip and move on
            continue
          os.removedirs( thing )

      # If this is a file (or link) simply remove.
      elif os.path.isfile(thing):
        os.remove( thing )

      # Path does not exist
      else:
        if self.verbose:
          print( f"  Path to \"{thing}\" does not exist." )


  # Upon entering a 'with ... as' block, load and return the module
  def __enter__(self):
    if self.verbose:
      print("Entering context")
    try:
      module = self.load()
    except Exception as exception:
      # Cleanup and exit
      if self.clean_on_context_exit:
        self.cleanup()
      raise exception
    return module

  # Upon exiting a 'with ... as', cleanup (if set) the module files
  def __exit__(self, type, value, traceback):
    if self.verbose:
      print( "Exiting context" )
    if self.clean_on_context_exit:
      self.cleanup()


def run_demo( name, source, bin, verbose, clean ):
  # Manage module state with context manager, which loads/cleans on entry/exit
  print( "Using ModuleLoader context manager" )
  with ModuleLoader( name, source, bin, clean, verbose ) as m:
    m.hello_world()

    # Specify my module, load, and cleanup explicitly
  print( "Explicitly invoking ModuleLoader API" )
  my_module_loader = ModuleLoader( name, source, bin, clean, verbose )
  # Build and import, my_module is the module
  my_module = my_module_loader.load()
  # Call hello_world function in module
  my_module.hello_world()
  # Cleanup the module, including deleting generated files.
  # Note: Not sure what happens with the module object.
  # I would assume nothing, since it's already loaded in to memory
  # but it could be invalid to use it afterwards
  my_module_loader.cleanup()


def main( argv ):
  # Path to script and its parent directory
  script_file = os.path.abspath( argv[0] )
  script_dir = os.path.dirname( script_file )

  parser = argparse.ArgumentParser( description="Demonstrate building and loading Python C module in runtime" )
  parser.add_argument( "-v", "--verbose",     help="Run with verbose output",                                                   action="store_true", default=False  )
  parser.add_argument( "-d", "--no-clean",    help="Do not clean created files on module exit",                                 action="store_true", default=False  )
  parser.add_argument( "-n", "--module-name", help="Name of module, and source file to compile",                                type=str,  nargs=1,  default="mymodule" )
  parser.add_argument( "-s", "--source",      help="Location of module source",                                                 type=str,  nargs=1,  default=os.path.join( script_dir, "src") )
  parser.add_argument( "-i", "--install",     help="Directory to install module object (will be created if it does not exist)", type=str,  nargs=1,  default=os.path.join( os.getcwd(), "bin") )

  args = parser.parse_args( argv[1:] )

  if args.verbose:
    print( f"Argument settings:" )
    args_dictionary = vars(args)
    max_len = max( *( len(a) for a in args_dictionary.keys() ) )
    for arg, value in args_dictionary.items():
      print( f"  {arg:>{max_len}}: {value}" )

  run_demo( args.module_name, args.source, args.install, args.verbose, not args.no_clean  )


if __name__ == "__main__":
  main( sys.argv )
