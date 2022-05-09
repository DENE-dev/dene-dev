from functools import reduce
import networkx as nx
import sys
import os
import json
import random
import scipy
from scipy import stats
random.seed(100)

def main():
    base_dir = "RQ2/" 
    all_lib_names = open("top-100.names").readlines()
    n_all_files = 0
    n_error_files = 0
    n_name_errors = 0
    scope_stat = {}
    file_length = []
    file_errors = []
    n_name_errors = 0
    type_stat = {"local": 0, "foreign":0, "unresolved":0}
    count = 0
    for lname in all_lib_names:
        content =  open(os.path.join(base_dir, lname.strip()+".json")).read()
        test_report = json.loads(content)
        n_total_files = len(test_report["error_file"])
        if n_total_files == 0:
                continue
        n_all_files += n_total_files 
        n_this_errors = 0
        n_this_err_files = 0
        for k, v in test_report["error_file"].items():
            name_error_lst = set()
            for err in v:
                rec = (err["name"], err["scope"], err["type"])
                name_error_lst.add(rec)
            n_name_errors += len(name_error_lst)
            if len(name_error_lst)>0:
                n_error_files += 1
                n_this_err_files  += 1
                n_this_errors += len(name_error_lst)
                for rec in name_error_lst: 
                    n_s = len(rec[1].split(".") )
                    if n_s not in scope_stat:
                        scope_stat[n_s] = 1
                    else:
                        scope_stat[n_s] += 1
                    type_stat[rec[2]] += 1
                    first_name = rec[0]
                    scope = rec[1]
                    e_type = rec[2]
        out_str = "{},{},{},{}".format(lname.strip(), n_total_files, n_this_err_files, n_this_errors)
        print(out_str)
    print(n_all_files,n_error_files, n_name_errors)

if __name__ == '__main__':
    main()
