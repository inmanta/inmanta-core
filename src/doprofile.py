import cProfile
import pstats
import ParserBench

result = cProfile.run('ParserBench.parserV4()',"run.profile")
p = pstats.Stats('run.profile')
p.strip_dirs().sort_stats("time").print_stats(20)

