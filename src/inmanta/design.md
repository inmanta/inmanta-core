
# On compile or export
![compile](/home/hugo/Pictures/2022-08-05 14-32-15 compile output.png)
## current behaviour :
> print all loaded modules and their  version after compilation / export

## TODO:
- [ ] move logging **before** compilation / export

## Open questions:

- change to table version ?


-----



# On update or install
![project install](/home/hugo/Pictures/2022-08-05 15-02-02 project install.png)
## current behaviour :

> WHEN:
> - before installation: print state that depends if v1 or v2 (see what to print ? )
> - after installation: print diff  for each individual module (v1) or top level module (v2)
>
> WHAT:
> - v1 module: print state of currently loaded (v1 and v2) modules (in `project.modules)
> - v2 module: print state of currently installed v2 modules (in `PythonWorkingSet)

## TODO:
- [ ] add constraints information


----


# Log pip output
## current behaviour:
> The full output is logged

## TODO:
- [ ] only log relevant lines

## Open question:
- relevant lines == ? "Successfully installed ..." ? anything else ?
