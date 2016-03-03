* Replace the relevant functions with a class and make `opt_use_modtime`,
  `opt_dirs`, and `strace_re` members of this class.

* Come put with a more practical example than the original one, maybe a small C
  program.

* Decouple file tracing from `strace` so we can use `truss` and other similar
  tools.
