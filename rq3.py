from functools import reduce
import sys
import os
import json
import random
random.seed(100)

def main():
    base_dir = "RQ3"
    all_data_files = os.listdir(base_dir)
    n_all_files = 0
    n_error_files = 0
    n_name_errors = 0
    scope_stat = {}
    file_length = []
    file_errors = []
    n_name_errors = 0
    type_stat = {"local": 0, "foreign":0, "unresolved":0}
    for fn in all_data_files:
        content =  open(os.path.join(base_dir, fn)).read()
        test_report = json.loads(content)
        n_all_files += len(test_report["error_file"])
        for k, v in test_report["error_file"].items():
            name_error_lst = set()
            for err in v:
                rec = (err["name"], err["scope"], err["type"])
                name_error_lst.add(rec)
            n_name_errors += len(name_error_lst)
            if len(name_error_lst)>0:
                n_error_files += 1
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
    print('----------------------------------------')
    print("General Stats:")
    print("Total Files", n_all_files)
    print("Error files", n_error_files)
    print("# NameErrors", n_name_errors)
    print('----------------------------------------')
    print("Scope Level Stats:")
    for l_no, nums in scope_stat.items():
        print(l_no, ":", nums)

    print('----------------------------------------')
    print("Error types:")
    for error_type, nums in  type_stat.items():
        print(error_type, ":", nums)


if __name__ == '__main__':
    main()
