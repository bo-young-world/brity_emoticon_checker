"""Prepare Tcl/Tk before the frozen application imports tkinter."""

import ctypes
import os
import sys


if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS
    os.environ["TCL_LIBRARY"] = os.path.join(bundle_dir, "_tcl_data")
    os.environ["TK_LIBRARY"] = os.path.join(bundle_dir, "_tk_data")

    # Python 3.14.4 on Windows can leave Tcl's library-path cache empty on
    # the first _tkinter.create() call. A bootstrap interpreter initializes it.
    tcl = ctypes.CDLL(os.path.join(bundle_dir, "tcl86t.dll"))
    tcl.Tcl_FindExecutable.argtypes = [ctypes.c_char_p]
    tcl.Tcl_CreateInterp.restype = ctypes.c_void_p
    tcl.Tcl_Init.argtypes = [ctypes.c_void_p]
    tcl.Tcl_Init.restype = ctypes.c_int
    tcl.Tcl_FindExecutable(sys.executable.encode("utf-8"))
    tcl.Tcl_Init(tcl.Tcl_CreateInterp())
