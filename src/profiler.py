import cProfile
from searchPath import searchPath

# cProfile.run('print(searchPath(1972106549, 1587650367))')
# huge
# cProfile.run('print(len(searchPath(2107710616, 2128635872)))')
cProfile.run('print(len(searchPath(2147152912, 307743305)))')
