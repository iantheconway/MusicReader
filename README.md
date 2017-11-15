# 
Overview
============
An open source tool which generates sheet music for the purpose of practicing sight reading.

Dependencies
============
Currently, this project only supports Mac OS
* Python 2.7
* Flask
* Tensorflow
* Magenta
* GNU Lilypond (Mac App is included for convenience)
* Numpy

AI_Composer for Neural Network mode: https://github.com/llSourcell/AI_Composer

Basic Usage
===========

Assuming all the dependencies are installed:

python WebReader.py 

in your web browser, go to:

http://127.0.0.1:5000/notereader

Credits
===========

Rendering of the sheet music is done in GNU Lilypond. One of the modes of music generation uses Google Magenta: https://magenta.tensorflow.org/