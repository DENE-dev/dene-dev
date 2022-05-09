from functools import reduce
import networkx as nx
import sys
import random
random.seed(500)

def read_data(fn):
    lines = open(fn).readlines()
    lines = [line.strip().split()[1] for line in lines]
    lines = [line.split('/')[-1] for line in lines]
    return lines
def count_unqiue():
    fn = sys.argv[1]
    lines = open(fn).readlines()
    print(len(lines))
    lines = set(lines)
    for line in lines:
        print(line.strip())

def unique_repo():
    fn = sys.argv[1]
    lines = open(fn).readlines()
    all_repo_names = []
    for line in lines:
        parts = line.split(',')
        repo_str = parts[1].split('/')[-1]
        repo_name  = "-".join(repo_str.split('-')[1:-1])
        all_repo_names.append(repo_name)
    all_repo_names = list(set(all_repo_names))
    print("\n".join(all_repo_names))

def sample():
    fn = sys.argv[1]
    all_lines = open(fn).readlines()
    all_lines = list(all_lines)
    k = 20
    sample_lines = random.choices(all_lines, k=20)
    for line in sample_lines:
        #print(line.strip().split(',')[2])
        print(line.strip())
def filter_repo_error():
    fn1 = sys.argv[1]
    all_lines = open(fn1).readlines()
    for line in all_lines:
        line = line.strip()
        parts = line.split(',')
        if parts[0] == "Yes":
            print(parts[1])

def is_nameerror_reduce():
    fn1 = "yes.res.csv"
    fn2 = "cur.res.csv"
    all_lines1 = open(fn1).readlines()
    all_lines2 = open(fn2).readlines()
    count = 0
    assert len(all_lines1) == len(all_lines2) 
    l = len(all_lines1)
    for i in range(l):
        parent_val = all_lines1[i].strip().split(',')[-1]
        cur_val = all_lines2[i].strip().split(',')[-1]
        parent_val = int(parent_val.strip())
        cur_val = int(cur_val.strip())

        #print(cur_one, parent_one)
        if cur_val < parent_val:
            count += 1
        else:
            print(cur_val, parent_val, all_lines1[i])
    print(count, l)

def main():
    fn1 = sys.argv[1]
    fn2 = sys.argv[2]
    lines1 = read_data(fn1)
    lines2 = read_data(fn2)
    for line in lines2:
        if line not in lines1:
            print(line.strip()) 

if __name__ == '__main__':
    #main()
    #count_unqiue()
    #unique_repo()
    sample()
    #filter_repo_error()
    #is_nameerror_reduce()
