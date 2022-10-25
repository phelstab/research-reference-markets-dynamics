python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
cd abides-core
python setup.py install
cd ../abides-markets
python setup.py install
cd ../abides-gym
python setup.py install
cd ..
