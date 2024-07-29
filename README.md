# prj-golivott-l536zhan

# Concolic execution in EXE style with z3 incremental solving mode

## Installation Instructions

A virtual environment is highly recommended

```
$ python3 -m venv $(pwd)/venv
$ . ./venv/activate
```

Install required packages
```
$ pip3 install -r requirements.txt
```

Execute file
```
$ python3 -m wlang.exe wlang/test1.prg
```

## Repo Structure

- `wlang` directory holds all of the code the bulk of the implementation is in `exe.py` and `sym.py`. The other files were all taken from the assingment 2 template.

- Testing files are `wlang\test_exe.py` and `wlang\test_sym.py`. 

- `report.pdf` is the report.