# HDM

This is the repository for the Holographic Declarative Memory (HDM) module for Python ACT-R.

This repository contains:
- sample ACT-R models that use HDM
- the HDM module itself
- code for the Holographic Reduced Representations (HRRs)
- conference papers that describe the theory and applications of HDM

Tutorials on how to use Python ACT-R can be found here: https://sites.google.com/site/pythonactr/home

To install HDM for use on your own computer, use one of the two following methods:

EASY INSTALL

1. Download the CCMSuite repository for Python 2 ACT-R and HDM from https://github.com/MatthewAKelly/ccmsuite

2. Add the CCMSuite folder to your Python Path.

3. Create a Python ACT-R model (see Python ACT-R tutorials).

4. Instead of creating an instance of DM, create an instance of HDM in your model (see example code in this repository).

LESS EASY INSTALL

1. Downloaded the official Python ACT-R for Python 2 from https://github.com/tcstewar/ccmsuite or for Python 3 from https://github.com/sterlingsomers/ccmsuite

2. Download hdm.py from this repository and place it in ccmsuite/ccm/lib/actr/hdm.py

3. Download hrr.py from this repository and use it to replace the one in ccmsuite/ccm/lib/hrr.py

4. Add the line “from ccm.lib.actr.hdm import HDM” to ccmsuite/ccm/lib/actr/__init__.py

5. Add the CCMSuite folder to your Python Path.

6. Create a Python ACT-R model (see Python ACT-R tutorials).

7. Instead of creating an instance of DM, create an instance of HDM in your model (see example code in this repository).

USING HDM

To use HDM:

   from ccm.lib.actr import *

   from ccm.lib.actr.hdm import *

 ...

   retrieval=Buffer()

   memory=HDM(retrieval)

The HDM module provides four methods for use by an ACT-R model:

1. The constructor, which takes a retrieval buffer and creates an HDM:
memory = HDM(retrieval)

2. Add a chunk, which takes a chunk and adds it to HDM:
memory.add(chunk)

3. Request a chunk, which takes a chunk and finds the best match in HDM:
memory.request(chunk)

4. Get activation, which takes a chunk and returns the chunk's activation as a cosine in HDM:
memory.get_activation(chunk)