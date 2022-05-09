import timeit, time, gc, itertools, shlex, getopt, ast, traceback, sys, math, pstats
import cProfile as profile
from pathlib import Path
from io import StringIO
#Below check copied from IPython source code, https://github.com/ipython/ipython/blob/a2c2a2dcec36224c7dca561efcf9ed9e5c514c3c/IPython/utils/timing.py#L23-L67
try:
    import resource
    def clocku():
        """clocku() -> floating point number
        Return the *USER* CPU time in seconds since the start of the process.
        This is done via a call to resource.getrusage, so it avoids the
        wraparound problems in time.clock()."""
        
        return resource.getrusage(resource.RUSAGE_SELF)[0]
    
    def clocks():
        """clocks() -> floating point number
        Return the *SYSTEM* CPU time in seconds since the start of the process.
        This is done via a call to resource.getrusage, so it avoids the
        wraparound problems in time.clock()."""
        
        return resource.getrusage(resource.RUSAGE_SELF)[1]
    
    def clock():
        """clock() -> floating point number
        Return the *TOTAL USER+SYSTEM* CPU time in seconds since the start of
        the process.  This is done via a call to resource.getrusage, so it
        avoids the wraparound problems in time.clock()."""
        
        u,s = resource.getrusage(resource.RUSAGE_SELF)[:2]
        return u+s
    
    def clock2():
        """clock2() -> (t_user,t_system)
        Similar to clock(), but return a tuple of user/system times."""
        return resource.getrusage(resource.RUSAGE_SELF)[:2]
except ImportError:
    # There is no distinction of user/system time under windows, so we just use
    # time.perff_counter() for everything...
    clocku = clocks = clock = time.perf_counter
    def clock2():
        """Under windows, system CPU time can't be measured.
        This just returns perf_counter() and zero."""
        return time.perf_counter(),0.0

#Below function copied from IPython source code, https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L1466-L1503
def _format_time(timespan, precision=3):
    if timespan >= 60.0:
        parts = [("d", 60*60*24),("h", 60*60),("min", 60), ("s", 1)]
        time = []
        leftover = timespan
        for suffix, length in parts:
            value = int(leftover / length)
            if value > 0:
                leftover = leftover % length
                time.append(u'%s%s' % (str(value), suffix))
            if leftover < 1:
                break
        return " ".join(time)
    
    units = [u"s", u"ms",u'us',"ns"] # the save value   
    if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
        try:
            u'\xb5'.encode(sys.stdout.encoding)
            units = [u"s", u"ms",u'\xb5s',"ns"]
        except:
            pass
    scaling = [1, 1e3, 1e6, 1e9]
    if timespan > 0.0:
        order = min(-int(math.floor(math.log10(timespan)) // 3), 3)
    else:
        order = 3
    return u"%.*g %s" % (precision, timespan * scaling[order], units[order])

#Below function has content copied from IPython source code, https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L305-L379
def _run_with_profiler(code, opts, namespace):
        opts = dict(opts)
        prof = profile.Profile()
        try:
            prof = prof.runctx(code, namespace, namespace)
            sys_exit = ''
        except SystemExit:
            sys_exit = """*** SystemExit exception caught in code being profiled."""
        
        stats = pstats.Stats(prof).strip_dirs().sort_stats(*opts.get('s', ['time']))
        
        lims = opts.get('l', [])
        if lims:
            lims, lims_ = [], lims  # rebuild lims with ints/floats/strings
            for lim in lims_:
                try:
                    lims.append(int(lim))
                except ValueError:
                    try:
                        lims.append(float(lim))
                    except ValueError:
                        lims.append(lim)
        
        # Trap output.
        stdout_trap = StringIO()
        stats_stream = stats.stream
        try:
            stats.stream = stdout_trap
            stats.print_stats(*lims)
        finally:
            stats.stream = stats_stream
        
        output = stdout_trap.getvalue()
        output = output.rstrip()
        
        if 'q' not in opts:
            page.page(output)
        print(sys_exit, end=' ')
        
        dump_file = opts.D[0]
        text_file = opts.T[0]
        if dump_file:
            prof.dump_stats(dump_file)
            print(
                f"\n*** Profile stats marshalled to file {repr(dump_file)}.{sys_exit}"
            )
        if text_file:
            pfile = Path(text_file)
            pfile.touch(exist_ok=True)
            pfile.write_text(output)

            print(
                f"\n*** Profile printout saved to text file {repr(text_file)}.{sys_exit}"
            )
        
        if 'r' in opts:
            return stats
        
        return None

#Below class copied from IPython source code, https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L60-L110
class TimeitResult(object):
    """
    Object returned by the timeit magic with info about the run.
    Contains the following attributes :
    loops: (int) number of loops done per measurement
    repeat: (int) number of times the measurement has been repeated
    best: (float) best execution time / number
    all_runs: (list of float) execution time of each run (in s)
    compile_time: (float) time of statement compilation (s)
    """
    def __init__(self, loops, repeat, best, worst, all_runs, compile_time, precision):
        self.loops = loops
        self.repeat = repeat
        self.best = best
        self.worst = worst
        self.all_runs = all_runs
        self.compile_time = compile_time
        self._precision = precision
        self.timings = [ dt / self.loops for dt in all_runs]
    
    @property
    def average(self):
        return math.fsum(self.timings) / len(self.timings)
    
    @property
    def stdev(self):
        mean = self.average
        return (math.fsum([(x - mean) ** 2 for x in self.timings]) / len(self.timings)) ** 0.5
    
    def __str__(self):
        pm = '+-'
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
            try:
                u'\xb1'.encode(sys.stdout.encoding)
                pm = u'\xb1'
            except:
                pass
        return (
            u"{mean} {pm} {std} per loop (mean {pm} std. dev. of {runs} run{run_plural}, {loops} loop{loop_plural} each)"
                .format(
                    pm = pm,
                    runs = self.repeat,
                    loops = self.loops,
                    loop_plural = "" if self.loops == 1 else "s",
                    run_plural = "" if self.repeat == 1 else "s",
                    mean = _format_time(self.average, self._precision),
                    std = _format_time(self.stdev, self._precision))
                )

#Below class copied from IPython source code, https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L117-L139
class TimeitTemplateFiller(ast.NodeTransformer):
    """Fill in the AST template for timing execution.
    This is quite closely tied to the template definition, which is in
    :meth:`ExecutionMagics.timeit`.
    """
    def __init__(self, ast_setup, ast_stmt):
        self.ast_setup = ast_setup
        self.ast_stmt = ast_stmt
    
    def visit_FunctionDef(self, node):
        "Fill in the setup statement"
        self.generic_visit(node)
        if node.name == "inner":
            node.body[:1] = self.ast_setup.body
        
        return node
    
    def visit_For(self, node):
        "Fill in the statement to be timed"
        if getattr(getattr(node.body[0], 'value', None), 'id', None) == 'stmt':
            node.body = self.ast_stmt.body
        return node

#Below class copied from IPython source code, https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L142-L167
class Timer(timeit.Timer):
    """Timer class that explicitly uses self.inner
    
    which is an undocumented implementation detail of CPython,
    not shared by PyPy.
    """
    # Timer.timeit copied from CPython 3.4.2
    def timeit(self, number=timeit.default_number):
        """Time 'number' executions of the main statement.
        To be precise, this executes the setup statement once, and
        then returns the time it takes to execute the main statement
        a number of times, as a float measured in seconds.  The
        argument is the number of times through the loop, defaulting
        to one million.  The main statement, the setup statement and
        the timer function to be used are passed to the constructor.
        """
        it = itertools.repeat(None, number)
        gcold = gc.isenabled()
        gc.disable()
        try:
            timing = self.inner(it, self.timer)
        finally:
            if gcold:
                gc.enable()
        return timing

#Implementation of %prun
def magic_prun(parameter_s=''):
    opts, arg_str = getopt.getopt(parameter_s, 'D:l:rs:T:q')
    return _run_with_profiler(arg_str, opts, globals())

#Implementation of %timeit
def magic_timeit(line='', local_ns=None):
    opts, stmt = getopt.getopt(shlex.split(line), 'n:r:s:tcp:qo')
    if not stmt:
        return
    
    timefunc = timeit.default_timer
    setupstmt = '\n'.join([x[1] for x in opts if x[0] == '-s'])
    stmt = '\n'.join(stmt)
    opts = dict(opts)
    number = int(opts.get("n", 0))
    default_repeat = 7 if timeit.default_repeat < 7 else timeit.default_repeat
    repeat = int(opts.get("r", default_repeat))
    precision = int(opts.get("p", 3))
    quiet, return_result = 'q' in opts, 'o' in opts
    if 'c' in opts:
        timefunc = clock
    elif 't' in opts:
        timefunc = time.time
    
    timer = Timer(timer=timefunc)
    valid = True
    try:
        setupstmt = compile(setupstmt, "<timeit-magic-setup>", "exec", ast.PyCF_ONLY_AST)
    except SyntaxError:
        valid = False
        traceback.print_exc()
    
    try:
        stmt = compile(stmt, "<timeit-magic-stmt>", "exec", ast.PyCF_ONLY_AST)
    except SyntaxError:
        if valid is not False: valid = False
        traceback.print_exc()
    
    if valid:
        timeit_ast_template = ast.parse('def inner(_it, _timer):\n'
                                        '    setupstmt\n'
                                        '    _t0 = _timer()\n'
                                        '    for _i in _it:\n'
                                        '        stmt\n'
                                        '    _t1 = _timer()\n'
                                        '    return _t1 - _t0\n')
        timeit_ast = TimeitTemplateFiller(setupstmt, stmt).visit(timeit_ast_template)
        timeit_ast = ast.fix_missing_locations(timeit_ast)
        tc_min = 0.1
        t0 = clock()
        code = compile(timeit_ast, "<timeit-magic>", "exec")
        tc = clock()-t0
        ns = {}
        glob = globals()
        conflict_globs = {}
        if local_ns:
            for var_name, var_val in glob.items():
                if var_name in local_ns:
                    conflict_globs[var_name] = var_val
            glob.update(local_ns)
        
        exec(code, glob, ns)
        timer.inner = ns["inner"]
        if number == 0:
            for index in range(10):
                number = 10**index
                time_number = timer.timeit(number)
                if time_number >= .2:
                    break
        
        all_runs = timer.repeat(repeat, number)
        best = min(all_runs)/number
        worst = max(all_runs)/number
        timeit_result = TimeitResult(number, repeat, best, worst, all_runs, tc, precision)
        if conflict_globs:
            glob.update(conflict_globs)
        
        if not quiet:
            if worst > 4 * best and best > 0 and worst > 1e-6:
                print("The slowest run took {:.2f} times longer than the "
                      "fastest. This could mean that an intermediate result "
                      "is being cached.".format(worst/best))
            
            print(timeit_result)
            if tc > tc_min:
                print("Compiler time: {:.2f} s".format(tc))
        if return_result:
            return timeit_result

#Below check copied from IPython source code, https://github.com/ipython/ipython/blob/master/IPython/core/magics/execution.py#L46-L52
if sys.version_info > (3,8):
    from ast import Module
else :
    # mock the new API, ignore second argument
    # see https://github.com/ipython/ipython/issues/11590
    from ast import Module as OriginalModule
    Module = lambda nodelist, type_ignores: OriginalModule(nodelist)

#Implementation of %time
def magic_time(line='', local_ns=None):
    tp_min = 0.1
    t0 = clock()
    expr_ast = ast.parse(line)
    tp = clock()-t0
    expr_ast = ast.fix_missing_locations(expr_ast)
    tc_min = 0.1
    expr_val = None
    if len(expr_ast.body)==1 and isinstance(expr_ast.body[0], ast.Expr):
        mode = 'eval'
        source = '<timed eval>'
        expr_ast = ast.Expression(expr_ast.body[0].value)
    else:
        mode = 'exec'
        source = '<timed exec>'
        if len(expr_ast.body) > 1 and isinstance(expr_ast.body[-1], ast.Expr):
            expr_val = expr_ast.body[-1]
            expr_ast = expr_ast.body[:-1]
            expr_ast = Module(expr_ast, [])
    
    t0 = clock()
    code = compile(expr_ast, source, mode)
    tc = clock()-t0
    glob = globals()
    wtime = time.time
    wall_st = wtime()
    if mode == 'eval':
        st = clock2()
        try:
            exec(code, glob, local_ns)
            out = None
            if expr_val is not None:
                code_2 = compile(expr_val, source, 'eval')
                out = eval(code_2, glob, local_ns)
        except:
            traceback.print_exc()
            return
        
        end = clock2()
    
    wall_end = wtime()
    wall_time = wall_end-wall_st
    cpu_user = end[0]-st[0]
    cpu_sys = end[1]-st[1]
    cpu_tot = cpu_user+cpu_sys
    if sys.platform != 'win32':
        print("CPU times: user {}, sys {}, total {}" \
                  .format(_format_time(cpu_user), _format_time(cpu_sys), _format_time(cpu_tot)))
    
    print("Wall time: {}".format(_format_time(wall_time)))
    if tc > tc_min:
        print("Compiler : {}".format(_format_time(tc)))
    
    if tp > tp_min:
        print("Parser   : {}".format(_format_time(tp)))
    
    return out
