import os
import re
import sys
import ast
#import astor
import json
import nbformat
#from nbconvert import PythonExporter
from Dene.core.mnode import MNode
from Dene.core.util import  UnitWalker
#from scalpel.SSA.ssa import Dene
from Dene.dene.ssa import Dene
from Dene.util import  get_path_by_ext
from test_syntax_desugar import rewrite

# we need to define cretieras for variables
def filter_line(line):
    if len(line)==0:
        return False

    if line[0] in ['%', '!', '?']:
        return False

    if line.split(' ')[0]  in ["cat", "ls", "mkdir", "less", "sudo", "cd"]:
        return False
    return True


def get_name_from_msg(msg):
    patter = r"/'((?:''|[^'])*)'/"
    idx2 = msg.find("is not defined")
    groups = re.findall(r"\'(.+?)\'", msg[idx2-30:idx2])
    if len(groups)>0:
        return groups[-1]
    return None

def code_syntax_check(src_path):
    src = open(src_path).read()
    fn = os.path.basename(src_path)
    try:
        tree = ast.parse(src)
    except Exception as e:
        #print(e)
        os.system('2to3 '+ src_path + ' -n -W  --output-dir=tmp/')
        src = open('./tmp/'+fn).read()
    return src

def detect(source):
    module_node = ast.parse(source)
    
    Walker = UnitWalker(module_node)
    for unit in Walker:
        new_stmts = rewrite(unit.node)
        unit.insert_stmts_before(new_stmts)
        pass
    new_ast = ast.fix_missing_locations(module_node)
    mnode = MNode("local")
   
    mnode.ast = new_ast
    ast_node = new_ast
    if ast_node is None: 
        #print('syntax')
        return []
    cfg = mnode.gen_cfg()

    detector = Dene(source)
    undefined_names = detector.compute_undefined_names(cfg)
    print(undefined_names)
    results = [(name["name"], name["scope"]) for name in undefined_names]
    results = list(set(results))
    return results

def run_dene_single(source):
    results = detect(source)
    for r in results:
        print(r)

def run_dene_batch():
    
    folder_path = sys.argv[1]
    
    folder_name = os.path.dirname(folder_path)
    test_report = {"repo_name":folder_name, "error_file": {}}

    all_fns = get_path_by_ext(folder_path)

    
    for fn in all_fns:
        src_path = fn
        try:
            #src = code_syntax_check(src_path)
            src = open(src_path).read()
            
            if src.find("import *")>=0:
        #        print('IMPORT STAR')
                continue
            if src.find("get_ipython()")>=0:
                continue
       
            undefined_idents = detect(src)
            test_report["error_file"][fn] = undefined_idents
         
        except Exception as e:
            print(fn, e)
            n_all_files = 0

    for k, v in test_report["error_file"].items():
        print(k, v)
if __name__ == '__main__':
    input_path = sys.argv[1]
    if os.path.isfile(input_path):
        src = open(input_path).read()
        run_dene_single(src)
    else:
        run_dene_batch()

   
