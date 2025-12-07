import sys

try:
    import pandas as pd

    has_pandas = True
    v = pd.__version__
except Exception as e:
    has_pandas = False
    v = str(e)

print("Python exe:", sys.executable)
print("Python ver:", sys.version)
print("Pandas ok?:", has_pandas, v)
