## DENE： Detecting  Name Errors in Python Program

##  Introduction

This project contains a replication package for our project including the source code and data used in our research. To replicate our results, please follow the following steps. 

## RQ1

Under the folder RQ1,  there are two parts for the exp#1 and exp2# 2 as mentioned in our paper.  Here are some description of these files and folders:

- RQ1-data/exp1: For exp1, 54 Python scripts extracted from the notebooks that contain execution name errors. These scripts are named after their repo names and their authors' names. 
- RQ1-data/rq1_fp.txt: 13 False positives listed here.
- RQ1-data/exp1/rq1_exp1_output.txt:  All 216 outputed name errors identified by DENE as stated in the RQ1 experiment 1. 
- RQ1-data/exp1/rq1-fail-samples.txt:  20 sampled cases for manual investigations in RQ1. Each line of them contain their folder name and their Github Link for your check.
- RQ1-data/exp2/rq1_exp2_folders.txt: 626 test cases for experiment 2 in our RQ1. Every line represents a folder in RQ1-data/exp2/
- RQ1-data/exp2/: Actual 626 test cases collected for experiment 2 in our RQ1.  Please note each of the folder names ontains the a test number (digits), authorname@repository name, and the corresponding commit has. Such as "972-ProgVal@Limnoria-14e637f4af81fff7d61075b1c8573326d87dda0e".

## RQ2

Under the folder of RQ2, there are all the raw experimental results stored as json files for each of libraries. To obtain our results, please execute：

```none
python rq2.py
```

## RQ3

Same as the above, raw data files are stored under the folder of RQ3, please execute the following command to see our results:

```none
python rq3.py
```

###  User study 

The 10 test cases for the user study in RQ3 are located in the folder of user-study. The Python source files are given to participants and the txt files are the additional data (execution path information produced by DENE) provided to the subject user.

## How to use our tool

To user our tool, simply execute the following command:

```console
python dene.py  $path
```
, where $path can be either a source file or a folder.

