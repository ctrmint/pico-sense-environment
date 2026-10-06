"""Keep boot minimal so the USB REPL stays recoverable."""
import gc
import micropython
micropython.alloc_emergency_exception_buf(100)
gc.collect()
